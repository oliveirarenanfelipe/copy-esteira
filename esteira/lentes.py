# -*- coding: utf-8 -*-
"""CAMADA 3 — o executor das mentes, em dois grupos.

    python -m esteira.lentes <achados.json>
    python -m esteira.lentes <achados.json> --fontes <material.json>

CHAMADOR: a CLI acima, pelo `main()` no fim deste arquivo; `esteira/criar.py`;
`esteira/dossie.py`, que e' a IDA do mesmo caminho; e `testar_gates.py`.
Segundo chamador de `esteira/mentes.json`.

🔴 ESTA E' A VOLTA, E ELA FICOU SEM PORTA ATE num caso medido
----------------------------------------------------
O `esteira.dossie` leva o material ate a lente. `validar` e `consolidar`
recebem o que a lente devolveu e RECUSAM o achado que nao cita evidencia.

Medido por varredura de alcancabilidade no repositorio ja publicado: partindo
de todos os `main()`, nenhum chegava nestas duas funcoes. Elas estavam
implementadas, testadas, e sem comando.

Efeito: a regra que sustenta o projeto inteiro — "achado sem evidencia e'
recusado" — nao tinha como ser aplicada por quem clonou. Um agente podia
escrever dez achados inventados e nada no repositorio os barrava.

E' o mesmo defeito do dossie, na outra ponta do mesmo caminho: eu consertei a
IDA e declarei a camada pronta sem olhar a VOLTA.

JA EXISTIA? `criar.py:59` decide QUAIS lentes se aplicam e `:84` conta os
grupos. Nada montava o dossie que a lente recebe nem validava o que ela
devolve. E' esse o buraco.

FERRAMENTA APROVADA? O orquestrador do catalogo de personas seria o
candidato, e a F0 o descartou: ele roteia por LLM, e a D-04 tira decisao do
LLM. Aqui os dois grupos rodam SEMPRE, sem chefe escolhendo.

🔴 O QUE E' DETERMINISTICO AQUI, E O QUE NAO E'
------------------------------------------------
A analise e' de LLM: e' ela que le a peca pela lente e escreve o achado. Isto
aqui nao tenta substitui-la. O que ele faz, e faz sem LLM nenhum:

  1. monta o DOSSIE que cada lente recebe, igual toda vez;
  2. VALIDA o que voltou — achado sem evidencia citada e' recusado;
  3. garante que os DOIS grupos apareceram (D-05);
  4. carrega as declaracoes de inaplicabilidade para a saida (D-06);
  5. entrega pre-achados mecanicos que a lente usa como insumo, em vez de
     pedir que ela conte coisas que um regex conta melhor.

Assim o LLM faz o que so ele faz, e o veto continua em codigo (D-04).

🔴 E A LENTE NAO ESCREVE O TEXTO FINAL (D-12). Ela devolve diagnostico e
argumento. A frase em portugues sai na Camada 5, com a gramatica do produto.
Mente que escreve direto produz copy traduzida, que e' copy de ninguem.
"""
import json
import sys

import re

from esteira import medidas, saida_legivel

OK, ACUSOU, NAO_USAR, NAO_MEDIR = 0, 1, 2, 3

CONFIANCAS = ("alta", "media", "baixa")

# alegacao que pede numero e nao tem: insumo mecanico para a lente de
# especificidade. Nao e' veredito — e' material para ela julgar.
_SUPERLATIVO = re.compile(
    r"\b(melhor|maior|l[íi]der|refer[êe]ncia|mais r[áa]pido|mais barato|"
    r"n[úu]mero 1|revolucion[áa]ri[ao]|[úu]nic[ao] no|incompar[áa]vel|"
    r"imbat[íi]vel|o mais)\b", re.I)
_TEM_NUMERO = re.compile(r"\d")


class Achado:
    """O que uma lente devolve. Sem evidencia, nao entra."""

    __slots__ = ("lente", "grupo", "regua", "diagnostico", "evidencia",
                 "confianca")

    def __init__(self, lente, grupo, regua, diagnostico, evidencia,
                 confianca="media"):
        self.lente = lente
        self.grupo = grupo
        self.regua = regua
        self.diagnostico = diagnostico
        self.evidencia = evidencia
        self.confianca = confianca

    def linha(self):
        return "  [%s · %s] %s\n      evidencia: %s  (confianca %s)" % (
            self.lente, self.grupo, self.diagnostico, self.evidencia,
            self.confianca)


def pre_achados(trechos):
    """O que um regex conta melhor que um LLM, entregue como insumo.

    Nao decide nada. Poupa a lente de contar, e da a ela a citacao pronta —
    o que faz diferenca porque achado sem `arquivo:linha` e' recusado logo
    abaixo, e uma lente que nao recebeu a fonte tende a inventar uma.
    """
    alegacoes, sem_numero = [], []
    for t in trechos:
        if _SUPERLATIVO.search(t.texto):
            alegacoes.append((t.texto, t.onde()))
            if not _TEM_NUMERO.search(t.texto):
                sem_numero.append((t.texto, t.onde()))
    junto = " ".join(t.texto for t in trechos)
    return {
        "trechos": len(trechos),
        "legibilidade": medidas.legibilidade(junto),
        "forma": medidas.forma(junto),
        "alegacoes_fortes": alegacoes[:20],
        "alegacoes_sem_numero": sem_numero[:20],
    }


def dossie_de(lente, trechos, fatos, pre=None):
    """O que ESTA lente recebe. Mesmo material, mesmo dossie, sempre.

    O dossie carrega a regua da lente e a instrucao da D-06, porque uma lente
    que nao pode declarar inaplicabilidade forca a propria regua no caso — e
    foi assim que dois vereditos falsos entraram numa rodada anterior.
    """
    pre = pre_achados(trechos) if pre is None else pre
    return {
        "lente": lente["id"],
        "grupo": lente["grupo"],
        "pergunta": lente["lente"],
        "regua": lente["regua"],
        "quando_nao_serve": lente["nao_serve_para"],
        "instrucao": (
            "Aplique a sua regua ao material. Se ela nao servir a este caso, "
            "DECLARE isso em vez de forca-la. Todo achado carrega a citacao "
            "de onde ele foi visto. Voce NAO escreve a copy final."),
        "material": [(t.texto, t.onde()) for t in trechos[:120]],
        "fatos_medidos": fatos,
        "pre_achados": pre,
    }


def validar(achado, fontes_validas=None):
    """(ok, motivo). Achado sem evidencia citada vale zero (R1)."""
    if not achado.diagnostico or not achado.diagnostico.strip():
        return False, "sem diagnostico"
    if not achado.evidencia or not str(achado.evidencia).strip():
        return False, "sem evidencia citada"
    if achado.confianca not in CONFIANCAS:
        return False, "confianca fora de %s" % (CONFIANCAS,)
    if fontes_validas is not None:
        alvo = str(achado.evidencia).split()[0].strip(".,;")
        if alvo not in fontes_validas:
            return False, "evidencia nao bate com o material: %s" % alvo
    return True, ""


def consolidar(achados, inaplicaveis, grupos_esperados=2, fontes=None):
    """Junta, valida e diz o que a saida ainda nao pode afirmar."""
    aceitos, recusados = [], []
    for a in achados:
        ok, motivo = validar(a, fontes)
        if ok:
            aceitos.append(a)
        else:
            recusados.append((a, motivo))

    grupos = {a.grupo for a in aceitos} | {g for _, g, _ in inaplicaveis}
    faltando = []
    if len(grupos) < grupos_esperados:
        faltando.append(
            "rodou %d de %d grupos de mentes; a D-05 exige os dois"
            % (len(grupos), grupos_esperados))
    if not aceitos and not inaplicaveis:
        faltando.append("nenhum achado sobreviveu a validacao")

    return {
        "aceitos": aceitos,
        "recusados": recusados,
        "inaplicaveis": inaplicaveis,
        "grupos": sorted(grupos),
        "faltando": faltando,
        "baixa_confianca": [a for a in aceitos if a.confianca == "baixa"],
    }


def impressao(r):
    L = ["CAMADA 3 — as mentes", ""]
    L.append("  grupos que rodaram: %s" % (", ".join(r["grupos"]) or "nenhum"))
    for f in r["faltando"]:
        L.append("  ATENCAO: %s" % f)
    L.append("")
    L.append("  ACHADOS ACEITOS: %d" % len(r["aceitos"]))
    for a in r["aceitos"]:
        L.append(a.linha())
    if r["baixa_confianca"]:
        L.append("")
        L.append("  %d achado(s) de baixa confianca — vao ao cetico antes de"
                 " virar linha de auditoria (D-13)." % len(r["baixa_confianca"]))
    L.append("")
    L.append("  ACHADOS RECUSADOS: %d  (nao entram na saida)"
             % len(r["recusados"]))
    for a, motivo in r["recusados"]:
        L.append("    [%s] %s" % (a.lente, motivo))
    L.append("")
    L.append("  DECLARACOES DE INAPLICABILIDADE (D-06): %d"
             % len(r["inaplicaveis"]))
    for lente, grupo, motivo in r["inaplicaveis"]:
        L.append("    %-22s (%s): %s" % (lente, grupo, motivo))
    return "\n".join(L)


def de_json(dados):
    """Os achados como o LLM os devolve, virando objetos que dao para validar.

    O campo que mais falta e' `evidencia`, e e' justamente o que faz o achado
    existir. Achado sem ele chega aqui, e' RECUSADO, e aparece na lista de
    recusados com o motivo — nunca some em silencio.
    """
    achados = []
    for a in dados.get("achados", []):
        achados.append(Achado(
            lente=a.get("lente", "?"), grupo=a.get("grupo", "?"),
            regua=a.get("regua", ""), diagnostico=a.get("diagnostico", ""),
            evidencia=a.get("evidencia", ""),
            confianca=a.get("confianca", "media")))
    fora = [tuple(x) for x in dados.get("inaplicaveis", []) if len(x) == 3]
    return achados, fora


def main(argv=None):
    saida_legivel()
    argv = list(sys.argv[1:] if argv is None else argv)
    livres = [a for a in argv if not a.startswith("--")]
    if not livres:
        print("uso: python -m esteira.lentes <achados.json>")
        print("     recebe o que as lentes devolveram e RECUSA o achado que")
        print("     nao cita evidencia. O material vai pelo `esteira.dossie`.")
        return NAO_USAR

    try:
        dados = json.load(open(livres[0], encoding="utf-8"))
    except (OSError, ValueError):
        print("nao deu para ler os achados. NAO DEU PARA MEDIR (3).")
        return NAO_MEDIR

    fontes = None
    if "--fontes" in argv:
        i = argv.index("--fontes")
        if i + 1 < len(argv):
            try:
                bruto = json.load(open(argv[i + 1], encoding="utf-8"))
            except (OSError, ValueError):
                print("nao deu para ler as fontes. NAO DEU PARA USAR (2).")
                return NAO_USAR
            # aceita a saida de `esteira.dossie --json`, que traz o material
            material = []
            for d in bruto.get("dossies", []):
                material += [onde for _texto, onde in d.get("material", [])]
            fontes = set(material) or None

    achados, fora = de_json(dados)
    if not achados and not fora:
        print("nenhum achado e nenhuma declaracao no arquivo.")
        print("  Gate que nao mede nao aprova — e isto NAO e um verde. (3)")
        return NAO_MEDIR

    r = consolidar(achados, fora, fontes=fontes)
    print(impressao(r))

    # 🔴 O VEREDITO E' O CODIGO DE SAIDA, igual ao resto da esteira.
    # Achado recusado nao e' aviso: se sobrou algum, este comando ACUSA.
    if r["recusados"] or r["faltando"]:
        return ACUSOU
    return OK


if __name__ == "__main__":
    sys.exit(main())
