# -*- coding: utf-8 -*-
"""CAMADA 2, o LEITOR FRIO — a pagina e' facil de ler, e diz o que ela e'?

    python -m esteira.leitor <caminho>
    python -m esteira.leitor <caminho> --exigir 6
    python -m esteira.leitor <pasta-do-projeto> --publico

CHAMADOR: a CLI acima, pelo `main()` no fim deste arquivo; o aferidor de gabarito da casa,
que usa esta peca para os dois itens do gabarito que a Camada 1 nao alcanca; e
`testar_gates.py`. E' o chamador de `esteira/corpus.py`.

🔴 O NUMERO QUE OBRIGA ESTA CAMADA A EXISTIR
----------------------------------------------
A MESMA pagina, medida por dois instrumentos:

    legibilidade (indice Flesch adaptado) .... 68,7   faixa "facil"
    compreensao (leitor sem contexto) ........ 3 de 10

Facil de ler, e nao diz o que a empresa faz. Nenhum ajuste de limiar de
legibilidade acharia esse defeito, porque legibilidade mede a FORMA da frase e
nao o que ela informa. Uma frase curta, direta e vazia pontua bem.

🔴 O QUE "FRIO" QUER DIZER, E E' A TRAVA DESTA PECA
----------------------------------------------------
O leitor le SO o texto visivel, pela Camada 0. Nome de arquivo, nome de
componente e comentario de codigo sao proibidos aqui com mais forca que em
qualquer outra camada: um leitor que leu `pricing-table.tsx` deixou de ser
frio. O visitante nao tem esse contexto, e e' o visitante que esta sendo
simulado.

E ele NAO julga se a copy e' boa. Ele responde, uma a uma, as dez perguntas
que qualquer pessoa faz ao cair numa pagina pela primeira vez, e diz de qual
trecho tirou cada resposta. Pergunta sem evidencia fica sem resposta — nunca
com uma resposta inventada a partir do que "a pagina provavelmente quis dizer".

🔴 POR QUE ELE FOI CALIBRADO ANTES DE PODER REPROVAR
------------------------------------------------------
Um gate novo que estreia reprovando e' um gate que ninguem confia. Antes de
ganhar poder de veto, este foi rodado contra pecas que JA CONVERTERAM — e o
piso saiu do placar delas, nao de um numero escolhido por parecer exigente.
Gate que reprova o que converteu esta errado sobre o mundo, nao sobre a
pagina. Sem `--exigir`, ele so relata.

CODIGOS DE SAIDA
    0  leu (ou, com --exigir, leu e passou do piso)
    1  ACUSOU — com --exigir, ficou abaixo do piso
    2  nao deu para USAR — caminho que nao existe, extensao sem leitor
    3  nao deu para MEDIR — sem texto visivel. NAO e' um verde.
"""
import os
import re
import sys

from esteira import saida_legivel
from esteira.corpus import colher, colher_pasta

OK, ACUSOU, NAO_USAR, NAO_MEDIR = 0, 1, 2, 3

# 🔴 O PISO, E DE ONDE ELE SAIU.
# Nao e' um numero escolhido: e' o menor placar entre as pecas que ja
# converteram, medidas antes de este gate poder reprovar qualquer coisa.
# A calibragem inteira, peca por peca, esta em `docs/F10-LEITOR-FRIO.md`.
PISO_CALIBRADO = 5

# As dez perguntas, na ordem em que o visitante as faz. Cada uma so e'
# respondida com EVIDENCIA no texto visivel.
#
# ⚠️ O LIMITE DESTA PECA, DITO EM VEZ DE ESCONDIDO: ela mede se a pagina
# RESPONDE a pergunta, nao se a resposta e' boa, verdadeira ou convincente.
# Uma pagina que diz "para todos os publicos" responde a pergunta 2 e responde
# mal. Isso e' julgamento, e julgamento nao e' o que esta camada faz.
AS_DEZ = [
    ("1 o que e isto",
     r"\b(curso|forma[cç][aã]o|treinamento|mentoria|programa|plataforma|"
     r"aplicativo|software|sistema|ferramenta|servi[cç]o|consultoria|"
     r"assinatura|comunidade|ebook|planilha|kit|workshop|imers[aã]o|"
     r"palestra|evento|webin[aá]rio|masterclass)\b"),

    ("2 para quem e",
     r"\b(para (?:quem|voc[eê]|profissionais?|empresas?)|se voc[eê] "
     r"(?:[eé]|trabalha|atua|quer|j[aá])|voltado para|feito para|"
     r"indicado para|destinado a|ideal para|pensado para)\b"),

    ("3 que problema resolve",
     r"\b(problema|dificuldade|dor de cabe[cç]a|sem saber|n[aã]o "
     r"(?:sabe|consegue|d[aá] conta)|perde (?:tempo|dinheiro|cliente)|"
     r"trava|travado|erro|risco|preju[ií]zo|retrabalho|frustra|"
     r"cansado de|cansa[cç]o|inseguran[cç]a|medo de)\b"),

    ("4 o que eu recebo",
     r"(\b(voc[eê] (?:recebe|leva|ganha)|voc[eê] vai (?:ter|receber)|"
     r"est[aá] inclu[ií]d|inclui|acesso a|material de apoio|suporte|"
     r"certificado|m[oó]dulos?|aulas?|encontros?|planilha|modelo)\b"
     r"|\b\d+\s+(?:m[oó]dulos?|aulas?|dias?|encontros?|v[ií]deos?|"
     r"materiais?|ferramentas?)\b)"),

    ("5 quanto custa",
     r"(R\$\s*\d|\b(gr[aá]tis|gratuito|sem custo|de gra[cç]a|investimento "
     r"(?:de|[eé])|por apenas|valor (?:de|[eé])|\d+\s*x\s*de|parcelad)\b)"),

    ("6 quanto tempo leva",
     r"\b(em \d+\s*(?:dias?|semanas?|meses|horas?|minutos?)|"
     r"\d+\s*(?:dias?|semanas?|meses|horas?|minutos?)\s+(?:de|para|at[eé])|"
     r"dura[cç][aã]o|carga hor[aá]ria|no seu ritmo|ao vivo em)\b"),

    ("7 por que confiar",
     r"(\b(desde \d{4}|h[aá] \d+ anos?|\d+\s*(?:anos?) de|"
     r"\d+\s*(?:alunos?|clientes?|empresas?|profissionais?|pessoas?)|"
     r"depoiment|quem j[aá] (?:fez|usou|passou)|resultado de|caso de|"
     r"formad[oa] (?:em|pel)|engenheir|especialista em)\b)"),

    ("8 e se nao der certo",
     r"\b(garantia|reembolso|dinheiro de volta|devolv|cancelar quando|"
     r"sem compromisso|sem fidelidade|teste (?:gr[aá]tis|por)|"
     r"risco zero|satisfa[cç][aã]o)\b"),

    ("9 qual o proximo passo",
     r"\b(clique|clica|acesse|garanta|inscreva|cadastre|preencha|baixe|"
     r"comece|agende|fale com|quero |entrar na lista|reservar|"
     r"pegar (?:minha|meu)|come[cç]ar agora)\b"),

    ("10 quem esta por tras",
     r"\b(criad[oa] por|desenvolvid[oa] por|meu nome [eé]|"
     r"somos (?:uma|a|um)|nossa (?:empresa|equipe)|CNPJ|fundad[oa]|"
     r"respons[aá]vel t[eé]cnic)\b"),
]
_AS_DEZ_C = [(nome, re.compile(pat, re.I)) for nome, pat in AS_DEZ]

# 🔴 UM NOME PROPRIO SO E' NOME PROPRIO COM A INICIAL MAIUSCULA, e por isso
# esta linha mora FORA do dicionario acima: la tudo compila com `re.I`, e o
# `re.I` apaga exatamente a informacao que distingue "por Maria Silva" de
# "por que sua ideia". Medido: numa pagina real a pergunta 10 foi dada como
# respondida pelo trecho "por que sua" — uma conjuncao lida como assinatura.
_ASSINATURA = re.compile(r"\bpor [A-Z][a-z]+ [A-Z][a-z]+\b")

# 🔴 AFIRMACAO NEGADA NAO E' A AFIRMACAO, e contar como se fosse inverte o
# sentido do achado. Medido na mesma pagina: "por que confiar" foi dada como
# respondida por "Voce nao precisa ser ESPECIALISTA EM..." — que e' a pagina
# dizendo que NAO ha credencial, lida como se houvesse.
_NEGACAO = re.compile(r"\b(n[aã]o|nunca|jamais|sem|nenhum[ao]?|nada de)\s+"
                      r"(?:\S+\s+){0,3}$", re.I)


def _negado(texto, inicio):
    """O que vem logo antes desvira o que foi casado?"""
    return bool(_NEGACAO.search(texto[max(0, inicio - 40):inicio]))

# Marcas de PUBLICO: o que a pagina diz sobre quem e' o leitor. Nao ha lista
# fechada de profissoes, e nem poderia haver — o que se colhe e' o SUJEITO que
# a pagina nomeia logo depois de uma marca de enderecamento.
_MARCA_DE_PUBLICO = re.compile(
    r"\b(?:para|voltado para|feito para|se voc[eê] [eé]|indicado para|"
    r"ideal para|destinado a)\s+(?:o |a |os |as |um |uma )?"
    r"([a-zà-ÿ]{4,}(?:\s+[a-zà-ÿ]{3,})?)", re.I)

_PARADAS = frozenset((
    "voce", "voc", "que", "quem", "todos", "todas", "isso", "isto", "ele",
    "ela", "seu", "sua", "mais", "melhor", "sempre", "nunca", "aqui", "agora",
    "ser", "ter", "fazer", "com", "sem", "por", "uma", "dos", "das", "nos",
    "cada", "esse", "essa", "este", "esta", "onde", "quando", "porque",
))

# 🔴 "PARA VALIDAR" NAO E' PUBLICO, E' FINALIDADE.
# A mesma preposicao serve as duas coisas: "para eletricistas" diz com quem a
# pagina fala, "para validar sua ideia" diz para que ela serve. Sem separar os
# dois, o detector devolveu `desenvolver`, `validar` e `apresentar` como se
# fossem gente — e uma pagina que nao nomeia ninguem sairia com a lista cheia.
_INFINITIVO = re.compile(r"^[a-zà-ÿ]+(ar|er|ir)$", re.I)


def _trechos(caminho):
    if os.path.isdir(caminho):
        return colher_pasta(caminho, limite=400)
    return colher(caminho)


def _normal(s):
    """Sem acento e em minuscula, so para COMPARAR palavra de publico.

    A comparacao precisa disso porque a mesma palavra aparece acentuada numa
    pagina e nao noutra. O texto que sai como evidencia continua o original.
    """
    tabela = str.maketrans("áàâãéêí"
                           "óôõúüç",
                           "aaaaeeiooouuc")
    return s.lower().translate(tabela)


def ler(caminho):
    """({respondidas, de, respostas}, codigo) — as dez perguntas, com fonte."""
    trechos, cod = _trechos(caminho)
    if cod != OK:
        return None, cod
    respostas = []
    for nome, rx in _AS_DEZ_C:
        achou = None
        for t in trechos:
            for m in rx.finditer(t.texto):
                if _negado(t.texto, m.start()):
                    continue
                achou = (m.group(0).strip(), t.onde(), t.texto[:90])
                break
            if achou is None and nome.startswith("10 "):
                m = _ASSINATURA.search(t.texto)
                if m and not _negado(t.texto, m.start()):
                    achou = (m.group(0).strip(), t.onde(), t.texto[:90])
            if achou:
                break
        respostas.append((nome, achou))
    return {"respondidas": sum(1 for _, a in respostas if a),
            "de": len(respostas),
            "respostas": respostas,
            "trechos": len(trechos)}, OK


def publico(caminho):
    """Quem a pagina diz que o leitor e', por ordem de quantas vezes disse.

    🔴 NAO decide se o publico esta certo. Devolve o que a pagina COMUNICA,
    para que isso possa ser comparado com o publico que o produto declara em
    outro lugar. A divergencia entre os dois e' um achado que nenhuma metrica
    de forma alcanca, e e' um achado que o produto produz contra si mesmo —
    o mesmo desenho do detector de tela prescrita e nao entregue.
    """
    trechos, cod = _trechos(caminho)
    if cod != OK:
        return None, cod
    conta, onde = {}, {}
    for t in trechos:
        for m in _MARCA_DE_PUBLICO.finditer(t.texto):
            alvo = m.group(1).strip()
            chave = _normal(alvo)
            if not chave:
                continue
            primeira = chave.split()[0]
            if primeira in _PARADAS or _INFINITIVO.match(primeira):
                continue
            conta[chave] = conta.get(chave, 0) + 1
            onde.setdefault(chave, (alvo, t.onde()))
    ordenado = sorted(conta.items(), key=lambda kv: (-kv[1], kv[0]))
    return {"publicos": [(onde[k][0], n, onde[k][1]) for k, n in ordenado],
            "trechos": len(trechos)}, OK


def divergencia_de_publico(comunicado, declarado):
    """O publico que a pagina COMUNICA bate com o que o produto DECLARA?

    Os dois vem do mesmo produto, medidos em lugares diferentes: um no texto
    que o visitante le, outro onde o produto se descreve. Quando divergem, a
    pagina esta falando com quem ela nao serve — e ninguem dentro do projeto
    percebe, porque cada lado, sozinho, parece certo.
    """
    if not comunicado or not declarado:
        return None
    topo = _normal(comunicado[0][0])
    nomes = [_normal(d) for d in declarado]
    bate = any(topo in d or d in topo for d in nomes)
    return {"comunicado": comunicado[0][0], "declarado": list(declarado),
            "diverge": not bate, "fonte": comunicado[0][2]}


def impressao(r, caminho):
    L = ["LEITOR FRIO — %s" % caminho, "",
         "  Le SO o texto visivel. Nome de arquivo e de componente nao entram.",
         ""]
    for nome, achou in r["respostas"]:
        if achou:
            marca, onde, trecho = achou
            L.append("  RESPONDE     %-22s  \"%s\"" % (nome, marca))
            L.append("               %s  %s"
                     % (onde, trecho.replace("\n", " ")))
        else:
            L.append("  SEM RESPOSTA %-22s  nenhuma evidencia no texto visivel"
                     % nome)
    L.append("")
    L.append("  COMPREENSAO: %d de %d  (sobre %d trecho(s) visiveis)"
             % (r["respondidas"], r["de"], r["trechos"]))
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

    exigir = opcao("--exigir")
    valores = {exigir} if exigir else set()
    livres = [a for a in argv if not a.startswith("--") and a not in valores]
    if not livres:
        print("uso: python -m esteira.leitor <caminho> [--exigir N] [--publico]")
        print("     sem --exigir ele relata; com, ele vira gate e reprova.")
        return NAO_USAR
    caminho = livres[0]

    if "--publico" in argv:
        p, cod = publico(caminho)
        if cod != OK:
            print("nao deu para ler %s (codigo %d)." % (caminho, cod))
            return cod
        print("QUEM A PAGINA DIZ QUE O LEITOR E' — %s" % caminho)
        print()
        if not p["publicos"]:
            print("  nenhum publico nomeado no texto visivel.")
            print("  Uma pagina que nao diz para quem e' deixa o visitante")
            print("  decidir sozinho se ela e' para ele. A maioria decide que nao.")
            return OK
        for nome, n, onde in p["publicos"][:8]:
            print("  %-34s %2dx   %s" % (nome, n, onde))
        return OK

    r, cod = ler(caminho)
    if cod != OK:
        print("nao deu para ler %s (codigo %d)." % (caminho, cod))
        if cod == NAO_MEDIR:
            print("  Gate que nao mede nao aprova — e isto NAO e um verde.")
        return cod
    print(impressao(r, caminho))

    if exigir is None:
        print()
        print("  Sem --exigir, o leitor RELATA e nao reprova.")
        return OK
    try:
        piso = int(exigir)
    except ValueError:
        print("  --exigir quer um numero. NAO DEU PARA USAR (2).")
        return NAO_USAR
    print()
    if r["respondidas"] < piso:
        print("  ACUSOU (1) — %d de %d, abaixo do piso %d."
              % (r["respondidas"], r["de"], piso))
        print("  O piso calibrado nas pecas que converteram e' %d."
              % PISO_CALIBRADO)
        return ACUSOU
    print("  LIMPO (0) — %d de %d, no piso %d ou acima."
          % (r["respondidas"], r["de"], piso))
    return OK


if __name__ == "__main__":
    sys.exit(main())
