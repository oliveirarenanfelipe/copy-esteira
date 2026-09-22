# -*- coding: utf-8 -*-
"""CAMADA 5, a PORTA — o operador pede em lingua normal, a esteira propoe.

    python -m esteira.porta "audita a copy da minha pagina de vendas em ./lp"

CHAMADOR: a CLI acima, pelo `main()` no fim deste arquivo; `testar_porta.py`;
e `docs/F5-PORTA.md`, que cola as execucoes repetidas.

JA EXISTIA? A casa tem roteadores por LLM (o `copy-chief` do squad, o
`/route`), e eles sao exatamente o que NAO serve aqui — ver abaixo.

🔴 POR QUE O PLANO E' DETERMINISTICO, E ISSO E' O CONTRATO
-----------------------------------------------------------
"Na esteira da VSL o diretor deu respostas diferentes para a mesma entrada,
duas vezes."  (D-04)

Para sugestao que ele revisa, resposta diferente e' aceitavel. Para o PLANO
do que vai rodar, nao: o operador precisa poder repetir o comando e receber a
mesma coisa, senao nao ha como confiar no que leu da primeira vez.

Entao esta peca e' casamento de palavra sobre tabela — zero LLM. E ela NAO
executa nada: propoe, e o o dono do projeto confirma (D-04).

O vocabulario vem de `gatilhos`, o campo que a casa ja usa em skill e
catalogo, e que existe porque a capacidade tem de ser alcancavel pelas
palavras DELE, nao pelas minhas.
"""
import os
import re
import sys
import unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))

OK, ACUSOU, NAO_USAR, NAO_MEDIR = 0, 1, 2, 3

# o que o operador pede, e como ele fala. Lista de pares: a ORDEM e' fixa, e
# e' parte do contrato de determinismo.
ACOES = [
    ("auditar", ("audita", "auditar", "auditoria", "analisa", "analisar",
                 "revisa", "revisar", "o que esta errado", "diagnostica",
                 "confere", "conferir", "checa", "avalia", "avaliar")),
    ("criar", ("escreve", "escrever", "cria", "criar", "reescreve",
               "reescrever", "manchete", "headline", "titulo", "abertura",
               "alternativa", "melhor versao", "proponha", "sugere")),
    ("medir", ("mede", "medir", "legibilidade", "contraste", "metrica")),
]

PECAS = [
    ("pagina-de-vendas", ("pagina de vendas", "pagina de venda", "lp de venda",
                          "sales page", "pagina que vende")),
    ("pagina-de-captura", ("pagina de captura", "captura", "lead magnet",
                           "isca", "landing de captura", "squeeze")),
    ("pagina-institucional", ("institucional", "site", "home", "homepage",
                              "pagina inicial", "landing", "lp")),
    ("email", ("email", "e-mail", "newsletter", "disparo")),
    ("anuncio", ("anuncio", "criativo", "ads", "campanha")),
    ("mensagem", ("whatsapp", "mensagem", "grupo", "telegram")),
]


def _normalizar(t):
    """Minuscula e sem acento, para casar a fala dele com a tabela."""
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _achar(tabela, texto):
    """(chave, gatilho). O gatilho mais LONGO vence.

    O desempate por comprimento e' o que torna o plano estavel: sem ele,
    "pagina de vendas" poderia casar com "lp" ou com "pagina de vendas"
    dependendo da ordem de varredura, e a mesma frase daria planos
    diferentes — que e' o defeito que esta peca existe para nao ter.
    """
    melhor = None
    for chave, gatilhos in tabela:
        for g in gatilhos:
            if g in texto and (melhor is None or len(g) > len(melhor[1])):
                melhor = (chave, g)
    return melhor or (None, None)


_CAMINHO = re.compile(
    r"(?:^|\s)((?:\.{1,2}[/\\]|[/\\]|[A-Za-z]:\\)[^\s\"']+|[\w\-.]+[/\\][^\s\"']*)")


def achar_caminho(pedido):
    m = _CAMINHO.search(pedido)
    return m.group(1).rstrip(".,;") if m else None


def planejar(pedido):
    """O plano, como dado. Mesma entrada, mesmo plano, sempre."""
    t = _normalizar(pedido)
    acao, gatilho_acao = _achar(ACOES, t)
    peca, gatilho_peca = _achar(PECAS, t)
    caminho = achar_caminho(pedido)

    falta = []
    if acao is None:
        falta.append("a acao (auditar, criar ou medir)")
    if peca is None:
        falta.append("o tipo de peca (a D-02 exige declarar o produto)")
    if caminho is None:
        falta.append("o caminho do material")

    comando = None
    if not falta:
        alvo = "esteira.criar" if acao == "criar" else "esteira.gate"
        comando = ("python -m %s %s --peca %s --saida ./saida"
                   % (alvo, caminho, peca))

    return {
        "pedido": pedido,
        "acao": acao,
        "gatilho_acao": gatilho_acao,
        "peca": peca,
        "gatilho_peca": gatilho_peca,
        "caminho": caminho,
        "falta": falta,
        "comando": comando,
        "executa": False,
    }


def impressao(p):
    L = ["PLANO (proposto, NAO executado)", ""]
    L.append('  pedido: "%s"' % p["pedido"])
    L.append("")
    L.append("  acao ........ %s  %s" % (
        p["acao"] or "(nao entendi)",
        ("[por: %s]" % p["gatilho_acao"]) if p["gatilho_acao"] else ""))
    L.append("  peca ........ %s  %s" % (
        p["peca"] or "(nao declarada)",
        ("[por: %s]" % p["gatilho_peca"]) if p["gatilho_peca"] else ""))
    L.append("  material .... %s" % (p["caminho"] or "(nao achei caminho)"))
    L.append("")
    if p["falta"]:
        L.append("  NAO DEU PARA USAR (2). Falta:")
        for f in p["falta"]:
            L.append("    - %s" % f)
    else:
        L.append("  comando proposto:")
        L.append("    %s" % p["comando"])
        L.append("")
        L.append("  Nada foi executado. Confirme para rodar.")
    return "\n".join(L)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print('uso: python -m esteira.porta "o que voce quer, em lingua normal"')
        return NAO_USAR
    p = planejar(" ".join(argv))
    print(impressao(p))
    return NAO_USAR if p["falta"] else OK


if __name__ == "__main__":
    sys.exit(main())
