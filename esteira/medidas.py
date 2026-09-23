# -*- coding: utf-8 -*-
"""CAMADA 1 (nucleo) — os fatos, sem LLM e sem dependencia.

    from esteira.medidas import legibilidade, forma, contraste, compor

CHAMADOR: `esteira/gate.py` (veredito com codigo de saida) e `testar_gates.py`
(suite com mutacao). Nasce com os dois, no mesmo commit.

Tudo aqui e' aritmetica sobre texto e cor. Mesma entrada, mesma saida, sempre.
Nenhuma funcao deste arquivo decide se a copy e' BOA — isso e' julgamento, e
julgamento e' da Camada 3. Aqui so se mede.

JA EXISTIA ALGO ASSIM? Sim, e a F0 o avaliou: `um auditor de copy anterior`
mede as mesmas seis metricas de forma. Veredito: ADOTAR o medidor, DESCARTAR o
veredito. Tres motivos, todos medidos:
  1. os ALVOS de la (`:108-133`) sao do um produto anterior, e a D-01 os mantem fora daqui;
  2. ele nunca reprova — `:731` e' `return 0` incondicional;
  3. nao tem legibilidade em portugues nem contraste.
Alem disso mora em projeto privado alheio, que este repositorio nao importa.
O METODO migra; o arquivo nao.

POR QUE ZERO DEPENDENCIA (D-11)
-------------------------------
Precedente da casa: o `o gerador de conhecimento` escreveu o teste exato de Fisher a
mao em vez de importar `scipy`. E o repositorio vai ser clonado por gente que
nao vai instalar nada: "um gate que so funciona depois de instalar algo e um
gate que a maioria nao liga".

A faixa ESTENDIDA (axe-core, pyphen, trafilatura) mora noutro lugar e, quando
falta, o gate sai 3 declarando o que nao mediu — nunca 0.

🔴 textstat NAO serve aqui, e isso foi medido na F0: as variantes de
`flesch_reading_ease` dele cobrem en/de/es/fr/it/nl/pl/ru. Portugues nao esta
na lista. Chamado sobre texto em portugues, devolve numero com coeficiente de
ingles — numero errado que le como fato.
"""
import re

# ── legibilidade ────────────────────────────────────────────────────────────
# Indice Flesch adaptado ao portugues, Martins/Ghiraldelo/Nunes/Oliveira Jr.
# (ICMC-USP, 1996). O intercepto muda de 206,835 (ingles) para 248,835 porque
# o portugues tem mais silabas por palavra e a formula inglesa o pune.
# ⚠️ GRAU: lida em duas fontes secundarias concordantes; o paper original NAO
# foi aberto. Marcado como `[nao-verificado na fonte primaria]` na F0.
ILF_BASE = 248.835
ILF_PESO_FRASE = 1.015
ILF_PESO_SILABA = 84.6

FAIXAS = ((75, "muito facil"), (50, "facil"), (25, "dificil"),
          (-1e9, "muito dificil"))

VOGAIS = set("aeiouáàâãéêíóôõúüÁÀÂÃÉÊÍÓÔÕÚÜ")

_FIM_DE_FRASE = re.compile(r"[.!?]+")
_PALAVRA = re.compile(r"[A-Za-zÀ-ÿ]+")


def silabas(palavra):
    """Conta nucleos vocalicos. Ditongo conta como um.

    Nao e' um silabador completo do portugues, e nao precisa ser: a formula
    de Flesch pede a contagem de nucleos. O erro de uma palavra isolada cai
    no ruido quando se mede um texto inteiro.

    Quem quiser exatidao de dicionario liga o `pyphen` na faixa estendida.
    """
    p = "".join(c for c in palavra if c.isalpha())
    if not p:
        return 0
    n = 0
    antes_vogal = False
    for c in p:
        e_vogal = c in VOGAIS
        if e_vogal and not antes_vogal:
            n += 1
        antes_vogal = e_vogal
    return max(1, n)


def frases_de(texto):
    return [f.strip() for f in _FIM_DE_FRASE.split(texto) if f.strip()]


def palavras_de(texto):
    return _PALAVRA.findall(texto)


def faixa_de(ilf):
    for piso, nome in FAIXAS:
        if ilf >= piso:
            return nome
    return "muito dificil"


def legibilidade(texto):
    """{ilf, faixa, pal_por_frase, sil_por_palavra, frases, palavras} ou None."""
    frases = frases_de(texto)
    palavras = palavras_de(texto)
    if not frases or not palavras:
        return None
    ppf = len(palavras) / len(frases)
    spp = sum(silabas(w) for w in palavras) / len(palavras)
    ilf = ILF_BASE - ILF_PESO_FRASE * ppf - ILF_PESO_SILABA * spp
    return {
        "ilf": round(ilf, 1), "faixa": faixa_de(ilf),
        "pal_por_frase": round(ppf, 2), "sil_por_palavra": round(spp, 2),
        "frases": len(frases), "palavras": len(palavras),
    }


# ── metricas de forma ───────────────────────────────────────────────────────
# As seis do `o auditor anterior:108-133`, que sao a parte da um projeto anterior que
# generaliza. Os ALVOS de la NAO vieram junto: sao do um produto anterior, e a D-01 os
# mantem fora. Aqui so se mede; o alvo vem do registro de reguas, em dados.
SEGUNDA_PESSOA = re.compile(
    r"\b(voc[êe]s?|teu|tua|teus|tuas|seu|sua|seus|suas|te|ti|contigo|"
    r"vosso|vossa)\b", re.I)

# imperativo de 2a pessoa: as terminacoes mais comuns em chamada de acao
IMPERATIVOS = {
    "clique", "acesse", "baixe", "compre", "assine", "cadastre", "garanta",
    "aproveite", "descubra", "saiba", "veja", "conheca", "conheça", "peca",
    "peça", "solicite", "entre", "comece", "experimente", "teste", "fale",
    "agende", "marque", "receba", "leia", "confira", "escolha", "monte",
    "junte", "participe", "inscreva", "preencha", "envie", "chame",
}

CURTA_ATE = 6          # frase de ate 6 palavras conta como curta


def forma(texto):
    """As seis metricas, em porcentagem, mais o n de frases."""
    frases = frases_de(texto)
    if not frases:
        return None
    palavras = palavras_de(texto)
    if not palavras:
        return None
    n = len(frases)
    curtas = sum(1 for f in frases if len(palavras_de(f)) <= CURTA_ATE)
    perg = texto.count("?")
    imper = 0
    for f in frases:
        ws = palavras_de(f)
        if ws and ws[0].lower() in IMPERATIVOS:
            imper += 1
    trav = texto.count("—") + texto.count(" - ")
    return {
        "n": n,
        "pf": round(len(palavras) / n, 2),
        "curtas": round(100 * curtas / n, 1),
        "perg": round(100 * perg / n, 1),
        "seg": round(100 * len(SEGUNDA_PESSOA.findall(texto)) / n, 1),
        "imper": round(100 * imper / n, 1),
        "trav": round(100 * trav / len(palavras), 1),
    }


# ── contraste ───────────────────────────────────────────────────────────────
# Formula da WCAG 2.x, direto da especificacao. A biblioteca
# `wcag-contrast-ratio` foi DESCARTADA na F0: parada desde 2015, tres funcoes.
WCAG_AA_NORMAL = 4.5
WCAG_AA_GRANDE = 3.0


def luminancia(rgb):
    def canal(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (canal(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(cor1, cor2):
    l1, l2 = luminancia(cor1), luminancia(cor2)
    claro, escuro = max(l1, l2), min(l1, l2)
    return round((claro + 0.05) / (escuro + 0.05), 2)


def compor(frente, fundo, alpha):
    """A cor que o olho ve quando `frente` tem opacidade `alpha` sobre `fundo`.

    🔴 E' o passo que quase todo medidor de contraste pula, e sem ele o achado
    do gabarito e' inalcancavel: `text-white/50` e' branco a 50% sobre video.
    Branco a 50% NAO e' branco. Medir branco puro contra o fundo daria um
    numero bonito e falso.
    """
    a = max(0.0, min(1.0, alpha))
    return tuple(round(f * a + b * (1 - a)) for f, b in zip(frente, fundo))


def contraste_com_alpha(frente, fundo, alpha):
    """Contraste REAL de um texto semitransparente sobre um fundo."""
    return contraste(compor(frente, fundo, alpha), fundo)


def pior_contraste(frente, fundos, alpha=1.0):
    """O pior caso entre varios fundos, que e' o unico que decide.

    Medir um quadro so de um fundo animado nao decide nada. Numa auditoria
    real o MESMO texto deu dois numeros distantes, um por quadro: aceitavel
    no trecho escuro, ilegivel no trecho claro. A media entre eles nao
    descreve nenhum dos dois, e o que o leitor sofre e' o pior.
    """
    if not fundos:
        return None
    return min(contraste_com_alpha(frente, f, alpha) for f in fundos)


def hex_para_rgb(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return None
    try:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


# ── vicio de escrita ────────────────────────────────────────────────────────
# O indice de vicio de escrita, por mil palavras. NAO mede de onde o texto
# veio: mede se ele tem os tiques que fazem o leitor desconfiar.
#
# ORIGEM: os sinais catalogados no `humanizer` (MIT, Copyright 2025 Siqi Chen),
# ja em uso na casa como porteiro de gravacao. O que migra e' a LISTA de
# sinais; o teto de 35 de la NAO migra, e a razao esta medida: aquele teto foi
# calibrado em prosa longa, e copy boa fica perto de 20. Copy tem teto proprio,
# saido do corpus, como manda o registro de reguas.
#
# 🔴 O QUE FICOU DE FORA, E POR QUE ISSO E' PARTE DA MEDIDA
# ---------------------------------------------------------
# Caixa alta (pega sigla tecnica), aspas curvas (convencao tipografica), par
# hifenizado (pega termo tecnico) e a triade de tres itens. A triade saiu
# depois de reprovar texto bom: um regex nao distingue a triade pelo RITMO,
# que e' o tell, de uma enumeracao legitima de tres coisas.
# Contar errado e' pior que nao contar.
TELLS = {
    "nao-X-mas-Y": r"\bn[aã]o\s+(?:[eé]|se trata de|apenas|s[oó])\b"
                   r"[^.!?\n]{2,60}?,?\s*(?:mas|e sim|[eé])\b",
    "frase de efeito": r"\b(no fim do dia|no fim das contas|a verdade [eé] que|"
                       r"leia de novo|pense nisso)\b",
    "discute com ninguem": r"\b(n[aã]o se engane|ao contr[aá]rio do que "
                           r"(?:muitos|voc[eê]) pensa|esque[cç]a (?:tudo )?o que)\b",
    "travessao": r"[—–]",
    "qualificador empilhado": r"\b(pode(?:ria)? (?:ser que )?talvez|talvez possa|"
                              r"geralmente costuma|normalmente tende)\b",
    "voz passiva": r"\b(?:foi|foram|ser[aá]|ser[aã]o|sido|[eé]|s[aã]o)\s+"
                   r"(?!cada\b|nada\b|toda\b|vida\b|medida\b|entrada\b|sa[ií]da\b"
                   r"|d[uú]vida\b|comida\b|jornada\b)"
                   r"\w{4,}(?:ado|ada|ados|adas|ido|ida|idos|idas)\b",
    "palavra generica": r"\b(crucial|fundamental|robusto|robusta|aprofundar|"
                        r"alavancar|primordial|essencial|no entanto|al[eé]m disso|"
                        r"em suma|vale ressaltar|[eé] importante "
                        r"(?:notar|ressaltar|destacar)|em resumo|por fim|"
                        r"dessa forma|portanto)\b",
    "significancia inflada": r"\b(revolucion[aá]?\w*|muda tudo|game[- ]chang\w+|"
                             r"divisor de [aá]guas|nunca mais ser[aá]|"
                             r"transform\w+ completamente)\b",
    "linguagem de venda": r"\b(descubra|desbloqueie|potencialize|turbine|"
                          r"poderos[ao]|incr[ií]vel|impression\w+|surpreendente)\b",
    "evita ser e ter": r"\b(consiste em|configura-se como|apresenta-se como|"
                       r"caracteriza-se por)\b",
    "negrito decorativo": r"\*\*[^*\n]{1,80}\*\*",
    "residuo de chat": r"^\s*(claro!|[oó]tima pergunta|com certeza!|aqui est[aá]|"
                       r"espero que (?:isso )?ajude)",
    "disclaimer de modelo": r"\b(como (?:um )?modelo de linguagem|"
                            r"at[eé] minha [uú]ltima atualiza[cç][aã]o|"
                            r"n[aã]o tenho acesso a)\b",
}
_TELLS_C = {nome: re.compile(pat, re.I | (re.M if nome == "residuo de chat" else 0))
            for nome, pat in TELLS.items()}

# 🔴 SEPARADOR DE SECAO NAO E' PROSA, E ELE SOZINHO DERRUBOU UMA MEDICAO.
# A unica peca que estourou o teto num corpus inteiro tinha 71 travessoes, e
# parte deles era separador de bloco. O tell "travessao" conta pontuacao
# dentro da frase; tres ou mais seguidos sao moldura, e moldura nao e' vicio.
_SEPARADOR = re.compile(r"[—–]{3,}")
_CERCA = re.compile(r"```.*?```", re.S)
_CODIGO = re.compile(r"`[^`\n]+`")
_LINHA_DE_TABELA = re.compile(r"^\|.*$", re.M)
_URL = re.compile(r"https?://\S+")
_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
_TAG = re.compile(r"<[^>]+>")
_FORTE = re.compile(r"<(strong|b)\b[^>]*>(.*?)</\1>", re.S | re.I)
_HTML_SUJO = re.compile(r"<(script|style)\b.*?</\1>|<!--.*?-->", re.S | re.I)
_ENTIDADES = (("&mdash;", "—"), ("&ndash;", "–"), ("&nbsp;", " "),
              ("&quot;", '"'), ("&#39;", "'"), ("&lt;", "<"), ("&gt;", ">"),
              ("&amp;", "&"))

# Abaixo disto o indice e' ruido: num texto de cem palavras, UM travessao vale
# dez pontos. O piso e' declarado em vez de escondido — peca curta demais
# devolve None, e None sai como "nao mediu", nunca como zero.
VICIO_MINIMO_DE_PALAVRAS = 120


def so_prosa(texto):
    """Tira do texto o que nao e' prosa que um humano le.

    Negrito em HTML vira negrito em markdown ANTES de as tags sumirem, para
    que exista UM reconhecedor de negrito e nao dois que divergem calados.
    """
    t = texto
    if "<" in t and re.search(r"<[a-zA-Z!/]", t):
        t = _HTML_SUJO.sub(" ", t)
        t = _FORTE.sub(lambda m: "**%s**" % m.group(2), t)
        t = _TAG.sub(" ", t)
        for ent, char in _ENTIDADES:
            t = t.replace(ent, char)
    t = _FRONTMATTER.sub("", t)
    t = _CERCA.sub(" ", t)
    t = _CODIGO.sub(" ", t)
    t = _LINHA_DE_TABELA.sub(" ", t)
    t = _URL.sub(" ", t)
    t = _SEPARADOR.sub(" ", t)          # moldura, nao pontuacao
    return t


def vicio(texto, minimo=VICIO_MINIMO_DE_PALAVRAS):
    """{indice, palavras, por_tell} por mil palavras, ou None se curto demais.

    None quer dizer NAO MEDIU. Devolver zero para um texto de trinta palavras
    seria um verde que ninguem apurou.
    """
    t = so_prosa(texto)
    palavras = len(_PALAVRA.findall(t))
    if palavras < minimo:
        return None
    por_tell = []
    total = 0
    for nome, rx in _TELLS_C.items():
        n = len(rx.findall(t))
        if n:
            por_tell.append((round(n * 1000.0 / palavras, 1), nome, n))
        total += n
    por_tell.sort(reverse=True)
    return {"indice": round(total * 1000.0 / palavras, 1),
            "palavras": palavras, "por_tell": por_tell}
