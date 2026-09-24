# -*- coding: utf-8 -*-
"""O AFERIDOR — corpus vira regua, e a regua passa por gate antes de entrar.

    python -m esteira.aferir <pasta-de-pecas> --peca <tipo>
    python -m esteira.aferir <pasta> --peca <tipo> --contra <pasta-de-copy-ruim>
    python -m esteira.aferir <pasta> --peca <tipo> --registrar

CHAMADOR: a CLI acima, pelo `main()` no fim deste arquivo; `testar_gates.py`;
e o aferidor da casa, que fatia o corpus privado e chama esta peca.
E' o chamador de `esteira/medidas.py` e escreve em `esteira/reguas.json`.

Cada arquivo da pasta e' UMA peca. O formato e' `.txt` ou `.md`, texto puro,
uma peca por arquivo — porque medir um arquivo que contem trinta e-mails da o
retrato de um e-mail de trinta mil caracteres, que nao existe.

🔴 POR QUE A REGUA PRECISA DE GATE, IGUAL A COPY
--------------------------------------------------
Regua extraida de corpus entra no registro com o resultado dos cinco testes
colado ao lado, e regua que nao passa NAO e' publicada.

A razao esta medida: a folga de palavras por frase era 2,0, herdada de outro
projeto. O desvio real do corpus era 2,3. A folga estava ABAIXO do
espalhamento natural do material e reprovava oito de quarenta e sete pecas
legitimas. A folga estava errada, nao o corpus — e sem o teste da dispersao
esse defeito viajaria para dentro da ferramenta como se fosse regua.

OS CINCO TESTES
    0  dispersao          a mediana descreve o conjunto de onde saiu?
    1  validacao cruzada  extraida de metade, ela aprova a outra metade?
    2  discriminacao      ela reprova copy reconhecidamente ruim?
    3  falso positivo     ela deixa passar peca boa que nao estava no corpus?
    4  cruzada            a regua de um grupo aprova a copy de outro?

🔴 O teste 0 parece circular e nao e'. O argumento contra ele era que rodar a
regua contra o proprio corpus passaria cem por cento por construcao. Medido:
deu sessenta e seis por cento. O corpus tem folga, as pecas se espalham, e o
numero nao e' garantido. Cem por cento seria regua frouxa demais para reprovar
qualquer coisa; vinte seria regua que nao descreve o material de onde saiu.

E a armadilha, dita na cara: validar a regua contra o corpus de onde ela saiu
prova COERENCIA, nao qualidade. O teste 0 sozinho nao basta, e foi por isso
que os outros quatro existem.

CODIGOS DE SAIDA
    0  extraiu a regua, e ela passou nos testes que rodaram
    1  ACUSOU — a regua nao passou num teste, e nao entra no registro
    2  nao deu para USAR — pasta que nao existe, tipo de peca desconhecido
    3  nao deu para MEDIR — pasta vazia, pecas sem frase. NAO e' um verde.
"""
import json
import os
import sys

from esteira import saida_legivel
from esteira import medidas

AQUI = os.path.dirname(os.path.abspath(__file__))
REGUAS = os.path.join(AQUI, "reguas.json")

OK, ACUSOU, NAO_USAR, NAO_MEDIR = 0, 1, 2, 3

# As metricas que saem do corpus. `perg` entra aqui embora o gate a trate
# igual: e' a que mais separa tipo de peca (captura perto de zero, vendas
# perto de sete por cento), entao ela nunca herda alvo de outro tipo.
METRICAS = ("pf", "curtas", "perg", "seg", "imper", "trav", "ilf", "vicio")

# O LADO que cada metrica vigia, e ele e' assimetrico de proposito.
# Frase longa demais reprova; frase curta demais nao. Um generico de mais ou
# menos dez por cento reprova o certo e passa o errado.
LADO = {
    "pf": "acima", "curtas": "abaixo", "perg": "acima", "seg": "abaixo",
    "imper": "acima", "trav": "acima", "ilf": "abaixo", "vicio": "acima",
}

# 🔴 O PISO QUE SEPARA LIMIAR DE DIRECAO.
# Abaixo disto o corpus descreve o gosto de quem escreveu aquelas poucas
# pecas, nao a forma do tipo de peca. Regua assim vira DIRECAO: o registro
# guarda o numero, e o gate NAO reprova por ele.
MINIMO_PARA_LIMIAR = 15

# 🔴 QUANTOS DESVIOS CABEM NA FOLGA, E POR QUE ISSO NAO E' UM NUMERO REDONDO
# ---------------------------------------------------------------------------
# A folga SAI do desvio medido do proprio corpus — essa parte nao se escolhe.
# O que se escolhe, e fica escolhido aqui em cima onde da para discutir, e'
# QUANTOS desvios ela cobre. O criterio foi declarado antes de medir:
#
#   "cada metrica, sozinha, deve deixar passar a grande maioria do corpus
#    legitimo; o que reprova e' o extremo, nao o comum."
#
# Numa cauda so, um desvio deixa passar cerca de 84 por cento e DOIS deixam
# passar cerca de 98. E o gate cobra oito metricas ao mesmo tempo: com um
# desvio, uma peca legitima precisa ter sorte oito vezes seguidas para passar
# inteira. Medido no corpus de e-mail, com um desvio, so 31,8% das pecas do
# PROPRIO corpus passavam, e a regua tirada de metade dele reprovava 81,8% da
# outra metade. Regua assim nao mede a peca: mede o acumulo de oito margens.
#
# O numero abaixo e' o unico parametro escolhido a mao neste arquivo, e ele
# esta declarado em vez de embutido. Quem discordar troca aqui e re-roda os
# cinco testes — que e' exatamente o que eles servem para dizer.
DESVIOS_NA_FOLGA = 2.0

EXTENSOES = (".txt", ".md")


def _mediana(vals):
    s = sorted(vals)
    n = len(s)
    if not n:
        return None
    meio = n // 2
    return s[meio] if n % 2 else (s[meio - 1] + s[meio]) / 2.0


def _desvio(vals):
    """Desvio padrao da populacao, a mao. Zero dependencia (o nucleo nao
    instala nada, e quem clona nao vai instalar)."""
    n = len(vals)
    if n < 2:
        return None
    media = sum(vals) / float(n)
    return (sum((v - media) ** 2 for v in vals) / float(n)) ** 0.5


def ler_pecas(pasta):
    """[(nome, texto)] — um arquivo, uma peca."""
    if not pasta or not os.path.isdir(pasta):
        return None
    saida = []
    for nome in sorted(os.listdir(pasta)):
        if os.path.splitext(nome)[1].lower() not in EXTENSOES:
            continue
        try:
            texto = open(os.path.join(pasta, nome), encoding="utf-8").read()
        except (OSError, UnicodeDecodeError):
            continue
        if texto.strip():
            saida.append((nome, texto))
    return saida


def medir_uma(texto):
    """As oito metricas de uma peca, ou None se nao der para medir.

    `vicio` pode vir None numa peca curta, e isso NAO invalida a peca: sai
    como ausente, e a regua daquela metrica se extrai so de quem a tem.
    """
    f = medidas.forma(texto)
    if f is None:
        return None
    leg = medidas.legibilidade(texto)
    if leg is None:
        return None
    v = medidas.vicio(texto)
    m = {k: f[k] for k in ("pf", "curtas", "perg", "seg", "imper", "trav")}
    m["ilf"] = leg["ilf"]
    m["vicio"] = None if v is None else v["indice"]
    m["frases"] = f["n"]
    m["palavras"] = leg["palavras"]
    return m


def medir_pecas(pecas):
    """[(nome, medidas)] das que deram para medir."""
    saida = []
    for nome, texto in pecas or []:
        m = medir_uma(texto)
        if m is not None:
            saida.append((nome, m))
    return saida


def extrair_regua(medidos, fonte="", minimo=MINIMO_PARA_LIMIAR, evidencia=None):
    """{alvos, folgas, n, n_por_metrica, regime} do corpus medido.

    O alvo e' a MEDIANA, nao a media: uma peca fora da curva puxa a media e
    nao move a mediana, e num corpus de copy sempre ha uma peca fora da curva.

    A folga e' o DESVIO MEDIDO do proprio corpus, nunca um numero redondo
    escolhido por parecer razoavel. Se o numero nao sai do desvio, ele sai de
    um palpite com cara de medida.
    """
    n = len(medidos)
    if not n:
        return None
    # 🔴 O TAMANHO DO CORPUS NAO BASTA PARA DAR PODER DE VETO.
    # `n >= 15` responde "este corpus descreve o tipo de peca, ou o gosto de
    # quem escreveu aquelas poucas?". Ele NAO responde a outra pergunta, que e'
    # anterior: este corpus e' de copy que funciona?
    #
    # As duas se confundem facilmente, e confundi-las e' como uma regua ganha
    # poder de reprovar peca de terceiro so por ter muitos arquivos. Um site
    # com dezoito paginas bem escritas e um site com dezoito paginas medianas
    # dao o mesmo `n`.
    #
    # `evidencia` e' a declaracao de QUE prova existe de que este corpus vale
    # ser perseguido — custo por lead medido, venda, conversao apurada. Sem
    # ela, a regua entra como DIRECAO por mais peca que tenha. E' o caminho
    # seguro na omissao: quem nao declarou, nao reprova.
    grande = n >= minimo
    regime = "limiar" if (grande and evidencia) else "direcao"
    alvos, folgas, n_por, sem_regua = {}, {}, {}, {}
    for met in METRICAS:
        vals = [m[met] for _, m in medidos if m.get(met) is not None]
        n_por[met] = len(vals)
        # 🔴 A METRICA TEM O PROPRIO `n`, E ELE NEM SEMPRE E' O DA REGUA.
        # `vicio` so mede peca acima de um piso de palavras: num corpus de 44
        # e-mails curtos, ele mediu 3. Um alvo tirado de 3 pecas dentro de uma
        # regua que REPROVA seria numero de aparencia medida decidindo sobre
        # peca de terceiro. Fica nulo, e nulo sai como "nao mediu".
        piso = minimo if regime == "limiar" else 2
        if not vals or len(vals) < piso:
            alvos[met] = None
            folgas[met] = {"acima": None, "abaixo": None}
            # 🔴 NULO CALADO E' INDISTINGUIVEL DE ESQUECIMENTO.
            # Quem abre o registro e ve `null` nao sabe se ninguem mediu ou se
            # a medicao nao alcancou. O motivo entra no arquivo, com o numero.
            sem_regua[met] = (
                "sem regua: %d de %d peca(s) alcancaram esta metrica, e o "
                "regime `%s` exige %d. Ausencia declarada, nao alvo inventado."
                % (len(vals), n, regime, piso))
            continue
        alvos[met] = round(_mediana(vals), 1)
        dp = _desvio(vals)
        # 🔴 DESVIO ZERO NAO E' PRECISAO, E' AUSENCIA DE ESPALHAMENTO.
        # Medido: nas 59 mensagens de grupo, TODAS deram 0,0 de imperativo.
        # Alvo 0,0 com folga 0,0 reprova a primeira mensagem que abrir com
        # "clica no link" — que e' mensagem de grupo normal. Um corpus sem
        # variacao nao ensina onde fica o limite; ele so diz que ali ninguem
        # variou. A folga sai nula, e nula NAO reprova.
        folga = (None if not dp else round(dp * DESVIOS_NA_FOLGA, 1))
        folgas[met] = {"acima": folga if LADO[met] == "acima" else None,
                       "abaixo": folga if LADO[met] == "abaixo" else None}
    return {
        "alvos": alvos,
        "folgas": folgas,
        "n": n,
        "n_por_metrica": n_por,
        "alvos_sem_regua": sem_regua,
        "regime": regime,
        "fonte": fonte,
    }


def reprova(valor, alvo, folga):
    """A MESMA conta do gate. Se divergir daqui, o aferidor esta medindo uma
    regua que o gate nao aplica, e ninguem descobre ate a peca errada passar."""
    if valor is None or alvo is None:
        return False
    acima, abaixo = folga.get("acima"), folga.get("abaixo")
    if acima is not None and valor - alvo > acima:
        return True
    if abaixo is not None and alvo - valor > abaixo:
        return True
    return False


def passa_tudo(m, regua):
    for met in METRICAS:
        if reprova(m.get(met), regua["alvos"].get(met),
                   regua["folgas"].get(met) or {}):
            return False
    return True


# ── os cinco testes da regua ────────────────────────────────────────────────

def teste_0_dispersao(medidos, regua):
    """A mediana descreve o conjunto de onde saiu?

    Cem por cento seria regua frouxa demais para reprovar; perto de zero seria
    regua que nao descreve o proprio material. O que informa e' o meio.
    """
    ok = sum(1 for _, m in medidos if passa_tudo(m, regua))
    pct = 100.0 * ok / len(medidos)
    return {"teste": "0 dispersao", "passam": ok, "de": len(medidos),
            "pct": round(pct, 1),
            "veredito": "passa" if 25.0 <= pct <= 95.0 else "reprova",
            "nota": "fora da faixa 25-95: regua frouxa ou que nao descreve o "
                    "proprio corpus" if not 25.0 <= pct <= 95.0 else ""}


def teste_1_validacao_cruzada(medidos, minimo=MINIMO_PARA_LIMIAR):
    """Extraida de metade, ela aprova a outra metade?

    O corte e' por POSICAO alternada, nao aleatorio: o resultado precisa ser o
    mesmo toda vez que alguem rodar, senao nao ha o que colar no registro.
    """
    if len(medidos) < 8:
        return {"teste": "1 validacao cruzada", "veredito": "nao-mediu",
                "nota": "menos de 8 pecas: metade de um corpus pequeno nao e "
                        "corpus"}
    a = [medidos[i] for i in range(0, len(medidos), 2)]
    b = [medidos[i] for i in range(1, len(medidos), 2)]
    r_a = extrair_regua(a, minimo=minimo)
    ok = sum(1 for _, m in b if passa_tudo(m, r_a))
    pct = 100.0 * ok / len(b)
    return {"teste": "1 validacao cruzada", "passam": ok, "de": len(b),
            "pct": round(pct, 1),
            "veredito": "passa" if pct >= 40.0 else "reprova",
            "nota": "" if pct >= 40.0 else
                    "a regua de metade do corpus reprova a outra metade: o "
                    "corpus nao e um conjunto so"}


def teste_2_discriminacao(ruins, regua):
    """Ela reprova copy reconhecidamente ruim?

    Sem este teste, uma regua que aprova tudo passa no teste 0 com nota alta.
    Gate que nao reprova nada nao e' gate.
    """
    if not ruins:
        return {"teste": "2 discriminacao", "veredito": "nao-mediu",
                "nota": "sem corpus de controle ruim"}
    reprovadas = sum(1 for _, m in ruins if not passa_tudo(m, regua))
    pct = 100.0 * reprovadas / len(ruins)
    return {"teste": "2 discriminacao", "reprova": reprovadas, "de": len(ruins),
            "pct": round(pct, 1),
            "veredito": "passa" if pct >= 50.0 else "reprova",
            "nota": "" if pct >= 50.0 else
                    "deixou passar mais da metade da copy ruim"}


def teste_3_falso_positivo(boas_de_fora, regua):
    """Ela deixa passar peca boa que nao estava no corpus?

    E' o teste que mede o custo de errar para o lado de reprovar. Uma regua
    que reprova o que e' bom some do uso na segunda semana.
    """
    if not boas_de_fora:
        return {"teste": "3 falso positivo", "veredito": "nao-mediu",
                "nota": "sem peca boa de fora do corpus"}
    ok = sum(1 for _, m in boas_de_fora if passa_tudo(m, regua))
    pct = 100.0 * ok / len(boas_de_fora)
    return {"teste": "3 falso positivo", "passam": ok, "de": len(boas_de_fora),
            "pct": round(pct, 1),
            "veredito": "passa" if pct >= 50.0 else "reprova",
            "nota": "" if pct >= 50.0 else
                    "reprova peca boa que nao estava no corpus"}


def teste_4_cruzada(regua, outros):
    """A regua de um grupo aprova a copy de outro?

    `outros` e' [(rotulo, medidos)]. Responde a pergunta que decide a forma do
    registro: existe UMA regua de copy boa, ou existem varias? Se a regua de um
    grupo reprovar a copy de outro, o registro precisa de campo de escola, e
    nao so de tipo de peca.

    🔴 O OUTRO GRUPO TEM DE SER DO MESMO TIPO DE PECA, e essa linha custou uma
    leitura errada: rodar a regua de anuncio contra um corpus de e-mail
    reprovou 71 por cento, e isso nao diz nada sobre escola de escrita — diz
    que anuncio e e-mail sao pecas diferentes, que e' a premissa do registro
    inteiro. Numero que confirma a premissa nao testa nada.
    """
    if not outros:
        return {"teste": "4 cruzada", "veredito": "nao-mediu",
                "nota": "so um grupo no corpus: nao ha com quem cruzar"}
    linhas = []
    for rotulo, medidos in outros:
        if not medidos:
            continue
        ok = sum(1 for _, m in medidos if passa_tudo(m, regua))
        linhas.append((rotulo, ok, len(medidos),
                       round(100.0 * ok / len(medidos), 1)))
    if not linhas:
        return {"teste": "4 cruzada", "veredito": "nao-mediu",
                "nota": "nenhum outro grupo deu para medir"}
    pior = min(l[3] for l in linhas)
    return {"teste": "4 cruzada", "linhas": linhas, "pior": pior,
            "veredito": "passa" if pior >= 25.0 else "reprova",
            "nota": "" if pior >= 25.0 else
                    "a regua de um grupo reprova quase tudo do outro: nao ha "
                    "uma regua de copy boa, ha varias"}


def rodar_os_cinco(medidos, regua, ruins=None, boas_de_fora=None, outros=None):
    return [
        teste_0_dispersao(medidos, regua),
        teste_1_validacao_cruzada(medidos),
        teste_2_discriminacao(ruins or [], regua),
        teste_3_falso_positivo(boas_de_fora or [], regua),
        teste_4_cruzada(regua, outros or []),
    ]


def registrar(peca, regua, testes, caminho=REGUAS):
    """Escreve a regua no registro. 🔴 Regua reprovada NAO e' gravada.

    Mesmo mecanismo do gate: o destino e' decidido pelo veredito, e nao ha
    opcao de forcar, porque a opcao de forcar e' como o gate morre.
    """
    if any(t["veredito"] == "reprova" for t in testes):
        return False, "regua reprovada num teste: nao entra no registro"
    try:
        reg = json.load(open(caminho, encoding="utf-8"))
    except (OSError, ValueError):
        return False, "registro ilegivel"
    ficha = reg.get("pecas", {}).get(peca)
    if ficha is None:
        return False, "tipo de peca desconhecido: %s" % peca

    # 🔴 REGUA NOVA NAO REBAIXA A QUE JA ESTA NO REGISTRO.
    # Achado por um agente cego que rodou `--registrar` para ver o efeito: com
    # 12 pecas ele quase substituiu a regua de `anuncio`, que tinha n=35 e
    # regime `limiar` — poder de veto, discriminacao medida —, por uma de
    # regime `direcao`, que nao veta nada.
    #
    # O cabecalho desta funcao ja dizia "nao ha opcao de forcar, porque a
    # opcao de forcar e' como o gate morre". Faltava perceber que APAGAR a
    # regua forte com uma fraca e' a mesma morte, so que pela porta de tras:
    # o registro fica com cara de atualizado e perde o veto.
    #
    # Corpus MAIOR e' o unico caminho para trocar. Menor nao passa.
    antes_regime = ficha.get("regime")
    antes_n = ficha.get("n") or 0
    agora_n = regua.get("n") or 0
    if antes_regime == "limiar" and regua.get("regime") != "limiar":
        return False, ("a regua no registro e' `limiar` (n=%s) e esta e'"
                       " `%s` (n=%s). Regua nova nao rebaixa a antiga: junte"
                       " mais pecas." % (antes_n, regua.get("regime"), agora_n))
    if agora_n < antes_n:
        return False, ("o registro tem n=%s e esta traz n=%s. Regua nova nao"
                       " encolhe o corpus da antiga." % (antes_n, agora_n))

    ficha["alvos"] = regua["alvos"]
    ficha["folgas"] = regua["folgas"]
    ficha["n"] = regua["n"]
    ficha["n_por_metrica"] = regua["n_por_metrica"]
    ficha["alvos_sem_regua"] = regua["alvos_sem_regua"]
    ficha["regime"] = regua["regime"]
    ficha["fonte"] = regua["fonte"] or ficha.get("fonte", "")
    ficha["testes"] = [{k: v for k, v in t.items() if k != "linhas"}
                       for t in testes]
    with open(caminho, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(reg, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return True, "registrado"


def impressao(peca, regua, testes):
    L = ["REGUA DE `%s` — extraida de %d peca(s), regime %s"
         % (peca, regua["n"], regua["regime"]), ""]
    L.append("  %-8s %8s %8s %8s   %s"
             % ("metrica", "alvo", "folga", "n", "lado vigiado"))
    for met in METRICAS:
        alvo = regua["alvos"].get(met)
        f = regua["folgas"].get(met) or {}
        folga = f.get("acima") if f.get("acima") is not None else f.get("abaixo")
        L.append("  %-8s %8s %8s %8d   %s"
                 % (met,
                    "-" if alvo is None else "%.1f" % alvo,
                    "-" if folga is None else "%.1f" % folga,
                    regua["n_por_metrica"].get(met, 0),
                    LADO[met]))
    L.append("")
    L.append("  OS CINCO TESTES DA REGUA")
    for t in testes:
        detalhe = ""
        if "pct" in t:
            chave = "reprova" if "reprova" in t else "passam"
            detalhe = "%d de %d  (%.1f%%)" % (t.get(chave, 0), t["de"], t["pct"])
        elif "pior" in t:
            detalhe = "pior grupo: %.1f%%" % t["pior"]
        L.append("    %-22s %-10s %s" % (t["teste"], t["veredito"].upper(),
                                         detalhe))
        for linha in t.get("linhas", []):
            L.append("        %-24s %d de %d  (%.1f%%)" % linha)
        if t.get("nota"):
            L.append("        %s" % t["nota"])
    return "\n".join(L)


def main(argv=None):
    saida_legivel()
    argv = list(sys.argv[1:] if argv is None else argv)

    def opcao(nome):
        if nome in argv:
            i = argv.index(nome)
            if i + 1 < len(argv):
                return argv[i + 1]
        return None

    valores = set()
    for opt in ("--peca", "--contra", "--fora", "--fonte"):
        v = opcao(opt)
        if v is not None:
            valores.add(v)
    livres = [a for a in argv if not a.startswith("--") and a not in valores]

    if not livres:
        print("uso: python -m esteira.aferir <pasta-de-pecas> --peca <tipo>")
        print("     cada arquivo .txt ou .md da pasta e' UMA peca")
        return NAO_USAR
    pasta = livres[0]

    peca = opcao("--peca")
    if peca is None:
        print("falta --peca. A regua e' POR TIPO: uma regua unica reprova")
        print("justamente a peca que esta certa.")
        return NAO_USAR

    pecas = ler_pecas(pasta)
    if pecas is None:
        print("pasta que nao existe: %s. NAO DEU PARA USAR (2)." % pasta)
        return NAO_USAR
    medidos = medir_pecas(pecas)
    if not medidos:
        print("nenhuma peca deu para medir em %s. NAO DEU PARA MEDIR (3)." % pasta)
        print("  Gate que nao mede nao aprova — e isto NAO e um verde.")
        return NAO_MEDIR

    regua = extrair_regua(medidos, fonte=opcao("--fonte") or "")
    ruins = medir_pecas(ler_pecas(opcao("--contra")))
    fora = medir_pecas(ler_pecas(opcao("--fora")))
    testes = rodar_os_cinco(medidos, regua, ruins=ruins, boas_de_fora=fora)
    print(impressao(peca, regua, testes))
    print()

    if "--registrar" in argv:
        ok, motivo = registrar(peca, regua, testes)
        print("  registro: %s" % motivo)
        if not ok:
            return ACUSOU
    if any(t["veredito"] == "reprova" for t in testes):
        print("  ACUSOU (1) — a regua nao entra no registro.")
        return ACUSOU
    print("  LIMPO (0) — a regua passou nos testes que deu para rodar.")
    return OK


if __name__ == "__main__":
    sys.exit(main())
