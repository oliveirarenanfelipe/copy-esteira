# -*- coding: utf-8 -*-
"""A esteira de copy: corpus, medidas, gate, leitor frio."""
import sys


def saida_legivel():
    """Faz a saida do terminal aguentar o texto que a peca auditada contem.

    🔴 ISTO NAO E' ENFEITE, E FOI UM TESTE CEGO QUE ACHOU.
    Um agente que nunca tinha visto este repositorio rodou o leitor frio numa
    pagina real, no console padrao do Windows, e recebeu:

        UnicodeEncodeError: 'charmap' codec can't encode character '\\u2b07'

    Nada a ver com a pagina: a pagina tem um emoji de seta, e o console estava
    em `cp1252`. O comando morreu antes de imprimir o veredito.

    Uma ferramenta que so funciona depois que a pessoa descobre sozinha uma
    variavel de ambiente e' uma ferramenta que a maioria abandona no primeiro
    erro. E o texto auditado NUNCA esta sob nosso controle — ele vem da pagina
    de outra pessoa, e vai ter emoji, seta, simbolo de moeda.

    `errors="replace"` de proposito: um caractere que o terminal nao desenha
    vira um sinal visivel, e o relatorio sai inteiro. Perder um glifo na tela
    e' melhor que perder o veredito.
    """
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            # fluxo redirecionado que nao aceita reconfigurar: seguir assim
            pass
