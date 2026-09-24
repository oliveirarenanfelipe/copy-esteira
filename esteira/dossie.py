# -*- coding: utf-8 -*-
"""CAMADA 3, a PORTA — entrega a quem escreve o que cada mente pergunta.

    python -m esteira.dossie <caminho> --peca <tipo>
    python -m esteira.dossie <caminho> --peca <tipo> --sem-prova
    python -m esteira.dossie <caminho> --peca <tipo> --json

CHAMADOR: a CLI acima, pelo `main()` no fim deste arquivo; `testar_gates.py`;
e as duas portas do repositorio, que citam o comando no roteiro, no mesmo
commit. E' o chamador de `esteira/criar.py` (a funcao `dossies`) e de
`esteira/lentes.py`.

🔴 POR QUE ESTA PECA EXISTE, E O DEFEITO ERA DO TAMANHO DA CAMADA
-------------------------------------------------------------------
`criar.py` define `dossies()`, que monta o dossie de cada lente aplicavel.
Medido no repositorio publicado: NENHUMA CLI a chamava. Os unicos usos eram a
propria definicao, o docstring e um teste.

Efeito: as oito mentes subiam no repositorio, o `criar` dizia quantas lentes
rodaram e quais se declararam inaplicaveis — e o conteudo delas nunca chegava
a quem escreve. A Camada 3 inteira, que e' justamente a parte que AJUDA A
ESCREVER, estava no repositorio sem comando que a alcancasse.

Isso apareceu em dois testes cegos sem ninguem perceber: os agentes escreveram
manchetes boas e nenhum usou as lentes. Eles nao tinham como.

No orfao na peca mais visivel do projeto e' o defeito que este repositorio
inteiro existe para impedir, e ele estava aqui dentro.

🔴 O QUE ESTA PECA NAO FAZ
---------------------------
Ela nao escreve, nao julga e nao chama LLM. Ela monta o material que a lente
recebe, sempre igual para a mesma entrada, e imprime. Quem le e' quem escreve:
voce, ou o agente que abriu o repositorio.

A lente tambem nao escreve a frase final (D-12). Ela devolve diagnostico e
argumento; a frase sai na Camada 5, na gramatica do produto, e passa pelo veto
do `esteira.criar`.

CODIGOS DE SAIDA
    0  montou os dossies
    2  nao deu para USAR — falta caminho, falta `--peca`, tipo desconhecido
    3  nao deu para MEDIR — sem material legivel. NAO e' um verde.
"""
import json
import os
import sys

from esteira import saida_legivel
from esteira import criar as _criar
from esteira.corpus import colher, colher_pasta
from esteira.gate import avaliar, carregar_reguas

OK, ACUSOU, NAO_USAR, NAO_MEDIR = 0, 1, 2, 3


def montar(caminho, peca, contexto=None):
    """(dados, codigo). Os dossies das lentes que se aplicam a este caso."""
    reguas = carregar_reguas() or {}
    if peca not in reguas.get("pecas", {}):
        return None, NAO_USAR

    if os.path.isdir(caminho):
        trechos, cod = colher_pasta(caminho)
    elif os.path.exists(caminho):
        trechos, cod = colher(caminho)
    else:
        return None, NAO_USAR
    if cod != OK or not trechos:
        return None, NAO_MEDIR

    # os fatos medidos entram no dossie para a lente NAO ter de contar o que
    # um medidor ja contou, e para ela receber o numero junto da fonte
    achados, _ = avaliar(caminho, peca, reguas)
    fatos = {a.gate: {"valor": a.valor, "limiar": a.limiar,
                      "veredito": a.veredito}
             for a in achados if a.veredito != "nao-mediu"}

    dados = _criar.dossies(trechos, fatos, contexto or {})
    dados["peca"] = peca
    dados["caminho"] = caminho
    return dados, OK


def impressao(d):
    L = ["CAMADA 3 — o que cada mente pergunta, sobre %s  (peca: %s)"
         % (d["caminho"], d["peca"]), ""]
    L.append("  Isto e' material para QUEM ESCREVE. Nao ha veredito aqui, e a")
    L.append("  lente nao escreve a frase final: ela devolve diagnostico e")
    L.append("  argumento, com a citacao de onde viu. A frase sai depois, e")
    L.append("  passa pelo veto do `python -m esteira.criar`.")
    L.append("")
    L.append("  grupos que se aplicam: %s" % ", ".join(d["grupos"]))
    L.append("  lentes aplicaveis ...: %d" % len(d["dossies"]))
    L.append("")

    pre = d.get("pre_achados") or {}
    L.append("  O QUE O MEDIDOR JA CONTOU, para a lente nao recontar:")
    L.append("    trechos de texto ........ %s" % pre.get("trechos"))
    leg = pre.get("legibilidade") or {}
    L.append("    legibilidade ............ %s  (faixa: %s)"
             % (leg.get("ilf"), leg.get("faixa")))
    fortes = pre.get("alegacoes_fortes") or []
    sem_num = pre.get("alegacoes_sem_numero") or []
    L.append("    alegacoes fortes ........ %d, das quais %d SEM numero"
             % (len(fortes), len(sem_num)))
    for texto, onde in sem_num[:5]:
        L.append("        %s  [%s]" % (texto[:72], onde))
    L.append("")

    for i, dos in enumerate(d["dossies"], 1):
        L.append("  " + "-" * 68)
        L.append("  LENTE %d de %d — %s  (%s)"
                 % (i, len(d["dossies"]), dos["lente"], dos["grupo"]))
        L.append("    pergunta : %s" % dos["pergunta"])
        L.append("    regua    : %s" % dos["regua"])
        L.append("    nao serve: %s" % dos["quando_nao_serve"])
    L.append("")

    fora = d.get("inaplicaveis") or []
    L.append("  DECLARACOES DE INAPLICABILIDADE (D-06): %d" % len(fora))
    for lente, grupo, motivo in fora:
        L.append("    %-22s (%s)" % (lente, grupo))
        L.append("      nao serve aqui: %s" % motivo)
    if not fora:
        L.append("    nenhuma. Todas as lentes se aplicam a este caso.")
    L.append("")
    L.append("  O PROXIMO PASSO e' seu: escreva as candidatas usando estas")
    L.append("  lentes, num JSON, e rode `python -m esteira.criar`. O veto e'")
    L.append("  codigo, e vale para a sua copy igual vale para a dos outros.")
    return "\n".join(L)


def main(argv=None):
    saida_legivel()
    argv = list(sys.argv[1:] if argv is None else argv)
    livres = [a for a in argv if not a.startswith("--")]
    reguas = carregar_reguas() or {}
    if not livres:
        print("uso: python -m esteira.dossie <caminho> --peca <tipo>")
        print("     tipos:", ", ".join(sorted(reguas.get("pecas", {}))))
        print("     entrega o que cada mente pergunta, para VOCE escrever.")
        return NAO_USAR

    peca = None
    if "--peca" in argv:
        i = argv.index("--peca")
        if i + 1 < len(argv):
            peca = argv[i + 1]
    if peca is None:
        print("falta --peca. Pela D-02, o produto se declara antes de medir.")
        print("tipos:", ", ".join(sorted(reguas.get("pecas", {}))))
        return NAO_USAR

    contexto = {"tem_oferta": "--sem-oferta" not in argv,
                "tem_prova": "--sem-prova" not in argv}
    if "--produto" in argv:
        i = argv.index("--produto")
        if i + 1 < len(argv):
            contexto["tipo_de_produto"] = argv[i + 1]

    # o valor de `--peca` e de `--produto` nao e' material
    material = [a for a in livres
                if a != peca and a != contexto.get("tipo_de_produto")]
    if not material:
        print("falta o caminho do material.")
        return NAO_USAR

    dados, cod = montar(material[0], peca, contexto)
    if cod == NAO_USAR:
        print("nao deu para usar: caminho que nao existe, ou peca "
              "desconhecida. NAO DEU PARA USAR (2).")
        return NAO_USAR
    if cod == NAO_MEDIR:
        print("nenhum texto legivel em %s. NAO DEU PARA MEDIR (3)."
              % material[0])
        print("  Gate que nao mede nao aprova — e isto NAO e um verde.")
        return NAO_MEDIR

    if "--json" in argv:
        print(json.dumps(dados, ensure_ascii=False, indent=2, default=str))
    else:
        print(impressao(dados))
    return OK


if __name__ == "__main__":
    sys.exit(main())
