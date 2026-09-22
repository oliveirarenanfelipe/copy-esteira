# -*- coding: utf-8 -*-
"""O VEREDITO da Camada 1 — e ele BLOQUEIA, nao avisa.

    python -m esteira.gate <caminho> --peca <tipo>
    python -m esteira.gate <caminho> --peca <tipo> --saida <pasta>

CHAMADORES, todos no mesmo commit (regra "nada e' feito sem chamador"):
  · a CLI acima, pelo `main()` no fim deste arquivo;
  · `testar_gate.py`, a suite com mutacao;
  · `.github/workflows/testes.yml`, que roda a suite em toda push.
E esta peca e' o chamador de `esteira/medidas.py` e `esteira/corpus.py`.

🔴 POR QUE ESTA PECA EXISTE, E E' A LICAO MAIS CARA DA F0
---------------------------------------------------------
O auditor de copy mais avancado da casa, `um auditor de copy anterior`,
tem 735 linhas, mede seis metricas por tipo de peca — e NUNCA reprovou uma
peca na vida. A linha `:731` e' `return 0`, incondicional. Os desvios saem
como texto numa coluna chamada "fora da regua", e a peca segue.

E' exatamente o que a D-04 nomeia: "aviso que nao reprova. Some no log e a
peca sai com cara de pronta".

Aqui o veredito E' o codigo de saida, e peca reprovada NAO GANHA ARQUIVO.
O mecanismo e' o da `a esteira de video da casa` do video: o destino do arquivo e'
decidido pelo resultado do gate, e o reprovado vai para `_reprovados/`, que
nao e' a pasta que a pessoa abre.

CODIGOS DE SAIDA (a taxonomia da maquina)
    0  nada a acusar
    1  ACUSOU — mediu, e o alvo reprovou
    2  nao deu para USAR — argumento faltando, caminho que nao existe
    3  nao deu para MEDIR — a fonte nao respondeu, ou nao ha regua.
       NAO e' um verde: "gate que nao mede nao aprova".
"""
import json
import os
import re
import sys

from esteira import medidas
from esteira.corpus import colher, colher_pasta

AQUI = os.path.dirname(os.path.abspath(__file__))
REGUAS = os.path.join(AQUI, "reguas.json")

OK, ACUSOU, NAO_USAR, NAO_MEDIR = 0, 1, 2, 3

# as tres marcas de medicao que toda pagina que capta lead ou vende carrega
MARCAS_DE_MEDICAO = {
    "pixel": re.compile(r"fbq\(|connect\.facebook\.net|facebook.{0,10}pixel", re.I),
    "ga4": re.compile(r"gtag\(|googletagmanager\.com|G-[A-Z0-9]{8,}", re.I),
    "clarity": re.compile(r"clarity\.ms|clarity\(", re.I),
}

# URL absoluta servindo recurso em runtime
_URL = re.compile(r"""["'](https?://[^"'\s]+)["']""")
_HREF = re.compile(r"""href\s*=\s*["']([^"']+)["']""")

# Hosts que nao contam como CDN de terceiro: fonte de letra e namespace de
# especificacao nao servem midia da pagina.
#
# A lista guarda HOST, nunca URL inteira, e isso tem dois motivos. O primeiro
# e' que comparar host e' mais correto que comparar prefixo de texto: com
# prefixo, `https://fonts.g` casaria tambem com um dominio parecido registrado
# por outra pessoa. O segundo e' que um gate de publicacao trata URL literal
# dentro do codigo como contato a redigir, e ele esta certo — a excecao e' que
# estas aqui sao padroes publicos, nao contato de ninguem.
HOSTS_PERMITIDOS = frozenset((
    "fonts.googleapis.com", "fonts.gstatic.com", "www.w3.org", "w3.org",
))


def _host(url):
    """O host de uma URL, em minuscula, sem porta."""
    corpo = url.split("//", 1)[-1]
    return corpo.split("/", 1)[0].split(":", 1)[0].lower()


class Achado:
    """Um fato medido, com veredito. Sem fonte, nao existe."""

    __slots__ = ("gate", "veredito", "valor", "limiar", "fonte", "nota",
                 "confianca")

    def __init__(self, gate, veredito, valor=None, limiar=None, fonte="",
                 nota="", confianca="alta"):
        self.gate = gate
        self.veredito = veredito      # "passa" | "reprova" | "nao-mediu"
        self.valor = valor
        self.limiar = limiar
        self.fonte = fonte
        self.nota = nota
        self.confianca = confianca

    def linha(self):
        marca = {"passa": "PASSA", "reprova": "REPROVA",
                 "nao-mediu": "NAO MEDIU"}[self.veredito]
        v = "" if self.valor is None else " %s" % self.valor
        lim = "" if self.limiar is None else " (limiar %s)" % self.limiar
        baixa = "  [confianca baixa]" if self.confianca == "baixa" else ""
        return "  %-9s %-22s%s%s  %s%s" % (
            marca, self.gate, v, lim, self.nota, baixa)


def carregar_reguas(caminho=REGUAS):
    try:
        return json.load(open(caminho, encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ── os gates ────────────────────────────────────────────────────────────────

def gate_legibilidade(texto, alvo_ilf, folga):
    m = medidas.legibilidade(texto)
    if m is None:
        return Achado("legibilidade", "nao-mediu", nota="texto sem frase")
    if alvo_ilf is None:
        return Achado("legibilidade", "nao-mediu", valor=m["ilf"],
                      nota="sem regua medida (faixa: %s)" % m["faixa"])
    piso = alvo_ilf - (folga.get("abaixo") or 0)
    ok = m["ilf"] >= piso
    return Achado("legibilidade", "passa" if ok else "reprova",
                  valor=m["ilf"], limiar=round(piso, 1),
                  nota="faixa: %s" % m["faixa"])


def gate_forma(texto, alvos, folgas):
    """Uma linha por metrica com alvo declarado. Alvo nulo nao reprova."""
    m = medidas.forma(texto)
    if m is None:
        return [Achado("forma", "nao-mediu", nota="texto sem frase")]
    saida = []
    for chave in ("pf", "curtas", "perg", "seg", "imper", "trav"):
        alvo = alvos.get(chave)
        if alvo is None:
            saida.append(Achado("forma:%s" % chave, "nao-mediu",
                                valor=m[chave], nota="sem alvo medido"))
            continue
        folga = folgas.get(chave) or {}
        acima, abaixo = folga.get("acima"), folga.get("abaixo")
        ruim = False
        if acima is not None and m[chave] - alvo > acima:
            ruim = True
        if abaixo is not None and alvo - m[chave] > abaixo:
            ruim = True
        saida.append(Achado("forma:%s" % chave, "reprova" if ruim else "passa",
                            valor=m[chave], limiar=alvo))
    return saida


def gate_medicao(fonte_bruta, exigidas):
    """As tres marcas de medicao. Pagina sem as tres nao responde por que
    nao converte — regra da casa, e o custo dela ja foi medido."""
    saida = []
    for marca in exigidas:
        padrao = MARCAS_DE_MEDICAO.get(marca)
        if padrao is None:
            saida.append(Achado("medicao:%s" % marca, "nao-mediu",
                                nota="marca desconhecida"))
            continue
        achou = bool(padrao.search(fonte_bruta))
        saida.append(Achado("medicao:%s" % marca,
                            "passa" if achou else "reprova",
                            valor="presente" if achou else "ausente"))
    return saida


def gate_cdn_de_terceiro(fonte_bruta, permitido):
    """URL absoluta servindo recurso em runtime.

    Achado do gabarito de num caso medido: o fundo animado vinha de CloudFront de
    terceiro. E' deterministico e barato de pegar.
    """
    if permitido:
        return [Achado("cdn-de-terceiro", "passa", nota="permitido pela regua")]
    urls = set(_URL.findall(fonte_bruta))
    externos = sorted(u for u in urls if _host(u) not in HOSTS_PERMITIDOS)
    if not externos:
        return [Achado("cdn-de-terceiro", "passa", valor=0)]
    return [Achado("cdn-de-terceiro", "reprova", valor=len(externos),
                   fonte=externos[0], nota="1o: %s" % externos[0][:60])]


def gate_caminhos(fonte_bruta, raiz_do_projeto=None):
    """Link interno que nao resolve. So conta o que da para conferir."""
    hrefs = [h for h in _HREF.findall(fonte_bruta)
             if h.startswith("/") and not h.startswith("//")]
    if not hrefs:
        return [Achado("caminhos", "nao-mediu", nota="nenhum link interno")]
    if raiz_do_projeto is None:
        return [Achado("caminhos", "nao-mediu", valor=len(hrefs),
                       nota="sem raiz para resolver as rotas")]
    faltando = []
    for h in sorted(set(hrefs)):
        rota = h.split("?")[0].split("#")[0].strip("/")
        if not rota:
            continue
        achou = False
        for base, dirs, _arqs in os.walk(raiz_do_projeto):
            dirs[:] = [d for d in dirs if d not in ("node_modules", ".git")]
            if rota.replace("/", os.sep) in base:
                achou = True
                break
        if not achou:
            faltando.append(h)
    return [Achado("caminhos", "reprova" if faltando else "passa",
                   valor=len(faltando), limiar=0,
                   nota=("1o: %s" % faltando[0]) if faltando else "")]


# ── o veredito ──────────────────────────────────────────────────────────────

def avaliar(caminho, peca, reguas=None, raiz=None):
    """(achados, codigo). O codigo e' o veredito da camada."""
    reguas = reguas or carregar_reguas()
    if reguas is None:
        return [], NAO_MEDIR
    ficha = reguas.get("pecas", {}).get(peca)
    if ficha is None:
        return [], NAO_USAR

    if os.path.isdir(caminho):
        trechos, cod = colher_pasta(caminho)
        raiz = raiz or caminho
    else:
        trechos, cod = colher(caminho)
    if cod != OK:
        return [], cod

    texto = " ".join(t.texto for t in trechos)
    try:
        bruta = (open(caminho, encoding="utf-8").read()
                 if os.path.isfile(caminho) else "")
    except (OSError, UnicodeDecodeError):
        bruta = ""

    alvos = ficha.get("alvos", {})
    folgas = reguas.get("_folgas", {})
    univ = reguas.get("universal", {})

    achados = [gate_legibilidade(texto, alvos.get("ilf"),
                                 folgas.get("ilf") or {})]
    achados += gate_forma(texto, alvos, folgas)
    if bruta:
        achados += gate_medicao(bruta, univ.get("medicao_exigida", []))
        achados += gate_cdn_de_terceiro(
            bruta, univ.get("cdn_de_terceiro_permitido", False))
        achados += gate_caminhos(bruta, raiz)

    if any(a.veredito == "reprova" for a in achados):
        return achados, ACUSOU
    if all(a.veredito == "nao-mediu" for a in achados):
        return achados, NAO_MEDIR
    return achados, OK


def escrever_saida(pasta, nome, conteudo, reprovado):
    """🔴 Reprovado NAO chega na pasta que a pessoa abre (D-04).

    Igual a `a esteira de video da casa`: o destino e' decidido pelo veredito. Nao ha
    opcao de forcar, porque a opcao de forcar e' como o gate morre.
    """
    destino = os.path.join(pasta, "_reprovados") if reprovado else pasta
    os.makedirs(destino, exist_ok=True)
    caminho = os.path.join(destino, nome)
    open(caminho, "w", encoding="utf-8").write(conteudo)
    return caminho


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    livres = [a for a in argv if not a.startswith("--")]
    if not livres:
        print("uso: python -m esteira.gate <caminho> --peca <tipo>")
        print("     tipos:", ", ".join(sorted(
            (carregar_reguas() or {}).get("pecas", {}))))
        return NAO_USAR
    caminho = livres[0]
    peca = None
    if "--peca" in argv:
        i = argv.index("--peca")
        if i + 1 < len(argv):
            peca = argv[i + 1]
    if peca is None:
        print("falta --peca. Pela D-02, o produto se declara antes de medir.")
        return NAO_USAR
    saida = None
    if "--saida" in argv:
        i = argv.index("--saida")
        if i + 1 < len(argv):
            saida = argv[i + 1]

    achados, cod = avaliar(caminho, peca)
    rotulo = {OK: "LIMPO", ACUSOU: "REPROVA", NAO_USAR: "NAO DEU PARA USAR",
              NAO_MEDIR: "NAO DEU PARA MEDIR"}[cod]
    print("GATE DA CAMADA 1 — %s  (peca: %s)" % (caminho, peca))
    print()
    for a in achados:
        print(a.linha())
    print()
    n_rep = sum(1 for a in achados if a.veredito == "reprova")
    n_nm = sum(1 for a in achados if a.veredito == "nao-mediu")
    print("  %s (%d) — %d reprovou, %d nao mediu, %d passou"
          % (rotulo, cod, n_rep, n_nm,
             sum(1 for a in achados if a.veredito == "passa")))
    if cod == NAO_MEDIR:
        print("  Gate que nao mede nao aprova — e isto NAO e um verde.")

    if saida:
        corpo = "\n".join(a.linha() for a in achados)
        onde = escrever_saida(saida, "auditoria.txt", corpo, cod == ACUSOU)
        print("  saida: %s" % onde)
    return cod


if __name__ == "__main__":
    sys.exit(main())
