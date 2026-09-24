# -*- coding: utf-8 -*-
"""A VARREDURA DE PROJETO — o que um arquivo sozinho nao mostra.

    python -m esteira.projeto <pasta-do-projeto>
    python -m esteira.projeto <pasta> --exigir

CHAMADOR: a CLI acima, pelo `main()` no fim deste arquivo; o aferidor de gabarito da casa,
que compara a saida daqui com um gabarito medido a mao; e `testar_gates.py`.
E' o chamador de `esteira/varredura.py` e de `esteira/medidas.py`.

🔴 POR QUE ESTA PECA EXISTE, E O DEFEITO QUE ELA CONSERTA E' DE ENTREGA
------------------------------------------------------------------------
`esteira/varredura.py` tem sete detectores que so funcionam olhando o projeto
inteiro — rotas, porteiro de sessao, link que nao resolve, texto sobre fundo
variavel, recurso de terceiro em tempo de execucao, tela que o produto
prescreve e nao entrega. Todos com teste.

E no repositorio publicado NENHUM comando os alcancava. Medido por grep: o
unico lugar que importava `varredura` era a suite de testes. A capacidade
subia inteira, testada, e sem porta.

Isso e' o defeito que esta casa chama de no orfao: a peca existe e ninguem a
chama. Ele nao aparece como erro — aparece como um repositorio que monta, roda
e passa nos testes, faltando o comando que ninguem procurou.

🔴 O QUE ESTES DETECTORES TEM DE DIFERENTE, E E' O QUE OS TORNA UNIVERSAIS
---------------------------------------------------------------------------
Nenhum deles precisa de corpus de ninguem. Dois exemplos:

  · o de tela prescrita nao compara a pagina com regra externa nenhuma: compara
    o produto com o que o PROPRIO produto declara que deveria existir;
  · o de rota protegida le o porteiro do projeto antes de responder, porque ha
    dois modelos de protecao e eles se leem ao contrario.

CODIGOS DE SAIDA
    0  varreu (ou, com --exigir, varreu e nada a acusar)
    1  ACUSOU — com --exigir, achou link quebrado, recurso de terceiro,
       contraste abaixo do minimo ou tela prescrita e ausente
    2  nao deu para USAR — pasta que nao existe
    3  nao deu para MEDIR — nenhum arquivo de pagina na pasta. NAO e' um verde.
"""
import json
import os
import sys

from esteira import saida_legivel
from esteira import medidas, varredura

AQUI = os.path.dirname(os.path.abspath(__file__))
REGUAS = os.path.join(AQUI, "reguas.json")

OK, ACUSOU, NAO_USAR, NAO_MEDIR = 0, 1, 2, 3

# Os quadros de um fundo animado, do escuro ao claro. Sem amostrar o video nao
# ha como cravar a cor real; o que se prova e' a FAIXA e o pior caso — e o
# pior caso e' o unico que decide, porque a media nao descreve nenhum dos dois.
QUADROS = [(10, 10, 14), (60, 60, 66), (120, 120, 128),
           (180, 180, 188), (230, 230, 236)]


def _universal():
    try:
        return json.load(open(REGUAS, encoding="utf-8")).get("universal", {})
    except (OSError, ValueError):
        return {}


def varrer(raiz):
    """Tudo que os detectores de projeto acham. Nao julga: reporta."""
    r = {"raiz": raiz}
    mapa = varredura.rotas(raiz)
    r["rotas"] = mapa

    todos, por_arquivo = set(), {}
    for caminho in varredura._arquivos(raiz):
        ls = varredura.links_internos(caminho)
        if ls:
            por_arquivo[caminho] = ls
            todos.update(ls)
    r["links"] = sorted(todos)
    r["quebrados"] = varredura.quebrados(sorted(todos), mapa)
    r["porteiro"] = varredura.achar_porteiro(raiz)
    r["protegidas"] = varredura.exigem_sessao(sorted(todos), mapa, raiz)
    r["prescrito_ausente"] = varredura.prescrito_e_ausente(raiz, mapa)
    r["cdn"] = varredura.fundo_externo(raiz)

    # contraste: o passo que quase todo medidor pula e' compor a cor sobre o
    # fundo ANTES de medir. Branco a 50 por cento nao e' branco.
    r["contraste"] = []
    r["invisiveis"] = 0
    for caminho in varredura._arquivos(raiz):
        for base, alpha, linha, trecho in varredura.texto_sobre_fundo(caminho):
            # 🔴 OPACIDADE ZERO E' TEXTO ESCONDIDO, NAO TEXTO DE BAIXO
            # CONTRASTE. Medido num projeto real: 3.033 trechos com opacidade
            # declarada, e boa parte era `text-white/0` — estado inicial de
            # animacao, texto que ainda nao apareceu. A conta de contraste
            # sobre ele da 1,00:1 e reprova, corretamente pela aritmetica e
            # erradamente pelo sentido.
            #
            # Falso positivo em volume ensina a pessoa a ignorar a linha
            # inteira, e a linha inteira e' onde mora o achado de verdade.
            if alpha <= 0:
                r["invisiveis"] += 1
                continue
            # 🔴 O PIOR CASO SAI DE `medidas.pior_contraste`, e nao de um
            # `min()` escrito aqui. A conta era a mesma em dois lugares, e a
            # de `medidas` carrega o motivo dela no docstring: a media entre
            # dois quadros nao descreve nenhum dos dois, e o que o leitor
            # sofre e' o pior. Duas copias da mesma conta divergem no dia em
            # que alguem melhora uma delas.
            pares = [medidas.contraste_com_alpha(base, q, alpha)
                     for q in QUADROS]
            r["contraste"].append({
                "arquivo": os.path.basename(caminho), "linha": linha,
                "trecho": trecho, "melhor": max(pares),
                "pior": medidas.pior_contraste(base, QUADROS, alpha),
            })
    r["arquivos"] = len(list(varredura._arquivos(raiz)))
    return r


def acusacoes(r, univ=None):
    """O que a regua UNIVERSAL reprova. Ela nao depende de corpus de ninguem."""
    univ = univ if univ is not None else _universal()
    fora = []
    if r["quebrados"]:
        fora.append(("caminhos", "%d link(s) interno(s) que nao resolvem: %s"
                     % (len(r["quebrados"]), ", ".join(r["quebrados"][:3]))))
    if r["cdn"] and not univ.get("cdn_de_terceiro_permitido", False):
        fora.append(("cdn-de-terceiro",
                     "%d recurso(s) de terceiro em tempo de execucao: %s"
                     % (len(r["cdn"]), r["cdn"][0][0][:60])))
    minimo = univ.get("contraste_minimo", 4.5)
    ruins = [c for c in r["contraste"] if c["pior"] < minimo]
    if ruins:
        pior = min(ruins, key=lambda c: c["pior"])
        fora.append(("contraste",
                     "%d trecho(s) abaixo de %.1f:1 no pior quadro; pior: "
                     "%s:%d com %.2f:1"
                     % (len(ruins), minimo, pior["arquivo"], pior["linha"],
                        pior["pior"])))
    if r["prescrito_ausente"]:
        fora.append(("prescrito-e-ausente",
                     "%d tela(s) que o produto declara e nao entrega: %s"
                     % (len(r["prescrito_ausente"]),
                        r["prescrito_ausente"][0][0])))
    return fora


def impressao(r):
    L = ["VARREDURA DE PROJETO — %s" % r["raiz"], ""]
    L.append("  arquivos de pagina ............ %d" % r["arquivos"])
    L.append("  rotas encontradas ............. %d" % len(r["rotas"]))
    L.append("  links internos declarados ..... %d" % len(r["links"]))
    L.append("  links que NAO resolvem ........ %d  %s"
             % (len(r["quebrados"]), ", ".join(r["quebrados"][:4])))
    p = r["porteiro"]
    L.append("  porteiro de rota .............. %s"
             % (("%s, declarado em %s" % (p["modo"], p["onde"])) if p
                else "nao achei lista de rotas publicas"))
    L.append("  rotas que EXIGEM SESSAO ....... %d" % len(r["protegidas"]))
    for rota, onde in r["protegidas"][:6]:
        L.append("      %-28s protegido por %s" % (rota, onde))
    L.append("  texto sobre fundo variavel .... %d  (%d invisivel(is), fora "
             "da conta)" % (len(r["contraste"]), r.get("invisiveis", 0)))
    for c in sorted(r["contraste"], key=lambda x: x["pior"])[:6]:
        L.append("      %s:%d  %-16s de %.2f:1 a %.2f:1   PIOR %.2f:1"
                 % (c["arquivo"], c["linha"], c["trecho"][:16],
                    c["melhor"], c["pior"], c["pior"]))
    L.append("  recursos de terceiro .......... %d" % len(r["cdn"]))
    for u, onde in r["cdn"][:4]:
        L.append("      %-50s %s" % (u[:50], onde))
    L.append("  prescrito e AUSENTE ........... %d" % len(r["prescrito_ausente"]))
    for rota, onde in r["prescrito_ausente"][:6]:
        L.append("      %-22s declarado em %s" % (rota, onde))
    return "\n".join(L)


def main(argv=None):
    saida_legivel()
    argv = list(sys.argv[1:] if argv is None else argv)
    livres = [a for a in argv if not a.startswith("--")]
    if not livres:
        print("uso: python -m esteira.projeto <pasta-do-projeto> [--exigir]")
        print("     sem --exigir ele relata; com, vira gate e reprova.")
        return NAO_USAR
    raiz = livres[0]
    if not os.path.isdir(raiz):
        print("pasta que nao existe: %s. NAO DEU PARA USAR (2)." % raiz)
        return NAO_USAR

    r = varrer(raiz)
    if not r["arquivos"]:
        print("nenhum arquivo de pagina em %s. NAO DEU PARA MEDIR (3)." % raiz)
        print("  Gate que nao mede nao aprova — e isto NAO e um verde.")
        return NAO_MEDIR
    print(impressao(r))
    print()

    fora = acusacoes(r)
    if "--exigir" not in argv:
        if fora:
            print("  %d ponto(s) fora da regua universal. Rode com --exigir"
                  " para que isto REPROVE:" % len(fora))
            for gate, texto in fora:
                print("      %-20s %s" % (gate, texto))
        else:
            print("  Nada fora da regua universal.")
        print()
        print("  Sem --exigir, a varredura RELATA e nao reprova.")
        return OK

    if fora:
        print("  ACUSOU (1) — %d ponto(s) fora da regua universal:" % len(fora))
        for gate, texto in fora:
            print("      %-20s %s" % (gate, texto))
        return ACUSOU
    print("  LIMPO (0) — nada fora da regua universal.")
    return OK


if __name__ == "__main__":
    sys.exit(main())
