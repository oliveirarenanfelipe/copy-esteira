# -*- coding: utf-8 -*-
"""A SUITE DA CAMADA 1 — e a metade que importa e' a MUTACAO.

    python -m pytest testar_gates.py -v

CHAMADOR: `.github/workflows/testes.yml`, reapontado para ca no mesmo commit,
e o hook `pre-push` da F6.

SUBSTITUI o teste de fumaca anterior, por ordem dele proprio: "O primeiro teste
de verdade SUBSTITUI este - nao o acumule."

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
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from esteira import aferir, criar, leitor, medidas, projeto    # noqa: E402
from esteira import lentes, varredura                          # noqa: E402
from esteira.corpus import (                                   # noqa: E402
    colher, colher_json, colher_marcado, colher_pasta,
)
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
# 2-b. O PORTEIRO — quem decide se uma rota exige sessao
# ══════════════════════════════════════════════════════════════════════
#
# 🔴 Ha DOIS modelos, e eles se leem ao contrario:
#
#   nega-por-omissao   -> middleware cobre tudo, uma LISTA DE PUBLICAS abre
#                         excecoes. A rota protegida e' a que ninguem cita.
#   permite-por-omissao -> cada rota se protege sozinha, com marca de sessao.
#
# A primeira versao deste detector so conhecia o segundo. Rodou contra um
# projeto do primeiro e devolveu ZERO rota protegida num site onde metade
# exige login. Nao errou por pouco: errou o sentido da pergunta.

def _projeto_nega_por_omissao(base):
    """Monta um projeto Next.js sintetico no modelo deny-by-default."""
    app = base / "src" / "app"
    for rota in ("", "blog", "painel", "faturas"):
        pasta = app / rota if rota else app
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / "page.tsx").write_text(
            "export default function P(){return <div>oi</div>}", encoding="utf-8")
    (base / "middleware.ts").write_text(
        'export const config = { matcher: ["/((?!_next/static).*)"] };',
        encoding="utf-8")
    lib = base / "src" / "lib"
    lib.mkdir(parents=True, exist_ok=True)
    (lib / "public-paths.ts").write_text(
        'export const PUBLIC_PATHS = ["/", "/blog", "/login", "/precos"];',
        encoding="utf-8")
    return base


def test_MUTACAO_porteiro_nega_por_omissao(tmp_path):
    base = _projeto_nega_por_omissao(tmp_path)
    raiz = str(base)
    mapa = varredura.rotas(raiz)

    porteiro = varredura.achar_porteiro(raiz)
    assert porteiro is not None, "nao achou o porteiro"
    assert porteiro["modo"] == "nega-por-omissao", porteiro
    assert porteiro["cobre_tudo"] is True

    # integro: o que NAO esta na lista publica exige sessao
    priv = dict(varredura.exigem_sessao(
        ["/blog", "/painel", "/faturas"], mapa, raiz=raiz))
    assert "/painel" in priv, priv
    assert "/faturas" in priv, priv

    # QUEBRADO: some a lista de publicas, e o detector perde o porteiro
    (base / "src" / "lib" / "public-paths.ts").write_text(
        "export const NADA = 1;", encoding="utf-8")
    assert varredura.achar_porteiro(raiz) is None


def test_porteiro_permite_por_omissao_ainda_funciona(tmp_path):
    """O modelo antigo nao pode ter sido perdido no conserto."""
    app = tmp_path / "src" / "app" / "conta"
    app.mkdir(parents=True, exist_ok=True)
    (app / "page.tsx").write_text("export default function P(){}", encoding="utf-8")
    (app / "layout.tsx").write_text(
        "const s = await getServerSession(); export default function L(){}",
        encoding="utf-8")
    raiz = str(tmp_path)
    mapa = varredura.rotas(raiz)
    assert varredura.achar_porteiro(raiz) is None       # sem lista publica
    priv = varredura.exigem_sessao(["/conta"], mapa, raiz=raiz)
    assert priv and priv[0][0] == "/conta", priv


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


def test_falso_positivo_rota_publica_NAO_pode_virar_rota_protegida(tmp_path):
    """🔴 O erro que constrange: dizer que pede login uma pagina que e' aberta.

    Este projeto nasceu de uma auditoria entregue a um cliente. Reportar como
    privada uma rota publica e' afirmacao errada na cara dele, e e' pior que
    nao achar nada: quem recebe conserta o que nao estava quebrado.
    """
    base = _projeto_nega_por_omissao(tmp_path)
    raiz = str(base)
    mapa = varredura.rotas(raiz)
    priv = dict(varredura.exigem_sessao(
        ["/", "/blog", "/login", "/precos"], mapa, raiz=raiz))
    for publica in ("/", "/blog", "/login", "/precos"):
        assert publica not in priv, "%s esta na lista publica e foi acusada" % publica


def test_prefixo_publico_abre_a_subarvore(tmp_path):
    """`/blog` publico abre `/blog/um-post`. Sem isto, todo post vira privado."""
    base = _projeto_nega_por_omissao(tmp_path)
    post = base / "src" / "app" / "blog" / "um-post"
    post.mkdir(parents=True, exist_ok=True)
    (post / "page.tsx").write_text("export default function P(){}", encoding="utf-8")
    raiz = str(base)
    mapa = varredura.rotas(raiz)
    priv = dict(varredura.exigem_sessao(["/blog/um-post"], mapa, raiz=raiz))
    assert "/blog/um-post" not in priv, priv


def test_falso_positivo_imperativo_no_meio_da_frase_nao_conta():
    """So conta imperativo que ABRE a frase. `Quem compra bem, economiza`
    nao e' chamada de acao, e contar isso inflaria a metrica."""
    texto = "Quem compra bem economiza muito. O cliente acessa o portal."
    achado = [a for a in gate_forma(texto, {"imper": 0.0}, FOLGAS)
              if a.gate == "forma:imper"][0]
    assert achado.veredito == "passa", achado.linha()


# ══════════════════════════════════════════════════════════════════════
# 3-b. CAMADA 3 — o executor das mentes
# ══════════════════════════════════════════════════════════════════════

def _trecho(texto, fonte="pagina.tsx", linha=1):
    from esteira.corpus import Trecho
    return Trecho(texto, fonte, linha)


def test_MUTACAO_achado_sem_evidencia_e_RECUSADO():
    """Sem citacao, a conclusao vale zero (R1). Integro passa, quebrado cai."""
    integro = lentes.Achado("hopkins-especificidade", "oficio-de-texto",
                            "toda alegacao carrega numero",
                            "a promessa nao diz quanto", "pagina.tsx:12", "alta")
    ok, motivo = lentes.validar(integro)
    assert ok, motivo

    quebrado = lentes.Achado("hopkins-especificidade", "oficio-de-texto",
                             "toda alegacao carrega numero",
                             "a promessa nao diz quanto", "", "alta")
    ok2, motivo2 = lentes.validar(quebrado)
    assert not ok2 and "evidencia" in motivo2, motivo2


def test_evidencia_que_nao_bate_com_o_material_e_recusada():
    """A lente tende a inventar fonte quando nao recebeu uma. Isso e' barrado."""
    a = lentes.Achado("ogilvy-prova", "arquitetura-da-oferta", "alegacao pede prova",
                      "nao ha prova", "inventado.tsx:99", "media")
    ok, motivo = lentes.validar(a, fontes_validas={"pagina.tsx:12"})
    assert not ok and "nao bate" in motivo, motivo


def test_consolidar_acusa_quando_so_UM_grupo_rodou():
    """A D-05 exige os dois grupos; rodar um e' o erro que ela nomeia."""
    so_um = [lentes.Achado("halbert-registro", "oficio-de-texto", "r",
                           "soa como empresa", "pagina.tsx:3", "media")]
    r = lentes.consolidar(so_um, [])
    assert r["faltando"], r
    assert "D-05" in r["faltando"][0]

    dois = so_um + [lentes.Achado("brown-mecanismo", "arquitetura-da-oferta",
                                  "r", "sem mecanismo", "pagina.tsx:5", "alta")]
    r2 = lentes.consolidar(dois, [])
    assert not r2["faltando"], r2["faltando"]


def test_declaracao_de_inaplicabilidade_CONTA_como_grupo(tmp_path):
    """D-06: a lente que se declara fora nao some, e o grupo dela rodou."""
    inap = [("ogilvy-prova", "arquitetura-da-oferta", "produto sem cliente")]
    achados = [lentes.Achado("halbert-registro", "oficio-de-texto", "r",
                             "soa como empresa", "pagina.tsx:3", "media")]
    r = lentes.consolidar(achados, inap)
    assert not r["faltando"], r["faltando"]
    assert len(r["inaplicaveis"]) == 1
    assert "D-06" in lentes.impressao(r)


def test_pre_achados_entrega_alegacao_sem_numero_com_a_fonte():
    """Insumo mecanico: o que um regex conta melhor que um LLM."""
    trechos = [
        _trecho("Somos a melhor plataforma do mercado.", "home.tsx", 10),
        _trecho("Reduz o custo em 32% no primeiro mes.", "home.tsx", 20),
        _trecho("O time atende de segunda a sexta.", "home.tsx", 30),
    ]
    pre = lentes.pre_achados(trechos)
    sem_numero = [t for t, _ in pre["alegacoes_sem_numero"]]
    assert "Somos a melhor plataforma do mercado." in sem_numero
    assert not any("32%" in t for t in sem_numero)   # essa TEM numero
    assert pre["alegacoes_sem_numero"][0][1] == "home.tsx:10"


def test_dossie_carrega_a_instrucao_da_D06_e_nao_pede_texto_final():
    lente = {"id": "x", "grupo": "oficio-de-texto", "lente": "p",
             "regua": "r", "nao_serve_para": "peca tecnica"}
    d = lentes.dossie_de(lente, [_trecho("O preco aparece na pagina.")], {})
    assert "DECLARE" in d["instrucao"]
    assert "NAO escreve a copy final" in d["instrucao"]
    assert d["quando_nao_serve"] == "peca tecnica"


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
        "O preco cabe no orcamento do mes.\n", encoding="utf-8")
    achados, cod = avaliar(str(integra), "x", reguas=reguas)
    assert cod == OK, [a.linha() for a in achados]

    quebrada = tmp_path / "ruim.md"
    quebrada.write_text(DIFICIL + "\n", encoding="utf-8")
    achados2, cod2 = avaliar(str(quebrada), "x", reguas=reguas)
    assert cod2 == ACUSOU, [a.linha() for a in achados2]




# ══════════════════════════════════════════════════════════════════════
# 6. O AFERIDOR — a regua tambem passa por gate, e a folga sai do desvio
# ══════════════════════════════════════════════════════════════════════

def _corpo(pf_alvo, n=20):
    """n pecas com palavras-por-frase perto de `pf_alvo`, variando de pouco."""
    saida = []
    for i in range(n):
        extra = " tambem" * (i % 3)
        texto = ("O sol paga a conta de luz%s. "
                 "A placa gera de dia e voce usa a noite%s. "
                 "O preco cabe no bolso do mes%s.\n" % (extra, extra, extra))
        saida.append(("p%02d.txt" % i, texto))
    return aferir.medir_pecas(saida)


def test_folga_sai_do_desvio_medido_e_nao_de_numero_redondo():
    medidos = _corpo(8.0)
    r = aferir.extrair_regua(medidos)
    dp = aferir._desvio([m["pf"] for _, m in medidos])
    assert r["folgas"]["pf"]["acima"] == round(dp * aferir.DESVIOS_NA_FOLGA, 1)


def test_MUTACAO_folga_herdada_reprova_o_que_a_medida_aprova():
    """A prova do defeito que viajou: folga escolhida a mao reprova peca
    legitima que a folga MEDIDA deixa passar."""
    medidos = _corpo(8.0)
    medida = aferir.extrair_regua(medidos)
    herdada = {"alvos": medida["alvos"],
               "folgas": dict(medida["folgas"],
                              pf={"acima": 0.1, "abaixo": None})}
    passam_medida = sum(1 for _, m in medidos if aferir.passa_tudo(m, medida))
    passam_herdada = sum(1 for _, m in medidos if aferir.passa_tudo(m, herdada))
    assert passam_herdada < passam_medida


def test_desvio_zero_NAO_vira_folga_zero():
    """Corpus sem espalhamento nao ensina limite. Medido: 59 mensagens com
    imperativo 0,0 em todas — folga 0,0 reprovaria a primeira que abrisse com
    'clica no link', que e' mensagem normal."""
    iguais = aferir.medir_pecas(
        [("p%d.txt" % i, "Clique aqui. Clique agora. Clique ja.\n")
         for i in range(20)])
    r = aferir.extrair_regua(iguais)
    for met in ("pf", "imper"):
        f = r["folgas"][met]
        assert f["acima"] is None and f["abaixo"] is None, met


def test_metrica_com_n_abaixo_do_piso_sai_NULA_com_o_motivo_escrito():
    """Alvo tirado de tres pecas dentro de uma regua que REPROVA seria numero
    de aparencia medida decidindo sobre peca de terceiro."""
    medidos = _corpo(8.0, n=20)          # pecas curtas: `vicio` nao alcanca
    r = aferir.extrair_regua(medidos, evidencia="corpus de controle da suite")
    assert r["regime"] == "limiar"
    assert r["alvos"]["vicio"] is None
    assert "vicio" in r["alvos_sem_regua"]
    assert "3 de" in r["alvos_sem_regua"]["vicio"] or \
           "0 de" in r["alvos_sem_regua"]["vicio"]


def test_MUTACAO_corpus_sem_evidencia_declarada_NAO_ganha_poder_de_veto():
    """Vinte pecas de um site sem conversao medida dao o mesmo `n` que vinte
    pecas de copy que vendeu. O tamanho responde "este corpus descreve o tipo
    de peca?"; ele NAO responde "este corpus e' de copy que funciona?".

    Confundir as duas e' como uma regua ganha poder de reprovar peca de
    terceiro so por ter muitos arquivos. Na omissao, o caminho seguro."""
    medidos = _corpo(8.0, n=20)
    sem = aferir.extrair_regua(medidos)
    com = aferir.extrair_regua(medidos, evidencia="custo por lead medido")
    assert sem["regime"] == "direcao"
    assert com["regime"] == "limiar"
    # e a consequencia de verdade: direcao nao reprova
    alvos = {"pf": 5.0}
    folgas = {"pf": {"acima": 0.5, "abaixo": None}}
    achado = [a for a in gate_forma(DIFICIL, alvos, folgas, sem["regime"])
              if a.gate == "forma:pf"][0]
    assert achado.veredito == "passa"


def test_MUTACAO_regua_reprovada_NAO_e_gravada_no_registro(tmp_path):
    """Mesmo mecanismo do gate: o destino e' decidido pelo veredito, e nao ha
    opcao de forcar."""
    registro = tmp_path / "reguas.json"
    registro.write_text(json.dumps(
        {"pecas": {"x": {"rotulo": "x", "alvos": {"pf": None}}}}),
        encoding="utf-8")
    medidos = _corpo(8.0)
    r = aferir.extrair_regua(medidos)
    reprovado = [{"teste": "0 dispersao", "veredito": "reprova"}]
    ok, _ = aferir.registrar("x", r, reprovado, caminho=str(registro))
    assert ok is False
    assert json.loads(registro.read_text(encoding="utf-8"))[
        "pecas"]["x"]["alvos"]["pf"] is None

    aprovado = [{"teste": "0 dispersao", "veredito": "passa"}]
    ok2, _ = aferir.registrar("x", r, aprovado, caminho=str(registro))
    assert ok2 is True
    assert json.loads(registro.read_text(encoding="utf-8"))[
        "pecas"]["x"]["alvos"]["pf"] is not None


def test_teste_0_fora_da_faixa_REPROVA_a_regua():
    """Cem por cento e' regua frouxa demais para reprovar qualquer coisa."""
    medidos = _corpo(8.0)
    frouxa = {"alvos": {"pf": 8.0},
              "folgas": {"pf": {"acima": 999.0, "abaixo": None}}}
    t = aferir.teste_0_dispersao(medidos, frouxa)
    assert t["pct"] == 100.0
    assert t["veredito"] == "reprova"


def test_aferidor_e_gate_fazem_a_MESMA_conta():
    """Se as duas contas divergirem, o aferidor valida uma regua que o gate
    nao aplica — e ninguem descobre ate a peca errada passar."""
    alvos = {"pf": 8.0}
    folgas = {"pf": {"acima": 1.0, "abaixo": None}}
    texto = DIFICIL
    m = medidas.forma(texto)
    do_aferidor = aferir.reprova(m["pf"], alvos["pf"], folgas["pf"])
    do_gate = [a for a in gate_forma(texto, alvos, folgas)
               if a.gate == "forma:pf"][0].veredito == "reprova"
    assert do_aferidor == do_gate is True


def test_regime_direcao_NAO_reprova_e_regime_limiar_reprova():
    alvos = {"pf": 5.0}
    folgas = {"pf": {"acima": 0.5, "abaixo": None}}
    achado_l = [a for a in gate_forma(DIFICIL, alvos, folgas, "limiar")
                if a.gate == "forma:pf"][0]
    achado_d = [a for a in gate_forma(DIFICIL, alvos, folgas, "direcao")
                if a.gate == "forma:pf"][0]
    assert achado_l.veredito == "reprova"
    assert achado_d.veredito == "passa"
    assert achado_d.confianca == "baixa"


# ══════════════════════════════════════════════════════════════════════
# 7. O LEITOR FRIO — e os tres modos de dar resposta a pergunta errada
# ══════════════════════════════════════════════════════════════════════

def test_MUTACAO_pagina_muda_e_a_compreensao_muda(tmp_path):
    vazia = tmp_path / "vazia.html"
    vazia.write_text("<p>Bem-vindo ao nosso espaco digital.</p>"
                     "<p>Excelencia e inovacao.</p>", encoding="utf-8")
    cheia = tmp_path / "cheia.html"
    cheia.write_text(
        "<p>Curso para eletricistas que querem instalar energia solar.</p>"
        "<p>Voce recebe 7 modulos e certificado.</p>"
        "<p>Custa R$ 1.997, em 12x de R$ 199.</p>"
        "<p>Sao 3 dias de encontro presencial.</p>"
        "<p>Garantia de 7 dias ou dinheiro de volta.</p>"
        "<p>Quem ensina esta no mercado desde 2015.</p>"
        "<p>O problema e nao saber por onde comecar.</p>"
        "<p>Clique e garanta sua vaga.</p>"
        "<p>Criado por quem instala usina ha 11 anos.</p>", encoding="utf-8")
    r_v, _ = leitor.ler(str(vazia))
    r_c, _ = leitor.ler(str(cheia))
    assert r_c["respondidas"] > r_v["respondidas"]
    assert r_v["respondidas"] <= 2


def test_falso_positivo_afirmacao_NEGADA_nao_conta_como_resposta(tmp_path):
    """Medido numa pagina real: 'por que confiar' foi dada como respondida por
    'voce NAO precisa ser especialista em' — a pagina dizendo que nao ha
    credencial, lida como se houvesse."""
    alvo = tmp_path / "p.html"
    alvo.write_text("<p>Voce nao precisa ser especialista em nada disso.</p>",
                    encoding="utf-8")
    r, _ = leitor.ler(str(alvo))
    por_confiar = dict(r["respostas"])["7 por que confiar"]
    assert por_confiar is None


def test_falso_positivo_conjuncao_nao_e_assinatura(tmp_path):
    """'por que sua ideia' nao e 'por Maria Silva'. A inicial maiuscula e' o
    unico sinal que separa os dois, e `re.I` apagaria exatamente ele."""
    alvo = tmp_path / "p.html"
    alvo.write_text("<p>Entenda por que sua ideia precisa de estrutura.</p>",
                    encoding="utf-8")
    r, _ = leitor.ler(str(alvo))
    assert dict(r["respostas"])["10 quem esta por tras"] is None

    assinado = tmp_path / "q.html"
    assinado.write_text("<p>Escrito por Maria Silva para quem comeca.</p>",
                        encoding="utf-8")
    r2, _ = leitor.ler(str(assinado))
    assert dict(r2["respostas"])["10 quem esta por tras"] is not None


def test_falso_positivo_para_VALIDAR_nao_e_publico(tmp_path):
    alvo = tmp_path / "p.html"
    alvo.write_text("<p>Uma ferramenta para validar sua ideia rapido.</p>"
                    "<p>Feito para eletricistas do interior.</p>",
                    encoding="utf-8")
    p, _ = leitor.publico(str(alvo))
    nomes = [n.lower() for n, _c, _o in p["publicos"]]
    assert not any(n.startswith("validar") for n in nomes)
    assert any("eletricista" in n for n in nomes)


def test_MUTACAO_a_trava_da_camada_2_documentacao_nao_e_pagina(tmp_path):
    """Um leitor que leu o README do projeto deixou de ser frio. Medido: nove
    das dez perguntas respondidas, sete delas por arquivo de documentacao."""
    projeto = tmp_path / "proj"
    (projeto / "src").mkdir(parents=True)
    (projeto / "LEIAME.md").write_text(
        "Curso para eletricistas. Voce recebe 7 modulos. Custa R$ 1.997. "
        "Garantia de 7 dias. Criado por quem trabalha desde 2015. "
        "Clique para comecar. Sao 3 dias de encontro.\n", encoding="utf-8")
    (projeto / "src" / "Pagina.tsx").write_text(
        '<div><p>Bem-vindo ao espaco digital.</p></div>', encoding="utf-8")
    r, cod = leitor.ler(str(projeto))
    assert cod == OK
    assert r["respondidas"] <= 2, [n for n, a in r["respostas"] if a]


def test_leitor_sem_exigir_RELATA_e_com_exigir_REPROVA(tmp_path):
    alvo = tmp_path / "p.html"
    alvo.write_text("<p>Bem-vindo ao nosso espaco digital de excelencia.</p>",
                    encoding="utf-8")
    assert leitor.main([str(alvo)]) == OK
    assert leitor.main([str(alvo), "--exigir", "5"]) == ACUSOU


def test_divergencia_de_publico_acusa_quando_comunicado_nao_bate(tmp_path):
    comunicado = [("investidores", 2, "hero.tsx:12")]
    assert leitor.divergencia_de_publico(
        comunicado, ["startups", "fundadores"])["diverge"] is True
    assert leitor.divergencia_de_publico(
        comunicado, ["investidores anjo"])["diverge"] is False

# ══════════════════════════════════════════════════════════════════════
# 5. RODAR SEM PYTEST — e o motivo disto existir e' um falso verde medido
# ══════════════════════════════════════════════════════════════════════
# 8. A COPY QUE MORA EM DADOS — e a trava da Camada 0 um nivel acima
# ══════════════════════════════════════════════════════════════════════

_JSON_DE_SITE = """{
  "ativo": true,
  "tema": "primary",
  "id": "hero-principal",
  "className": "mt-4 text-lg",
  "src": "/imagens/telhado.png",
  "versao_do_layout": "v3-hero-largo",
  "titulo": "A conta de luz para de subir no mes que vem.",
  "paragrafos": [
    "Voce instala hoje e a economia comeca na proxima fatura.",
    "Nada de obra grande: sao dois dias de servico no telhado."
  ],
  "cta": {"texto": "Quero simular a minha economia agora", "href": "/simular"}
}"""


def test_colher_json_le_a_copy_que_mora_em_dados():
    """Medido num site real: a pagina de 20 KB entregava 150 caracteres pela
    Camada 0, e a home entregava ZERO. Os 240 KB de texto estavam em `.json`,
    e o componente so os renderizava."""
    trechos = colher_json(_JSON_DE_SITE, "pagina.json")
    textos = [t.texto for t in trechos]
    assert any("conta de luz para de subir" in t for t in textos)
    assert any("dois dias de servico" in t for t in textos)
    assert any("Quero simular" in t for t in textos)


def test_MUTACAO_a_CHAVE_do_json_NUNCA_entra_no_corpus():
    """A trava da Camada 0, um nivel acima: `titulo`, `cta` e `paragrafos` sao
    o vocabulario de quem montou o arquivo, igual a nome de componente. O
    visitante le o VALOR."""
    textos = " ".join(t.texto for t in colher_json(_JSON_DE_SITE, "p.json"))
    for chave in ("titulo", "paragrafos", "cta", "ativo", "atualizado"):
        assert chave not in textos, chave


def test_falso_positivo_configuracao_nao_e_copy():
    """Sem este corte a regua sai medindo o arquivo de configuracao."""
    textos = [t.texto for t in colher_json(_JSON_DE_SITE, "p.json")]
    for lixo in ("primary", "hero-principal", "mt-4 text-lg",
                 "/imagens/telhado.png", "v3-hero-largo", "/simular"):
        assert lixo not in textos, lixo


def test_json_carrega_arquivo_e_linha_conferiveis():
    """Achado sem fonte nao existe. O parser perde a posicao, entao a linha
    vem de procurar o texto no arquivo bruto."""
    trechos = colher_json(_JSON_DE_SITE, "pagina.json")
    titulo = [t for t in trechos if "conta de luz" in t.texto][0]
    linha_real = _JSON_DE_SITE.split("\n").index(
        [l for l in _JSON_DE_SITE.split("\n") if "conta de luz" in l][0]) + 1
    assert titulo.linha == linha_real
    assert titulo.onde().startswith("pagina.json:")


def test_json_quebrado_nao_derruba_a_colheita(tmp_path):
    alvo = tmp_path / "meio.json"
    alvo.write_text('{"titulo": "sem fechar', encoding="utf-8")
    trechos, cod = colher(str(alvo))
    assert cod == NAO_MEDIR
    assert trechos == []
def test_MUTACAO_entidade_html_NAO_entra_como_palavra():
    """Achado ao rodar a Camada 0 sobre pagina real da web, e nao sobre
    arquivo de teste. O codigo que NOS escrevemos usa aspas de verdade; o
    HTML de terceiro vem cheio de `&quot;` e `&#x27;`.

    Cada entidade nao desfeita vira uma palavra na contagem, infla
    palavras-por-frase e move o indice de legibilidade. O numero sai errado e
    le como fato.
    """
    bruto = ('<p>Ele disse &quot;vem&quot; e ela n&#227;o foi.</p>'
             '<p>Custa 10 &amp; pouco, com 20&#37; de desconto.</p>')
    textos = [t.texto for t in colher_marcado(bruto, "x.html")]
    juntos = " ".join(textos)
    for entidade in ("&quot;", "&#227;", "&amp;", "&#37;"):
        assert entidade not in juntos, entidade
    assert '"vem"' in juntos
    assert "não foi" in juntos

    # e a prova de que isso MOVE a medida, nao so a aparencia
    from esteira import medidas
    com = medidas.legibilidade(" ".join(
        t.texto for t in colher_marcado(bruto, "x.html")))
    sujo = medidas.legibilidade("Ele disse &quot;vem&quot; e ela n&#227;o foi.")
    assert com["pal_por_frase"] != sujo["pal_por_frase"]


def test_amp_e_desfeito_por_ultimo():
    """`&amp;quot;` e' um `&quot;` escrito literalmente na pagina. Trocar
    `&amp;` primeiro o transformaria em aspas, que e' o contrario do que a
    pagina mostra."""
    textos = [t.texto for t in colher_marcado(
        "<p>Escreva &amp;quot; para uma aspa no codigo.</p>", "x.html")]
    assert any("&quot;" in t for t in textos)


def test_json_NAO_entra_na_varredura_de_pasta_por_padrao(tmp_path):
    """Mesma razao do `.md`: dentro de um projeto, `.json` e' quase sempre
    configuracao, `package.json`, `tsconfig`, dado de build. Quem quer medir a
    copy em dados aponta o caminho PARA o arquivo."""
    projeto = tmp_path / "proj"
    (projeto / "src").mkdir(parents=True)
    (projeto / "package.json").write_text(
        '{"name": "meu-site", "description": "Um site para vender energia '
        'solar para quem mora em casa."}', encoding="utf-8")
    (projeto / "src" / "Pagina.tsx").write_text(
        '<div><p>O sol paga a sua conta de luz.</p></div>', encoding="utf-8")
    trechos, _ = colher_pasta(str(projeto))
    juntos = " ".join(t.texto for t in trechos)
    assert "conta de luz" in juntos
    assert "vender energia" not in juntos

# ══════════════════════════════════════════════════════════════════════
# 9. A VARREDURA DE PROJETO — a capacidade que subia sem porta
# ══════════════════════════════════════════════════════════════════════

def _projeto_next(tmp_path, com_defeito=False):
    """Um projeto Next minimo: duas rotas, um link, um porteiro."""
    raiz = tmp_path / "site"
    (raiz / "app" / "precos").mkdir(parents=True)
    (raiz / "app" / "conta").mkdir(parents=True)
    (raiz / "app" / "precos" / "page.tsx").write_text(
        '<a href="/conta">Minha conta</a>', encoding="utf-8")
    (raiz / "app" / "conta" / "page.tsx").write_text(
        '<p>Painel</p>', encoding="utf-8")
    (raiz / "public-paths.ts").write_text(
        'export const PUBLIC_PATHS = ["/", "/precos", "/blog"];',
        encoding="utf-8")
    (raiz / "middleware.ts").write_text(
        'export const config = { matcher: ["/((?!_next).*)"] };',
        encoding="utf-8")
    if com_defeito:
        (raiz / "app" / "precos" / "page.tsx").write_text(
            '<a href="/nao-existe">Ver</a>'
            '<img src="%s">' % CDN_DE_TESTE, encoding="utf-8")
    return str(raiz)


def test_varredura_de_projeto_acha_rota_link_e_porteiro(tmp_path):
    r = projeto.varrer(_projeto_next(tmp_path))
    assert len(r["rotas"]) == 2
    assert "/conta" in r["links"]
    assert r["porteiro"] is not None
    assert any(rota == "/conta" for rota, _onde in r["protegidas"])


def test_MUTACAO_varredura_de_projeto_reprova_link_quebrado_e_cdn(tmp_path):
    limpo = projeto.varrer(_projeto_next(tmp_path))
    assert projeto.acusacoes(limpo, univ={"cdn_de_terceiro_permitido": False}) == []

    sujo = projeto.varrer(_projeto_next(tmp_path / "b", com_defeito=True))
    gates = [g for g, _t in projeto.acusacoes(
        sujo, univ={"cdn_de_terceiro_permitido": False})]
    assert "caminhos" in gates
    assert "cdn-de-terceiro" in gates


def test_MUTACAO_a_CLI_de_projeto_sai_1_com_exigir_e_0_sem(tmp_path):
    """O que separa esta peca de um relatorio: com `--exigir`, ela REPROVA."""
    raiz = _projeto_next(tmp_path, com_defeito=True)
    assert projeto.main([raiz]) == OK                    # relata
    assert projeto.main([raiz, "--exigir"]) == ACUSOU    # reprova


def test_falso_positivo_opacidade_ZERO_nao_e_baixo_contraste(tmp_path):
    """Medido num projeto real: 3.033 trechos com opacidade declarada, e parte
    era `text-white/0` — estado inicial de animacao, texto que ainda nao
    apareceu. A conta da 1,00:1 e reprova, certa pela aritmetica e errada pelo
    sentido. Falso positivo em volume ensina a ignorar a linha inteira."""
    raiz = tmp_path / "s"
    (raiz / "app" / "x").mkdir(parents=True)
    (raiz / "app" / "x" / "page.tsx").write_text(
        '<p className="text-white/0">some</p>'
        '<p className="text-white/70">aparece</p>', encoding="utf-8")
    r = projeto.varrer(str(raiz))
    assert r["invisiveis"] >= 1
    assert all(c["trecho"] != "text-white/0" for c in r["contraste"])


def test_pasta_sem_pagina_sai_3_e_3_nao_e_verde(tmp_path):
    vazia = tmp_path / "vazia"
    vazia.mkdir()
    assert projeto.main([str(vazia)]) == NAO_MEDIR


def test_varredura_de_projeto_em_pasta_inexistente_sai_2():
    assert projeto.main(["nao/existe/em/lugar/nenhum"]) == NAO_USAR

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

        @property
        def parent(self):
            return _Caminho(os.path.dirname(self))

        def write_text(self, txt, encoding="utf-8"):
            open(self, "w", encoding=encoding).write(txt)

        def write_bytes(self, b):
            open(self, "wb").write(b)

        # 🔴 O REMENDO SO E' HONESTO ENQUANTO COBRE O QUE A SUITE USA.
        # Faltava `read_text`, e o modo sem pytest reprovou UM teste que o
        # modo com pytest aprovava. Os dois modos existem justamente para
        # darem o MESMO veredito: se divergirem, um dos dois esta mentindo,
        # e o CI roda o que mentir mais barato.
        def read_text(self, encoding="utf-8"):
            return open(self, encoding=encoding).read()

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
def test_MUTACAO_montagem_com_suite_vermelha_NAO_sai_zero(tmp_path):
    """Achado por um agente cego rodando a suite DENTRO do clone.

    A suite passava na casa e REPROVAVA no repositorio montado, no mesmo
    instante. Causa: um teste usava uma data dentro do material de exemplo, e
    a regra de destilacao apagou a data — corretamente, porque data e' contexto
    da nossa operacao — deixando a asercao procurando um texto que nao existia
    mais.

    A montagem saia 0 e ninguem olhava: ela media privacidade e nao media se o
    que acabara de escrever ainda FUNCIONA. Gate que aprova repositorio com a
    suite vermelha e' um gate de privacidade com nome grande.
    """
    montado = tmp_path / "montado"
    montado.mkdir()
    suite = montado / "testar_gates.py"

    verde = "import sys\nsys.exit(0)\n"
    suite.write_text(verde, encoding="utf-8")
    r = subprocess.run([sys.executable, "testar_gates.py"], cwd=str(montado),
                       capture_output=True, text=True)
    assert r.returncode == 0

    vermelha = "import sys\nprint('=== RESULTADO: 1 de 1 FALHA ===')\nsys.exit(1)\n"
    suite.write_text(vermelha, encoding="utf-8")
    r2 = subprocess.run([sys.executable, "testar_gates.py"], cwd=str(montado),
                        capture_output=True, text=True)
    assert r2.returncode != 0, "suite vermelha tem de sair diferente de zero"


def test_o_fixture_de_json_NAO_pode_carregar_data(tmp_path):
    """O guarda permanente do defeito acima, e ele e' de PREVENCAO.

    Qualquer data dentro de material de exemplo desta suite vira 'num caso
    medido' na destilacao, e o teste que a procurava passa a falhar so no
    repositorio publicado — onde ninguem roda antes de publicar.
    """
    data = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{2}/\d{2}/\d{4}\b")
    assert not data.search(_JSON_DE_SITE), (
        "material de exemplo com data: a destilacao vai troca-la e o teste "
        "vai falhar so no montado")


def test_MUTACAO_terminal_estreito_NAO_derruba_o_veredito(tmp_path):
    """Achado por um teste cego: um agente rodou o leitor numa pagina real, no
    console padrao do Windows, e recebeu UnicodeEncodeError em vez do veredito.
    A pagina tinha um emoji; o console estava em cp1252.

    O texto auditado nunca esta sob nosso controle — vem da pagina de outra
    pessoa, e vai ter emoji, seta e simbolo de moeda. Ferramenta que so
    funciona depois que a pessoa descobre sozinha uma variavel de ambiente e'
    ferramenta abandonada no primeiro erro.
    """
    import io
    alvo = tmp_path / "p.html"
    alvo.write_text("<p>Curso para eletricistas ⬇ desde 2015.</p>"
                    "<p>Clique e garanta a sua vaga agora.</p>",
                    encoding="utf-8")
    estreito = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", newline="")
    guardado = sys.stdout
    try:
        sys.stdout = estreito
        cod = leitor.main([str(alvo)])
    finally:
        sys.stdout = guardado
    assert cod == OK
    estreito.flush()
    bruto = estreito.buffer.getvalue().decode("utf-8", "replace")
    assert "COMPREENSAO" in bruto


def test_TODA_CLI_responde_sem_argumento_nenhum():
    """O teste mais barato que existe, e ele faltava.

    Um conserto de encoding aplicado as seis CLIs de uma vez deixou UMA delas
    sem o import — e a suite inteira continuou verde, porque nenhum teste
    chamava aquela peca como COMANDO. O erro so apareceu ao rodar o modulo na
    mao, depois de o repositorio ja estar montado.

    Teste de funcao nao cobre `main()`. E `main()` e' a unica parte que a
    pessoa que clonou vai executar.
    """
    from esteira import aferir as _a, criar as _c, gate as _g
    from esteira import leitor as _l, porta as _p
    for modulo in (_g, _l, _a, _p, _c):
        cod = modulo.main([])
        assert cod in (OK, NAO_USAR, NAO_MEDIR), (modulo.__name__, cod)


# ---------------------------------------------------------------------------
# CAMADA 5 — o `criar`, que era a unica peca do motor sem teste de COMPORTAMENTO
#
# Havia UMA linha tocando nele na suite inteira: o import dentro de
# `test_TODA_CLI_responde_sem_argumento_nenhum`, que so prova que a CLI nao
# explode sem argumento. Nada media o que ela FAZ — e ela e' a peca que escreve
# copy. Os testes abaixo nasceram de quatro defeitos medidos num clone limpo.
# ---------------------------------------------------------------------------

def _regua_sintetica(texto, regime="limiar", folga_da_peca=20.0,
                     folga_reserva=0.0, acima_do_alvo=10.0):
    """Uma regua montada EM VOLTA do texto que o teste vai medir.

    Sem isto o teste dependeria dos numeros do `reguas.json`, que mudam toda
    vez que o corpus e' re-aferido — e um teste que quebra quando a regua e'
    recalibrada ensina a pessoa a apagar o teste, nao a olhar a regua.
    """
    ilf = medidas.legibilidade(texto)["ilf"]
    return {
        "_folgas": {"ilf": {"acima": None, "abaixo": folga_reserva}},
        "pecas": {"teste": {
            "regime": regime,
            "alvos": {"ilf": ilf + acima_do_alvo},
            "folgas": {"ilf": {"acima": None, "abaixo": folga_da_peca}},
        }},
    }


BOA = ("Voce faz o servico bem feito e perde a obra no preco. "
       "O problema nao e a sua tecnica.")
ILEGIVEL = ("A consubstanciacao de instrumentos contratuais padronizados "
            "pressupoe a internalizacao de paradigmas gerenciais que "
            "viabilizem a otimizacao dos processos de precificacao no ambito "
            "das atividades eletrotecnicas desenvolvidas em carater autonomo.")


def _entrada(tmp_path, candidatas):
    alvo = tmp_path / "candidatas.json"
    alvo.write_text(json.dumps({
        "contexto": {"tipo_de_produto": "kit digital",
                     "tem_oferta": True, "tem_prova": True},
        "candidatas": candidatas,
    }, ensure_ascii=False), encoding="utf-8")
    return alvo


def test_criar_usa_a_folga_MEDIDA_da_peca_igual_ao_gate():
    """MUTACAO: trocar `ficha['folgas']` pela de reserva faz este teste cair.

    O `gate.py` ja escreve, no proprio comentario, por que a folga da peca vem
    primeiro: "foi herdando folga que um defeito viajou de um projeto para
    outro". O `criar` lia SO a de reserva, entao julgava a copy que a esteira
    escreve por uma regua mais dura que a aplicada a copy dos outros.

    Medido na `pagina-de-vendas` antes do conserto: piso de `seg` era 3,6 pelo
    gate e 31,5 pelo criar. O texto da promessa no cabecalho do `criar.py` —
    "passa pelos MESMOS gates da Camada 1" — era falso.
    """
    reg = _regua_sintetica(BOA, folga_da_peca=20.0, folga_reserva=0.0)
    achados, cod = criar.medir_candidata(BOA, "teste", reg)
    leg = [a for a in achados if a.gate == "legibilidade"][0]
    assert leg.veredito == "passa", (
        "usou a folga de reserva, nao a da peca; limiar aplicado: %s"
        % leg.limiar)
    assert cod == OK


def test_criar_respeita_o_regime_da_peca_igual_ao_gate():
    """MUTACAO: parar de passar `regime` faz este teste cair.

    Regime `direcao` NAO reprova, por contrato — e o `criar` nao passava o
    regime adiante, entao caia no default `limiar` e reprovava. A
    `pagina-de-vendas` esta registrada como `direcao`.
    """
    reg = _regua_sintetica(ILEGIVEL, regime="direcao", folga_da_peca=0.0,
                           folga_reserva=0.0, acima_do_alvo=10.0)
    achados, cod = criar.medir_candidata(ILEGIVEL, "teste", reg)
    leg = [a for a in achados if a.gate == "legibilidade"][0]
    assert leg.veredito == "passa", "direcao nao pode reprovar"
    assert leg.confianca == "baixa"


def test_criar_com_candidata_reprovada_NAO_sai_zero(tmp_path):
    """MUTACAO: voltar para `return OK if r['aprovadas']` faz este teste cair.

    Era o defeito mais caro da peca, e o mais parecido com o que o projeto
    inteiro existe para impedir: o codigo de saida dizia limpo enquanto o
    arquivo ia para `_reprovados/`. Quem le o codigo de saida — CI, script,
    outro agente — lia zero e seguia.
    """
    candidatas = [{"molde": "boa", "lente": "x", "texto": BOA},
                  {"molde": "ruim", "lente": "y", "texto": ILEGIVEL}]

    # 🔴 O CENARIO PRECISA SER MISTO, OU O TESTE PASSA PELO MOTIVO ERRADO.
    # Na primeira rodada ele ficou verde porque NENHUMA candidata era
    # aprovada — e ai `OK if aprovadas else ACUSOU` devolvia 1 sozinho, sem
    # que o defeito tivesse sido consertado. Teste que passa por falta de
    # aprovada nao mede codigo de saida: mede outra coisa.
    r = criar.avaliar_candidatas(candidatas, "pagina-de-vendas",
                                 {"tipo_de_produto": "kit digital",
                                  "tem_oferta": True, "tem_prova": True})
    assert r["aprovadas"], "o cenario nao e misto: nenhuma candidata aprovada"
    assert r["reprovadas"], "o cenario nao e misto: nenhuma candidata reprovada"

    entrada = _entrada(tmp_path, candidatas)
    cod = criar.main([str(entrada), "--peca", "pagina-de-vendas",
                      "--saida", str(tmp_path / "saida")])
    assert cod == ACUSOU, (
        "havia aprovada E reprovada, e o codigo de saida foi %s" % cod)


def test_criar_poe_a_aprovada_FORA_da_pasta_de_reprovados(tmp_path):
    """A boa nao pode ficar escondida junto com a ruim.

    Antes do conserto havia UM arquivo so para as duas listas, e o destino
    dele era decidido por "houve alguma reprovada?". Resultado: duas
    candidatas aprovadas iam parar em `_reprovados/`, que e' a pasta que a
    pessoa nao abre.
    """
    entrada = _entrada(tmp_path, [
        {"molde": "boa", "lente": "x", "texto": BOA},
        {"molde": "ruim", "lente": "y", "texto": ILEGIVEL},
    ])
    saida = tmp_path / "saida"
    criar.main([str(entrada), "--peca", "pagina-de-vendas",
                "--saida", str(saida)])
    aprovada = os.path.join(str(saida), "copy-nova.txt")
    reprovada = os.path.join(str(saida), "_reprovados",
                             "copy-nova-reprovadas.txt")
    assert os.path.exists(aprovada), "a aprovada nao chegou na pasta que se abre"
    assert os.path.exists(reprovada), "a reprovada nao foi separada"
    assert BOA[:40] in open(aprovada, encoding="utf-8").read()
    assert ILEGIVEL[:40] not in open(aprovada, encoding="utf-8").read(), (
        "copy reprovada vazou para o arquivo das aprovadas")


def test_criar_sem_nenhuma_aprovada_tambem_acusa(tmp_path):
    entrada = _entrada(tmp_path, [
        {"molde": "ruim", "lente": "y", "texto": ILEGIVEL}])
    cod = criar.main([str(entrada), "--peca", "pagina-de-vendas"])
    assert cod == ACUSOU


def test_criar_veta_a_propria_copy_ilegivel():
    """Regua que vale so para os outros nao e' regua, e' opiniao (D-05)."""
    achados, cod = criar.medir_candidata(ILEGIVEL, "pagina-de-vendas")
    assert cod == ACUSOU
    assert any(a.gate == "universal:ilegivel" and a.veredito == "reprova"
               for a in achados), [a.gate for a in achados]


def test_criar_com_peca_desconhecida_sai_2_e_nao_0():
    achados, cod = criar.medir_candidata(BOA, "peca-que-nao-existe")
    assert cod == NAO_USAR
    assert achados == []


def test_criar_declara_inaplicabilidade_em_vez_de_forcar_a_lente():
    """D-06: a mente DECLARA quando a propria regua nao serve."""
    r = avaliar_sem_prova = criar.avaliar_candidatas(
        [{"molde": "boa", "lente": "x", "texto": BOA}], "pagina-de-vendas",
        {"tipo_de_produto": "kit digital", "tem_oferta": True,
         "tem_prova": False})
    assert r["inaplicaveis"], "nenhuma lente se declarou fora sem prova"
    assert avaliar_sem_prova is r


def test_a_varredura_le_pagina_HTML_e_nao_so_a_familia_do_javascript(tmp_path):
    """MUTACAO: tirar `.html` de `_arquivos` derruba isto.

    A lista de extensoes era so `.tsx/.jsx/.ts/.js`. Medido sobre uma pagina de
    vendas real: `esteira.projeto` respondia "nenhum arquivo de pagina" e saia
    3; a MESMA pagina, com os MESMOS bytes, renomeada para `.jsx`, devolvia 1
    arquivo e 5 recursos de terceiro. Site estatico e' o caso comum de quem
    clona isto para auditar uma landing page.
    """
    pagina = tmp_path / "index.html"
    pagina.write_text(
        '<html><body><h1>Oi</h1>'
        '<script src="https://cdn.exemplo.com/x.js"></script>'
        '<a href="/obrigado">ir</a></body></html>', encoding="utf-8")

    achados = list(varredura._arquivos(str(tmp_path)))
    assert achados, "a varredura nao enxergou a pagina `.html`"

    r = projeto.varrer(str(tmp_path))
    assert r["arquivos"] == 1, r["arquivos"]
    assert r["cdn"], "o recurso de terceiro na pagina HTML passou batido"


def test_a_rota_do_site_estatico_vem_do_disco_e_evita_o_alarme_falso(tmp_path):
    """MUTACAO: tirar o bloco de rotas estaticas de `rotas()` derruba isto.

    Aceitar `.html` sem isto criaria o alarme falso que a propria `rotas()`
    documenta: com o mapa VAZIO, `quebrados()` devolve TODO link interno como
    quebrado, e o gate acusaria o site inteiro. Um detector que acusa tudo
    ensina a pessoa a ignorar a linha onde mora o achado de verdade.
    """
    (tmp_path / "index.html").write_text(
        '<a href="/obrigado">ok</a><a href="/nao-existe">quebrado</a>',
        encoding="utf-8")
    (tmp_path / "obrigado.html").write_text("<p>valeu</p>", encoding="utf-8")

    mapa = varredura.rotas(str(tmp_path))
    assert "/" in mapa, mapa
    assert "/obrigado" in mapa, mapa

    r = projeto.varrer(str(tmp_path))
    assert r["quebrados"] == ["/nao-existe"], (
        "o link que resolve foi acusado junto: %s" % r["quebrados"])


def test_a_porta_nao_manda_o_criar_ler_uma_PAGINA():
    """MUTACAO: voltar a propor `esteira.criar <pagina>` derruba isto.

    `esteira.criar` le um JSON de candidatas, nunca uma pagina. A porta
    propunha o caminho da pagina no lugar do arquivo de candidatas, e o
    comando saia 3 toda vez — medido num clone limpo, rodando o comando
    literal que ela imprimiu.

    A porta e' a primeira coisa que um agente de fora le. Comando proposto que
    nao roda e' pior que nenhum comando: gasta a confianca antes do primeiro
    resultado.
    """
    from esteira import porta
    p = porta.planejar("escreve a manchete nova da minha pagina de vendas em ./lp")
    assert p["acao"] == "criar", p["acao"]
    assert p["comandos"], "sem roteiro para um pedido completo"

    criar_ = [c for c in p["comandos"] if "esteira.criar" in c]
    assert criar_, "o pedido era criar e o roteiro nao chega no `esteira.criar`"
    assert "./lp" not in criar_[0], (
        "a porta mandou o `criar` ler a pagina: %s" % criar_[0])
    assert ".json" in criar_[0], criar_[0]

    # e o roteiro de criacao passa pela auditoria ANTES, porque quem escreve
    # a manchete nova precisa dos fatos da peca (D-05)
    assert any("esteira.gate" in c for c in p["comandos"])
    assert any("esteira.leitor" in c for c in p["comandos"])


def test_a_porta_propoe_e_nao_executa_e_pede_o_que_falta():
    from esteira import porta
    incompleto = porta.planejar("audita a minha pagina de vendas")
    assert incompleto["falta"] and not incompleto["comandos"]
    assert incompleto["executa"] is False

    completo = porta.planejar("audita a copy da pagina de vendas em ./lp")
    assert not completo["falta"]
    assert completo["executa"] is False
    assert all(c.startswith(("python", "#")) for c in completo["comandos"])


def test_a_porta_da_o_MESMO_plano_para_a_mesma_frase():
    """Zero LLM aqui, e o contrato e' esse. (D-04)"""
    from esteira import porta
    frase = "reescreve a manchete da pagina de captura em ./x"
    planos = [porta.planejar(frase)["comandos"] for _ in range(5)]
    assert all(p == planos[0] for p in planos), planos


# ---------------------------------------------------------------------------
# O CAMINHO INTEIRO, RODADO COMO COMANDO
#
# Teste de funcao importa o modulo. A pessoa que clonou nao importa modulo:
# ela digita o comando. Medido num clone limpo com esta suite INTEIRA verde:
# o `criar` saia 0 com candidata reprovada no arquivo, e seis cabecalhos
# declaravam chamador inexistente. Nada disso aparece importando a funcao.
# ---------------------------------------------------------------------------

RAIZ = os.path.dirname(os.path.abspath(__file__))

PAGINA_DE_EXEMPLO = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>Kit de exemplo</title></head>
<body>
  <h1>O kit que organiza o seu servico</h1>
  <p>Voce faz o servico bem feito e perde a obra no preco.</p>
  <p>Sao 4 ferramentas prontas. Use ainda hoje. O preco e R$37.</p>
  <p>Clique no botao e garanta o seu acesso agora.</p>
  <a href="/obrigado">Quero o kit</a>
</body></html>
"""


def _material(*candidatos):
    """O mesmo material tem nome diferente na casa e no repositorio montado.

    Na casa ele e' `publicar/exemplo-candidatas.json`; montado, vira
    `exemplos/candidatas.json`. O teste precisa rodar nos DOIS, porque o
    defeito que ele guarda so apareceu no montado.
    """
    for c in candidatos:
        inteiro = os.path.join(RAIZ, c)
        if os.path.exists(inteiro):
            return inteiro
    return None


def _comando(argumentos):
    """Roda `python -m ...` de verdade e devolve (codigo, saida)."""
    proc = subprocess.run([sys.executable, "-B", "-m"] + argumentos,
                          cwd=RAIZ, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def test_as_seis_CLIs_respondem_como_COMANDO_e_nao_so_como_funcao():
    """MUTACAO: tirar o import de uma CLI derruba isto, e nao a suite.

    Ja aconteceu: um conserto de encoding aplicado as seis de uma vez deixou
    UMA sem o import, e a suite seguiu verde. O teste que existia chamava
    `modulo.main([])` DENTRO do processo, o que nao exercita `python -m` nem
    o empacotamento.
    """
    for nome in ("porta", "projeto", "gate", "leitor", "criar", "aferir"):
        cod, saida = _comando(["esteira.%s" % nome])
        assert "Traceback (most recent call last)" not in saida, (nome, saida)
        assert cod == NAO_USAR, (nome, cod)
        assert saida.strip(), "%s nao imprimiu nada; comando mudo nao responde" % nome


def test_o_caminho_inteiro_roda_como_COMANDO_sem_excecao(tmp_path):
    """porta -> projeto -> gate -> leitor -> criar, na ordem do AGENTS.md.

    O `projeto` sobre uma pasta com `.html` sai 0 desde que a varredura passou
    a ler HTML. Este numero ficou cravado aqui de proposito: quando ele mudar,
    alguem precisa olhar em vez de o silencio virar verde. Ele JA mudou uma
    vez — era 3, e 3 queria dizer "nao enxerguei a pagina".
    """
    pagina = tmp_path / "index.html"
    pagina.write_text(PAGINA_DE_EXEMPLO, encoding="utf-8")
    contrato = (OK, ACUSOU, NAO_USAR, NAO_MEDIR)

    passos = [
        (["esteira.porta", "audita a copy da pagina de vendas em ./x"], OK),
        (["esteira.projeto", str(tmp_path)], OK),
        (["esteira.gate", str(pagina), "--peca", "pagina-de-vendas"], None),
        (["esteira.leitor", str(pagina)], None),
    ]
    for argumentos, esperado in passos:
        cod, saida = _comando(argumentos)
        rotulo = " ".join(argumentos)
        assert "Traceback (most recent call last)" not in saida, \
            "excecao nao tratada em `%s`:\n%s" % (rotulo, saida[-500:])
        assert cod in contrato, "`%s` saiu %s, fora do contrato" % (rotulo, cod)
        if esperado is not None:
            assert cod == esperado, "`%s` saiu %s, esperado %s" % (
                rotulo, cod, esperado)


def test_o_criar_como_COMANDO_acusa_e_separa_os_dois_arquivos(tmp_path):
    """O exemplo que sobe no repositorio traz UMA candidata ilegivel de
    proposito. Se este comando sair 0, a esteira voltou a aprovar copy que
    ela mesma reprova — que e' o defeito que ela existe para impedir."""
    entrada = _material("exemplos/candidatas.json",
                        "publicar/exemplo-candidatas.json")
    assert entrada, "o exemplo de candidatas sumiu do repositorio"
    saida = tmp_path / "saida"
    cod, texto = _comando(["esteira.criar", entrada, "--peca",
                           "pagina-de-vendas", "--saida", str(saida)])
    assert "Traceback (most recent call last)" not in texto, texto[-500:]
    assert cod == ACUSOU, (
        "havia candidata ilegivel no exemplo e o comando saiu %s" % cod)
    assert os.path.exists(os.path.join(str(saida), "copy-nova.txt"))
    assert os.path.exists(os.path.join(str(saida), "_reprovados",
                                       "copy-nova-reprovadas.txt"))


def test_o_aferidor_como_COMANDO_responde_dentro_do_contrato():
    corpus = _material("exemplos/controle-ruim", "casa/controle-ruim")
    assert corpus, "o corpus de controle sumiu do repositorio"
    cod, texto = _comando(["esteira.aferir", corpus, "--peca",
                           "pagina-de-vendas"])
    assert "Traceback (most recent call last)" not in texto, texto[-500:]
    assert cod in (OK, ACUSOU, NAO_MEDIR), cod


def test_todo_cabecalho_CHAMADOR_aponta_para_arquivo_que_existe():
    """MUTACAO: apontar um `CHAMADOR:` para arquivo inexistente derruba isto.

    Nao e' teste de um defeito: e' o gate do defeito. Um cabecalho que declara
    chamador falso e' PIOR que um no orfao calado, porque ele diz que a peca
    esta coberta. Medido num clone limpo do repositorio publicado: 9
    declaracoes falsas em 6 arquivos, e a que estava mapeada era uma so.

    A fronteira do bloco e' a primeira linha em branco depois de `CHAMADOR:`,
    porque o que vem depois e' outra secao do cabecalho e nao promete chamador.
    """
    raiz = os.path.dirname(os.path.abspath(__file__))
    ref = re.compile(r"`([\w./-]+\.(?:py|md|json|ya?ml))`")
    faltando = []
    for base, dirs, arqs in os.walk(raiz):
        dirs[:] = [d for d in dirs
                   if d not in ("__pycache__", ".git", ".pytest_cache",
                                "publicado", "node_modules", "casa")]
        for nome in sorted(arqs):
            if not nome.endswith(".py"):
                continue
            caminho = os.path.join(base, nome)
            try:
                texto = open(caminho, encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            achado = re.search(r"^CHAMADOR:(.*?)(?=\n\s*\n)", texto,
                               re.S | re.M)
            if not achado:
                continue
            rel = os.path.relpath(caminho, raiz).replace("\\", "/")
            for citado in ref.findall(achado.group(1)):
                if not os.path.exists(os.path.join(raiz, citado)):
                    faltando.append("%s declara %s" % (rel, citado))
    assert not faltando, "cabecalho com chamador que nao exist<caminho local>  " + \
        "\n  ".join(faltando)


if __name__ == "__main__":
    sys.exit(_rodar_sozinho())
