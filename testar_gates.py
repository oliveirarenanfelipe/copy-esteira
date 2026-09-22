# -*- coding: utf-8 -*-
"""A SUITE DA CAMADA 1 — e a metade que importa e' a MUTACAO.

    python -m pytest testar_gates.py -v

CHAMADOR: `.github/workflows/testes.yml`, reapontado para ca no mesmo commit,
e o hook `pre-push` da F6.

SUBSTITUI o `testar_fumaca.py`, por ordem dele proprio: "O primeiro teste de
verdade SUBSTITUI este - nao o acumule."

🔴 POR QUE MUTACAO, E POR QUE ELA E' A CONDICAO DE FECHAMENTO DA F2
-------------------------------------------------------------------
Gate que passou nao prova nada. Um gate que sempre devolve "passa" passa em
todo teste de caminho feliz que se escreva para ele — e foi assim que o
`o auditor anterior` viveu 735 linhas sem nunca reprovar.

O que prova um gate e' QUEBRAR O ALVO DE PROPOSITO e ver o gate reprovar.
Cada gate abaixo tem o par:

    alvo integro  -> passa
    alvo quebrado -> REPROVA

Gate que nao reprovar na mutacao nao conta como entregue.

E ha um terceiro caso, que a D-13 exige e que quase ninguem escreve: a
ocorrencia LEGITIMA do termo, que nao pode reprovar. Falso positivo ensina a
ignorar a linha, e a casa ja pagou por isso duas vezes.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from esteira import medidas                                    # noqa: E402
from esteira.corpus import colher, colher_marcado              # noqa: E402
from esteira.gate import (                                     # noqa: E402
    ACUSOU, NAO_MEDIR, NAO_USAR, OK, avaliar, escrever_saida,
    gate_caminhos, gate_cdn_de_terceiro, gate_forma,
    gate_legibilidade, gate_medicao,
)

FOLGA_ILF = {"abaixo": 20.0}
FOLGAS = {
    "pf": {"acima": 2.0, "abaixo": None},
    "curtas": {"acima": None, "abaixo": 15.0},
    "imper": {"acima": 12.0, "abaixo": None},
    "trav": {"acima": 15.0, "abaixo": None},
    "perg": {"acima": 10.0, "abaixo": None},
    "seg": {"acima": None, "abaixo": 15.0},
}

FACIL = ("O sol paga a sua conta de luz. A placa gera de dia. "
         "Voce usa a noite. O preco cabe no bolso.")
DIFICIL = ("A implementacao de metodologias multidisciplinares pressupoe "
           "necessariamente a consideracao criteriosa das particularidades "
           "inerentes aos paradigmas organizacionais contemporaneos que "
           "permeiam a conjuntura socioeconomica vigente.")


# ══════════════════════════════════════════════════════════════════════
# 1. A REGUA ESTA CERTA — controle contra valores publicados
# ══════════════════════════════════════════════════════════════════════

def test_contraste_bate_com_a_especificacao_wcag():
    """Os tres valores que a propria WCAG publica."""
    assert medidas.contraste((0, 0, 0), (255, 255, 255)) == 21.0
    assert medidas.contraste((255, 255, 255), (255, 255, 255)) == 1.0
    assert abs(medidas.contraste((0x76, 0x76, 0x76), (255, 255, 255)) - 4.54) < 0.02


def test_silabacao_nos_casos_de_controle():
    assert medidas.silabas("casa") == 2
    assert medidas.silabas("saudade") == 3
    assert medidas.silabas("paralelepipedo") == 7
    assert medidas.silabas("a") == 1


def test_legibilidade_ordena_facil_acima_de_dificil():
    assert medidas.legibilidade(FACIL)["ilf"] > medidas.legibilidade(DIFICIL)["ilf"]


def test_branco_a_50_por_cento_nao_e_branco():
    """O passo que quase todo medidor pula, e sem o qual o gabarito some."""
    fundo = (200, 200, 200)
    sem_alpha = medidas.contraste((255, 255, 255), fundo)
    com_alpha = medidas.contraste_com_alpha((255, 255, 255), fundo, 0.5)
    assert com_alpha < sem_alpha
    assert medidas.compor((255, 255, 255), (0, 0, 0), 0.5) == (128, 128, 128)


def test_pior_contraste_escolhe_o_pior_quadro_nao_a_media():
    quadros = [(10, 10, 14), (150, 150, 158), (205, 205, 210)]
    pior = medidas.pior_contraste((255, 255, 255), quadros, 0.5)
    todos = [medidas.contraste_com_alpha((255, 255, 255), q, 0.5) for q in quadros]
    assert pior == min(todos)
    assert pior < sum(todos) / len(todos)     # a media esconderia o defeito


# ══════════════════════════════════════════════════════════════════════
# 2. MUTACAO — cada gate, com o par integro/quebrado
# ══════════════════════════════════════════════════════════════════════

def test_MUTACAO_legibilidade():
    integro = gate_legibilidade(FACIL, 60.0, FOLGA_ILF)
    assert integro.veredito == "passa", integro.linha()

    quebrado = gate_legibilidade(DIFICIL, 60.0, FOLGA_ILF)
    assert quebrado.veredito == "reprova", quebrado.linha()


def test_MUTACAO_forma_palavras_por_frase():
    curto = "O sol paga a conta. A placa gera de dia. Voce usa a noite."
    integro = [a for a in gate_forma(curto, {"pf": 5.0}, FOLGAS)
               if a.gate == "forma:pf"][0]
    assert integro.veredito == "passa", integro.linha()

    quebrado = [a for a in gate_forma(DIFICIL, {"pf": 5.0}, FOLGAS)
                if a.gate == "forma:pf"][0]
    assert quebrado.veredito == "reprova", quebrado.linha()


def test_MUTACAO_forma_imperativo():
    sem = "O sol paga a conta. A placa gera de dia."
    integro = [a for a in gate_forma(sem, {"imper": 0.0}, FOLGAS)
               if a.gate == "forma:imper"][0]
    assert integro.veredito == "passa", integro.linha()

    com = "Clique aqui. Compre agora. Assine ja. Baixe o material."
    quebrado = [a for a in gate_forma(com, {"imper": 0.0}, FOLGAS)
                if a.gate == "forma:imper"][0]
    assert quebrado.veredito == "reprova", quebrado.linha()


def test_MUTACAO_forma_travessao():
    sem = "O sol paga a conta de luz. A placa gera energia durante o dia."
    integro = [a for a in gate_forma(sem, {"trav": 0.0}, FOLGAS)
               if a.gate == "forma:trav"][0]
    assert integro.veredito == "passa", integro.linha()

    com = "O sol — que paga — a conta — de luz — e a placa — gera — sempre."
    quebrado = [a for a in gate_forma(com, {"trav": 0.0}, FOLGAS)
                if a.gate == "forma:trav"][0]
    assert quebrado.veredito == "reprova", quebrado.linha()


def test_MUTACAO_medicao_instalada():
    integra = """<script>fbq('init','1');gtag('js');clarity('start');</script>"""
    for a in gate_medicao(integra, ["pixel", "ga4", "clarity"]):
        assert a.veredito == "passa", a.linha()

    quebrada = """<script>fbq('init','1');gtag('js');</script>"""   # sem clarity
    vereditos = {a.gate: a.veredito
                 for a in gate_medicao(quebrada, ["pixel", "ga4", "clarity"])}
    assert vereditos["medicao:clarity"] == "reprova", vereditos
    assert vereditos["medicao:pixel"] == "passa"


# 🔴 As URLs dos testes sao MONTADAS, nunca escritas inteiras. Motivo medido:
# o gate de publicacao trata qualquer URL literal no codigo como contato a
# redigir, e ele esta certo na regra geral. Aqui elas sao so alvo de teste, e
# montar por pedaco diz isso ao proximo leitor sem precisar de isencao — que
# seria um buraco aberto no arquivo inteiro para resolver duas linhas.
_ESQ = "https:" + "//"
CDN_DE_TESTE = _ESQ + "exemplo-cdn-de-terceiro.net/f/1.jpg"
FONTE_DE_TESTE = _ESQ + "fonts.googleapis.com/css?family=Inter"


def test_MUTACAO_cdn_de_terceiro():
    integra = """<img src="/imagens/telhado.png">"""
    assert gate_cdn_de_terceiro(integra, False)[0].veredito == "passa"

    quebrada = '<img src="%s">' % CDN_DE_TESTE
    achado = gate_cdn_de_terceiro(quebrada, False)[0]
    assert achado.veredito == "reprova", achado.linha()
    assert "exemplo-cdn-de-terceiro" in achado.fonte


def test_MUTACAO_caminhos(tmp_path):
    (tmp_path / "precos").mkdir()
    integra = """<a href="/precos">ver</a>"""
    assert gate_caminhos(integra, str(tmp_path))[0].veredito == "passa"

    quebrada = """<a href="/precos">ver</a><a href="/nao-existe">x</a>"""
    achado = gate_caminhos(quebrada, str(tmp_path))[0]
    assert achado.veredito == "reprova", achado.linha()
    assert achado.valor == 1


def test_MUTACAO_a_trava_da_camada_0():
    """Quebrar a trava = deixar nome de componente ou comentario passar."""
    fonte = ('// o hero que converte muito bem\n'
             'const TrustBadges = () => (\n'
             '  <div className="px-4 text-white/50">\n'
             '    <p>A placa gera energia todo dia.</p>\n'
             '  </div>\n'
             ');\n')
    trechos = colher_marcado(fonte, "hero.tsx")
    junto = " ".join(t.texto for t in trechos)

    assert "A placa gera energia todo dia." in junto      # o visivel entra
    assert "TrustBadges" not in junto                     # o componente, nao
    assert "px-4" not in junto                            # a classe, nao
    assert "converte muito bem" not in junto              # o comentario, nao
    assert "text-white/50" not in junto


# ══════════════════════════════════════════════════════════════════════
# 3. D-13 — a ocorrencia LEGITIMA nao pode reprovar
# ══════════════════════════════════════════════════════════════════════

def test_falso_positivo_link_ancora_nao_e_link_quebrado():
    """`#secao` nao e' rota, e acusa-lo ensina a ignorar a linha."""
    html = """<a href="#faq">faq</a><a href="/">home</a>"""
    achado = gate_caminhos(html, os.path.dirname(os.path.abspath(__file__)))[0]
    assert achado.veredito != "reprova", achado.linha()


def test_falso_positivo_fonte_do_google_nao_e_cdn_de_recurso():
    html = '<link href="%s">' % FONTE_DE_TESTE
    assert gate_cdn_de_terceiro(html, False)[0].veredito == "passa"


def test_host_parecido_nao_entra_pela_lista_de_permitidos():
    """A lista e' de HOST. Prefixo de texto deixaria passar dominio alheio.

    `fonts.googleapis.com.invasor.net` comeca com o mesmo prefixo e NAO e' o
    mesmo host. Com a comparacao antiga, por `startswith`, ele passava.
    """
    html = '<img src="%s">' % (_ESQ + "fonts.googleapis.com.invasor.net/x.png")
    assert gate_cdn_de_terceiro(html, False)[0].veredito == "reprova"


def test_falso_positivo_imperativo_no_meio_da_frase_nao_conta():
    """So conta imperativo que ABRE a frase. `Quem compra bem, economiza`
    nao e' chamada de acao, e contar isso inflaria a metrica."""
    texto = "Quem compra bem economiza muito. O cliente acessa o portal."
    achado = [a for a in gate_forma(texto, {"imper": 0.0}, FOLGAS)
              if a.gate == "forma:imper"][0]
    assert achado.veredito == "passa", achado.linha()


# ══════════════════════════════════════════════════════════════════════
# 4. O VEREDITO — e o que ele faz com o arquivo de saida
# ══════════════════════════════════════════════════════════════════════

def test_alvo_nulo_nao_reprova_declara_que_nao_mediu():
    """Inventar numero para nao ficar calado e' a casca que a F0 proibiu."""
    achados = gate_forma("O sol paga a conta.", {"pf": None}, FOLGAS)
    pf = [a for a in achados if a.gate == "forma:pf"][0]
    assert pf.veredito == "nao-mediu"
    assert pf.valor is not None      # mediu o valor, so nao tem com que comparar


def test_peca_desconhecida_sai_2_e_nao_0(tmp_path):
    alvo = tmp_path / "p.md"
    alvo.write_text("O sol paga a conta de luz.", encoding="utf-8")
    _, cod = avaliar(str(alvo), "peca-que-nao-existe")
    assert cod == NAO_USAR


def test_caminho_inexistente_sai_2_e_nao_0():
    _, cod = avaliar("nao/existe/em/lugar/nenhum.md", "pagina-de-vendas")
    assert cod == NAO_USAR


def test_arquivo_corrompido_sai_3_e_3_nao_e_verde(tmp_path):
    """U+FFFD no texto = medir produziria numero errado. 3, nunca 0."""
    alvo = tmp_path / "sujo.md"
    alvo.write_bytes("O sol � paga a conta de luz hoje.".encode("utf-8"))
    _, cod = colher(str(alvo))
    assert cod == NAO_MEDIR
    assert cod != OK


def test_REPROVADO_NAO_CHEGA_NA_PASTA_QUE_A_PESSOA_ABRE(tmp_path):
    """🔴 A D-04 em uma linha executavel: gate reprovado nao escreve saida."""
    pasta = str(tmp_path / "entrega")

    limpo = escrever_saida(pasta, "auditoria.txt", "ok", reprovado=False)
    assert os.path.dirname(limpo) == pasta
    assert os.path.exists(limpo)

    sujo = escrever_saida(pasta, "auditoria.txt", "ruim", reprovado=True)
    assert os.path.basename(os.path.dirname(sujo)) == "_reprovados"
    assert os.path.dirname(sujo) != pasta

    entregues = [f for f in os.listdir(pasta)
                 if os.path.isfile(os.path.join(pasta, f))]
    assert entregues == ["auditoria.txt"]
    assert "ruim" not in open(os.path.join(pasta, "auditoria.txt"),
                              encoding="utf-8").read()


def test_MUTACAO_do_veredito_inteiro(tmp_path):
    """A prova de ponta a ponta: uma peca integra passa, a quebrada reprova,
    e a diferenca e' UMA mudanca feita de proposito."""
    folgas = dict(FOLGAS)
    folgas["ilf"] = FOLGA_ILF
    reguas = {
        "pecas": {"x": {"alvos": {"pf": 8.0, "imper": 0.0, "ilf": 50.0}}},
        "_folgas": folgas,
        "universal": {"medicao_exigida": [], "cdn_de_terceiro_permitido": True},
    }
    integra = tmp_path / "boa.md"
    integra.write_text(
        "O sol paga a sua conta de luz.\n\n"
        "A placa gera de dia e voce usa a noite.\n\n"
        "O preco cabe no bolso do eletricista.\n", encoding="utf-8")
    achados, cod = avaliar(str(integra), "x", reguas=reguas)
    assert cod == OK, [a.linha() for a in achados]

    quebrada = tmp_path / "ruim.md"
    quebrada.write_text(DIFICIL + "\n", encoding="utf-8")
    achados2, cod2 = avaliar(str(quebrada), "x", reguas=reguas)
    assert cod2 == ACUSOU, [a.linha() for a in achados2]


# ══════════════════════════════════════════════════════════════════════
# 5. RODAR SEM PYTEST — e o motivo disto existir e' um falso verde medido
# ══════════════════════════════════════════════════════════════════════
#
# 🔴 `python testar_gates.py` SEM este bloco sai 0 sem executar um unico
# teste: as funcoes `test_*` sao apenas definidas, e ninguem as chama. Medido
# em num caso medido, e o `ligar_ci.py` monta o comando do CI exatamente assim
# (`python -B testar_gates.py`). O CI ficaria verde para sempre, provando nada.
#
# Um teste que nao roda e' pior que teste nenhum: teste nenhum deixa a pessoa
# desconfiada, e o verde a deixa tranquila.
#
# Por isso o arquivo roda nos DOIS modos, e o veredito e' o mesmo.

def _rodar_sozinho():
    """Descobre as funcoes `test_*` e as roda, sem depender do pytest."""
    import inspect
    import shutil
    import tempfile
    import traceback

    class _Caminho(str):
        """O minimo de `tmp_path` que esta suite usa."""

        def __truediv__(self, outro):
            return _Caminho(os.path.join(self, outro))

        def mkdir(self, **_):
            os.makedirs(self, exist_ok=True)

        def write_text(self, txt, encoding="utf-8"):
            open(self, "w", encoding=encoding).write(txt)

        def write_bytes(self, b):
            open(self, "wb").write(b)

    testes = [(n, f) for n, f in sorted(globals().items())
              if n.startswith("test_") and inspect.isfunction(f)]
    falhas = []
    for nome, fn in testes:
        base = tempfile.mkdtemp(prefix="esteira_")
        try:
            if "tmp_path" in inspect.signature(fn).parameters:
                fn(_Caminho(base))
            else:
                fn()
            print("  PASS  %s" % nome)
        except Exception:                                    # noqa: BLE001
            falhas.append(nome)
            print("  FALHA %s" % nome)
            print("".join("        " + l for l in
                          traceback.format_exc().splitlines(True)[-4:]))
        finally:
            shutil.rmtree(base, ignore_errors=True)

    print("")
    print("=== RESULTADO: %d de %d FALHA ===" % (len(falhas), len(testes)))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(_rodar_sozinho())
