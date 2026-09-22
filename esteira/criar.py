# -*- coding: utf-8 -*-
"""CAMADA 5 — as duas saidas, e a criacao passa pelo MESMO gate.

    python -m esteira.criar <candidatas.json> --peca <tipo> [--saida <pasta>]

CHAMADOR: a CLI acima, pelo `main()` no fim deste arquivo; `testar_criar.py`;
e `docs/F4-CRIACAO.md`, que cita o comando e cola a saida.
Esta peca e' o chamador de `esteira/mentes.json`.

JA EXISTIA? Nao. Nada na casa aplica gate a copy que ela mesma escreve. O
`o auditor anterior` mede peca pronta, e ainda assim nunca reprova (`:731`).

FERRAMENTA APROVADA? O `oferta-design.md` ja esta em uso na casa e entra aqui
como LENTE, dentro de `mentes.json`. Ele diagnostica oferta; nao veta texto.

🔴 A REGUA QUE MANDA AQUI
--------------------------
"Auditoria de copy que nao poe manchete melhor na mesa e' critica, nao
trabalho. A criacao nao e' um segundo produto, e' a prova de que a auditoria
entendeu o caso."  (D-05)

E a contrapartida, que e' o que da' peso a ela: a copy que a esteira escreve
passa pelos MESMOS gates da Camada 1. Candidata reprovada nao chega na pasta
de saida, igual a qualquer peca de terceiro. Regua que vale so para os outros
nao e' regua, e' opiniao.

🔴 O QUE ESTA PECA NAO FAZ (D-04 e D-12)
-----------------------------------------
Ela NAO escreve o texto. O texto vem do LLM, na gramatica do produto
declarado. O que esta peca faz e' deterministico: aplica as lentes, exige a
declaracao de inaplicabilidade (D-06), mede cada candidata e VETA.

Quem escreve propoe; quem veta e' codigo.
"""
import json
import os
import sys

from esteira import lentes, medidas
from esteira.gate import (ACUSOU, NAO_MEDIR, NAO_USAR, OK, Achado,
                          carregar_reguas, escrever_saida, gate_forma,
                          gate_legibilidade)

AQUI = os.path.dirname(os.path.abspath(__file__))
MENTES = os.path.join(AQUI, "mentes.json")

# abaixo disto a formula ja chama de "dificil"; manchete ilegivel reprova
# mesmo sem alvo declarado, porque isso nao depende do corpus de ninguem
PISO_UNIVERSAL_ILF = 25


def carregar_mentes(caminho=MENTES):
    try:
        return json.load(open(caminho, encoding="utf-8"))
    except (OSError, ValueError):
        return None


def lentes_aplicaveis(mentes, contexto):
    """(aplicaveis, declaradas_inaplicaveis).

    A D-06 exige que a mente DECLARE quando a propria regua nao serve, em vez
    de forcar. A declaracao entra na saida, nao some.
    """
    aplicaveis, fora = [], []
    tipo = (contexto.get("tipo_de_produto") or "").lower()
    tem_oferta = bool(contexto.get("tem_oferta", True))
    tem_prova = bool(contexto.get("tem_prova", True))
    for m in mentes.get("mentes", []):
        motivo = None
        if not tem_oferta and "sem oferta" in m["nao_serve_para"]:
            motivo = m["nao_serve_para"]
        elif not tem_prova and "sem cliente" in m["nao_serve_para"]:
            motivo = m["nao_serve_para"]
        elif tipo and tipo in m["nao_serve_para"]:
            motivo = m["nao_serve_para"]
        if motivo:
            fora.append((m["id"], m["grupo"], motivo))
        else:
            aplicaveis.append(m)
    return aplicaveis, fora


def grupos_cobertos(aplicaveis):
    return {m["grupo"] for m in aplicaveis}


def dossies(trechos, fatos, contexto, mentes=None):
    """Os dossies da Camada 3: um por lente aplicavel, mais as declaracoes.

    E' a ponte entre esta camada e `esteira/lentes.py`. Quem chama entrega os
    dossies ao LLM, recebe os achados de volta e passa em `lentes.consolidar`,
    que recusa o que vier sem evidencia citada.
    """
    mentes = mentes or carregar_mentes() or {}
    aplicaveis, fora = lentes_aplicaveis(mentes, contexto)
    pre = lentes.pre_achados(trechos)
    return {
        "dossies": [lentes.dossie_de(m, trechos, fatos, pre) for m in aplicaveis],
        "inaplicaveis": fora,
        "grupos": sorted(grupos_cobertos(aplicaveis)),
        "pre_achados": pre,
    }


def medir_candidata(texto, peca, reguas=None):
    """Roda os gates da Camada 1 sobre UMA candidata."""
    reguas = reguas or carregar_reguas()
    ficha = (reguas or {}).get("pecas", {}).get(peca)
    if ficha is None:
        return [], NAO_USAR
    alvos = ficha.get("alvos", {})
    folgas = reguas.get("_folgas", {})
    achados = [gate_legibilidade(texto, alvos.get("ilf"),
                                 folgas.get("ilf") or {})]
    achados += gate_forma(texto, alvos, folgas)

    leg = medidas.legibilidade(texto)
    if leg is not None:
        ruim = leg["ilf"] < PISO_UNIVERSAL_ILF
        achados.append(Achado("universal:ilegivel",
                              "reprova" if ruim else "passa",
                              valor=leg["ilf"], limiar=PISO_UNIVERSAL_ILF,
                              nota="faixa: %s" % leg["faixa"]))
    if any(a.veredito == "reprova" for a in achados):
        return achados, ACUSOU
    if all(a.veredito == "nao-mediu" for a in achados):
        return achados, NAO_MEDIR
    return achados, OK


def avaliar_candidatas(candidatas, peca, contexto, reguas=None, mentes=None):
    """{aprovadas, reprovadas, inaplicaveis, grupos, lentes}."""
    mentes = mentes or carregar_mentes() or {}
    aplicaveis, fora = lentes_aplicaveis(mentes, contexto)
    aprovadas, reprovadas = [], []
    for c in candidatas:
        achados, cod = medir_candidata(c["texto"], peca, reguas)
        registro = dict(c)
        registro["achados"] = achados
        registro["codigo"] = cod
        (aprovadas if cod == OK else reprovadas).append(registro)
    return {
        "aprovadas": aprovadas,
        "reprovadas": reprovadas,
        "inaplicaveis": fora,
        "grupos": sorted(grupos_cobertos(aplicaveis)),
        "lentes": [m["id"] for m in aplicaveis],
    }


def relatorio(r, peca):
    L = ["CAMADA 5 — criacao, peca: %s" % peca, ""]
    L.append("  grupos de mentes que rodaram: %s" % ", ".join(r["grupos"]))
    if len(r["grupos"]) < 2:
        L.append("  ATENCAO: a D-05 exige os DOIS grupos. Rodou %d."
                 % len(r["grupos"]))
    L.append("  lentes aplicadas: %d" % len(r["lentes"]))
    L.append("")
    L.append("  DECLARACOES DE INAPLICABILIDADE (D-06): %d"
             % len(r["inaplicaveis"]))
    for mid, grupo, motivo in r["inaplicaveis"]:
        L.append("    %-22s (%s)" % (mid, grupo))
        L.append("      nao serve aqui: %s" % motivo)
    L.append("")
    L.append("  CANDIDATAS APROVADAS: %d" % len(r["aprovadas"]))
    for c in r["aprovadas"]:
        L.append("    [%s] %s" % (c.get("molde", "?"), c["texto"]))
        for a in c["achados"]:
            if a.veredito != "nao-mediu":
                L.append("        " + a.linha().strip())
    L.append("")
    L.append("  CANDIDATAS REPROVADAS: %d  (nao vao para a pasta de saida)"
             % len(r["reprovadas"]))
    for c in r["reprovadas"]:
        L.append("    [%s] %s" % (c.get("molde", "?"), c["texto"]))
        for a in c["achados"]:
            if a.veredito == "reprova":
                L.append("        " + a.linha().strip())
    return "\n".join(L)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    livres = [a for a in argv if not a.startswith("--")]
    if not livres:
        print("uso: python -m esteira.criar <candidatas.json> --peca <tipo>")
        return NAO_USAR
    peca = None
    if "--peca" in argv:
        i = argv.index("--peca")
        if i + 1 < len(argv):
            peca = argv[i + 1]
    if peca is None:
        print("falta --peca. Pela D-02, o produto se declara antes de escrever.")
        return NAO_USAR
    try:
        dados = json.load(open(livres[0], encoding="utf-8"))
    except (OSError, ValueError):
        print("nao deu para ler as candidatas.")
        return NAO_MEDIR

    r = avaliar_candidatas(dados.get("candidatas", []), peca,
                           dados.get("contexto", {}))
    texto = relatorio(r, peca)
    print(texto)

    saida = None
    if "--saida" in argv:
        i = argv.index("--saida")
        if i + 1 < len(argv):
            saida = argv[i + 1]
    if saida:
        onde = escrever_saida(saida, "copy-nova.txt", texto,
                              bool(r["reprovadas"]))
        print("\n  saida: %s" % onde)
    return OK if r["aprovadas"] else ACUSOU


if __name__ == "__main__":
    sys.exit(main())
