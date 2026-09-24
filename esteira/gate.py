# -*- coding: utf-8 -*-
"""O VEREDITO da Camada 1 — e ele BLOQUEIA, nao avisa.

    python -m esteira.gate <caminho> --peca <tipo>
    python -m esteira.gate <caminho> --peca <tipo> --saida <pasta>

CHAMADORES, todos no mesmo commit (regra "nada e' feito sem chamador"):
  · a CLI acima, pelo `main()` no fim deste arquivo;
  · `testar_gates.py`, a suite com mutacao;
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

from esteira import saida_legivel
from esteira import medidas
from esteira.corpus import arquivos_de_pagina, colher, colher_pasta

AQUI = os.path.dirname(os.path.abspath(__file__))
REGUAS = os.path.join(AQUI, "reguas.json")

OK, ACUSOU, NAO_USAR, NAO_MEDIR = 0, 1, 2, 3

# as tres marcas de medicao que toda pagina que capta lead ou vende carrega
MARCAS_DE_MEDICAO = {
    # `facebook.com/tr` e' a metade `noscript` do mesmo pixel, e faltava. Sem
    # ela o detector de terceiro reprovava a imagem de fallback do pixel que a
    # propria regua exige — o mesmo defeito do script, na outra metade.
    "pixel": re.compile(r"fbq\(|connect\.facebook\.net|facebook\.com/tr"
                        r"|facebook.{0,10}pixel", re.I),
    "ga4": re.compile(r"gtag\(|googletagmanager\.com|G-[A-Z0-9]{8,}", re.I),
    "clarity": re.compile(r"clarity\.ms|clarity\(", re.I),
}

# URL absoluta servindo recurso em runtime
_URL = re.compile(r"""["'](https?://[^"'\s]+)["']""")
_HREF = re.compile(r"""href\s*=\s*["']([^"']+)["']""")

# 🔴 `<a href>` E' PARA ONDE A PESSOA VAI, NAO O QUE A PAGINA CARREGA.
# O `_URL` acima casa qualquer URL entre aspas, entao o link do checkout era
# contado como "recurso de terceiro em tempo de execucao". Medido na pagina de
# vendas real: das 6 URLs absolutas, a UNICA que sobrava acusada depois das
# outras isencoes era uma ancora de checkout — ou seja, o detector acusava a
# pagina por ter um botao de comprar.
#
# `<link href>` continua contando, porque folha de estilo a pagina carrega
# mesmo. A diferenca esta na TAG, e por isso o padrao exige o `<a`.
_ANCORA = re.compile(r"""<a\b[^>]*?href\s*=\s*["'](https?://[^"']+)["']""",
                     re.I | re.S)

# Hosts que nao contam como CDN de terceiro: fonte de letra e namespace de
# especificacao nao servem midia da pagina.
#
# A lista guarda HOST, nunca URL inteira, e isso tem dois motivos. O primeiro
# e' que comparar host e' mais correto que casar prefixo de texto: um prefixo
# curto casa tambem com dominio parecido que outra pessoa registrou, e ha um
# teste so para esse caso. O segundo e' que um gate de publicacao trata URL
# literal dentro do codigo como contato a redigir, e ele esta certo na regra
# geral — estas aqui sao padroes publicos, nao contato de ninguem.
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

def gate_legibilidade(texto, alvo_ilf, folga, regime="limiar"):
    m = medidas.legibilidade(texto)
    if m is None:
        return Achado("legibilidade", "nao-mediu", nota="texto sem frase")
    if alvo_ilf is None:
        return Achado("legibilidade", "nao-mediu", valor=m["ilf"],
                      nota="sem regua medida (faixa: %s)" % m["faixa"])
    piso = alvo_ilf - (folga.get("abaixo") or 0)
    ok = m["ilf"] >= piso
    if not ok and regime != "limiar":
        return Achado("legibilidade", "passa", valor=m["ilf"],
                      limiar=round(piso, 1), confianca="baixa",
                      nota="fora da direcao, e direcao nao reprova "
                           "(faixa: %s)" % m["faixa"])
    return Achado("legibilidade", "passa" if ok else "reprova",
                  valor=m["ilf"], limiar=round(piso, 1),
                  nota="faixa: %s" % m["faixa"])


def gate_forma(texto, alvos, folgas, regime="limiar"):
    """Uma linha por metrica com alvo declarado. Alvo nulo nao reprova.

    🔴 `regime` decide se o alvo REPROVA ou so orienta. Regua tirada de menos
    de quinze pecas descreve o gosto de quem escreveu aquelas poucas, nao a
    forma do tipo de peca — entao ela sai como DIRECAO, com o numero a vista e
    sem poder de veto. Chamar isso de limiar seria dar a um corpus de cinco
    pecas o mesmo peso que a um de cinquenta.
    """
    m = medidas.forma(texto)
    if m is None:
        return [Achado("forma", "nao-mediu", nota="texto sem frase")]
    v = medidas.vicio(texto)
    m = dict(m)
    m["vicio"] = None if v is None else v["indice"]
    saida = []
    for chave in ("pf", "curtas", "perg", "seg", "imper", "trav", "vicio"):
        alvo = alvos.get(chave)
        valor = m.get(chave)
        if valor is None:
            saida.append(Achado("forma:%s" % chave, "nao-mediu",
                                nota="texto curto demais para esta metrica"))
            continue
        if alvo is None:
            saida.append(Achado("forma:%s" % chave, "nao-mediu",
                                valor=valor, nota="sem alvo medido"))
            continue
        folga = folgas.get(chave) or {}
        acima, abaixo = folga.get("acima"), folga.get("abaixo")
        ruim = False
        if acima is not None and valor - alvo > acima:
            ruim = True
        if abaixo is not None and alvo - valor > abaixo:
            ruim = True
        if ruim and regime != "limiar":
            saida.append(Achado("forma:%s" % chave, "passa", valor=valor,
                                limiar=alvo, confianca="baixa",
                                nota="fora da direcao, e direcao nao reprova"))
            continue
        saida.append(Achado("forma:%s" % chave, "reprova" if ruim else "passa",
                            valor=valor, limiar=alvo))
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


def gate_cdn_de_terceiro(fonte_bruta, permitido, exigidas=()):
    """URL absoluta servindo recurso em runtime.

    Achado do gabarito de num caso medido: o fundo animado vinha de CloudFront de
    terceiro. E' deterministico e barato de pegar.

    🔴 O QUE A REGUA EXIGE, ELA NAO PODE REPROVAR.
    Medido na mesma pagina, na mesma rodada, antes desta linha existir:

        PASSA     medicao:pixel     presente
        REPROVA   cdn-de-terceiro   1o: https://connect.facebook.net/...

    As duas linhas falam do MESMO script. `medicao_exigida` manda instalar o
    pixel; o detector de terceiro reprovava o arquivo que o instala. Nenhuma
    pagina medida conseguia passar nos dois, e a pessoa nao tinha o que
    consertar — que e' o alarme que ensina a ignorar a linha inteira.

    A isencao sai das PROPRIAS marcas de medicao, e nao de uma lista escrita a
    mao, para que as duas regras nao possam divergir depois. E vale so para o
    que a regua exige: marca de medicao que ninguem pediu continua sendo
    recurso de terceiro.

    O que sobra do detector continua inteiro, e e' o que ele existia para
    pegar: fonte, imagem, video e script que a PAGINA PRECISA para renderizar.
    Pixel de medicao nao renderiza nada.
    """
    if permitido:
        return [Achado("cdn-de-terceiro", "passa", nota="permitido pela regua")]
    padroes = [MARCAS_DE_MEDICAO[m] for m in exigidas
               if m in MARCAS_DE_MEDICAO]
    ancoras = set(_ANCORA.findall(fonte_bruta))
    urls = set(_URL.findall(fonte_bruta))
    externos = sorted(u for u in urls
                      if u not in ancoras
                      and _host(u) not in HOSTS_PERMITIDOS
                      and not any(p.search(u) for p in padroes))
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

    # 🔴 A PASTA PRECISA DO TEXTO BRUTO, IGUAL AO ARQUIVO SOZINHO.
    # Aqui havia `if os.path.isfile(caminho) else ""`, e o `if bruta:` logo
    # abaixo pulava TRES gates quando o caminho era pasta: medicao instalada,
    # recurso de terceiro e link interno. Medido na mesma pagina, mesmos bytes:
    #
    #     gate <pasta>   -> LIMPO (0),   8 medidas
    #     gate <arquivo> -> REPROVA (1), 12 medidas, 3 reprovas
    #
    # E a pasta e' o que o roteiro do `AGENTS.md` manda usar. O caminho
    # documentado era o que escondia os gates — que e' a definicao de gate
    # decorativo, so que pior, porque ele parecia estar rodando.
    #
    # LIMITE DECLARADO: numa pasta com varias paginas a bruta e' a
    # CONCATENACAO. Entao `medicao:ga4` passa se QUALQUER pagina instalar o
    # GA4, e nao se todas instalarem. Para a pergunta "esta pagina esta
    # medida?", aponte o gate para o arquivo.
    try:
        if os.path.isfile(caminho):
            bruta = open(caminho, encoding="utf-8").read()
        else:
            partes = []
            for p in arquivos_de_pagina(caminho):
                try:
                    partes.append(open(p, encoding="utf-8").read())
                except (OSError, UnicodeDecodeError):
                    continue
            bruta = "\n".join(partes)
    except (OSError, UnicodeDecodeError):
        bruta = ""

    alvos = ficha.get("alvos", {})
    # 🔴 A FOLGA DA PROPRIA PECA VEM PRIMEIRO. A do topo e' herdada, e foi
    # herdando folga que um defeito viajou de um projeto para outro: 2,0 onde
    # o desvio medido era 2,3, reprovando oito pecas legitimas de quarenta e
    # sete. Quem tem folga medida usa a sua; quem nao tem cai na de reserva.
    folgas = ficha.get("folgas") or reguas.get("_folgas", {})
    regime = ficha.get("regime", "limiar")
    univ = reguas.get("universal", {})

    achados = [gate_legibilidade(texto, alvos.get("ilf"),
                                 folgas.get("ilf") or {}, regime)]
    achados += gate_forma(texto, alvos, folgas, regime)
    if bruta:
        achados += gate_medicao(bruta, univ.get("medicao_exigida", []))
        achados += gate_cdn_de_terceiro(
            bruta, univ.get("cdn_de_terceiro_permitido", False),
            univ.get("medicao_exigida", []))
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
    saida_legivel()
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
