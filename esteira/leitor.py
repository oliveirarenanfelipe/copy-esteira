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

🔴 O QUE "FRIO" E "VISIVEL" QUEREM DIZER AQUI, E O QUE NAO QUEREM
-------------------------------------------------------------------
Esta peca dizia "le SO o texto visivel", e a frase era grande demais para o
que ela faz. Ela tira comentario, `<style>`, `<script>` e nome de componente.
Ela NAO calcula visibilidade CSS, e nao tem como: sem renderizar a pagina,
`max-height: 0` e' so mais uma declaracao.

Medido numa pagina de vendas real: uma das respostas contadas vinha de dentro
de um item de FAQ recolhido por padrao. O visitante que nao clica no acordeao
nao le aquele texto, e o placar contou como se lesse. Entao o placar erra para
CIMA, e o limite agora sai impresso junto com ele.

Prometer mais precisao do que se entrega e' o mesmo defeito que este
repositorio persegue nos outros, so que na primeira linha da propria saida.

O leitor le o texto da pagina, pela Camada 0. Nome de arquivo, nome de
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
     # 🔴 `R\$\s*\d` casava UM digito, e a pista impressa saia "R$3" numa
     # pagina de R$37. O que e' DETECTADO nao muda, porque as duas versoes
     # casam nos mesmos textos; o que muda e' o pedaco que aparece na saida.
     # E numero cortado le como fato: "R$3" nao e' um preco aproximado, e'
     # outro preco.
     r"(R\$\s*[\d.,]+|\b(gr[aá]tis|gratuito|sem custo|de gra[cç]a|investimento "
     r"(?:de|[eé])|por apenas|valor (?:de|[eé])|\d+\s*x\s*de|parcelad\w*)\b)"),

    ("6 quanto tempo leva",
     r"\b(em \d+\s*(?:dias?|semanas?|meses|horas?|minutos?)|"
     r"\d+\s*(?:dias?|semanas?|meses|horas?|minutos?)\s+(?:de|para|at[eé])|"
     r"dura[cç][aã]o|carga hor[aá]ria|no seu ritmo|ao vivo em)\b"),

    # 🔴 `depoiment`, `engenheir` e `pel` ESTAVAM MORTOS, e eram os tres
    # termos mais obvios desta pergunta. Ver a nota sobre prefixo truncado
    # logo abaixo da lista.
    ("7 por que confiar",
     # 🔴 AS ESTRELAS MORAM FORA DO GRUPO `\b(...)\b`, E O MOTIVO E' O MESMO
     # DEFEITO, na outra ponta. `\b` e' fronteira entre caractere de palavra e
     # o resto; a estrela nao e' caractere de palavra, entao `\b[★⭐]` nunca
     # casa. Escrita dentro do grupo, a pista nascia morta igual ao
     # `depoiment` — so que pelo `\b` de ABERTURA em vez do de fechamento.
     # Medido: com ela dentro, `<div>★★★★★</div>` dava "sem evidencia".
     r"([★⭐]{3,}|"
     r"\b(desde \d{4}|h[aá] \d+ anos?|\d+\s*(?:anos?) de|"
     # `mil` e `milhao` entram porque "500 mil alunos" nao casava, e e' a
     # forma mais comum de escrever numero grande de gente em copy brasileira.
     # Medido: sem isto, 1 das 10 pecas do corpus ficava sem resposta apesar
     # de dizer o numero de alunos tres vezes.
     r"\d[\d.,]*\s*(?:mil|milh[oõ][ei]?s?(?: de)?)?\s*"
     r"(?:alunos?|clientes?|empresas?|profissionais?|pessoas?)|"
     r"depoiment\w*|quem j[aá] (?:fez|usou|passou)|resultado de|caso de|"
     # 🔴 PROVA SOCIAL QUE NAO DIZ A PALAVRA "DEPOIMENTO", que era o caso que
     # abriu esta pendencia. Uma pagina de vendas real tinha tres depoimentos
     # com nome, cidade e cinco estrelas, e esta pergunta saia "sem evidencia
     # no texto visivel" — o que e' falso, e falso negativo nao aparece como
     # erro: aparece como pagina ruim.
     #
     # As duas pistas abaixo entraram MEDIDAS, pelos tres criterios que o
     # projeto exige de qualquer regua: acham na pagina que tem depoimento,
     # dao 0 de 6 de falso positivo na copy de controle, e nao mexem nas 10
     # pecas que ja estavam certas.
     #
     # ⚠️ Uma TERCEIRA candidata foi DESCARTADA na medicao: `\\w+ que usou`
     # casava "o profissional que usa raramente tem problema", que e'
     # afirmacao generica de beneficio e nao prova de que alguem usou. Cobrir
     # mais nao vale perder a precisao.
     r"o que (?:\w+\s+){0,3}(?:dizem|dizendo|falam|falando|acham|achou)|"
     # 🔴 `engenheir\w*` SOZINHO E' FALSO POSITIVO, e eu o criei consertando o
     # prefixo morto. Medido na copy de controle: casou em "projetos
     # elaborados por engenheiros habilitados", que e' mencao generica no meio
     # de uma explicacao tecnica, e nao credencial de quem vende. A pergunta e'
     # "por que confiar em VOCES", entao o termo so vale com marca de
     # identidade ou de responsabilidade.
     r"formad[oa] (?:em|pel\w*)|"
     r"(?:sou|somos|nossos?|nossas?|equipe de|time de)\s+(?:\w+\s+){0,2}"
     r"engenheir\w*|engenheir\w*\s+(?:respons[aá]ve|s[oó]ci|fundador|"
     r"chef)\w*|"
     r"especialista em)\b)"),

    ("8 e se nao der certo",
     r"\b(garantia|reembolso|dinheiro de volta|devolv\w*|cancelar quando|"
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

# 🔴 PREFIXO TRUNCADO DENTRO DE GRUPO FECHADO POR `\b` NAO CASA NADA.
# ---------------------------------------------------------------------------
# Os padroes acima terminam em `)\b`. Quem escreve `depoiment` esta pedindo a
# familia da palavra — depoimento, depoimentos —, mas o `\b` exige fronteira
# logo depois de `depoiment`, e em "depoimento" vem um `o`, que e' caractere de
# palavra. Resultado: o termo so casaria a string `depoiment`, que nao existe
# em portugues. A pista ficou morta desde o dia em que foi escrita.
#
# Medido em num caso medido, e nao era teorico:
#
#     `depoiment`  morto, e a palavra aparece em 4 das 10 pecas do corpus
#     `devolv`     morto, e aparece em 3 das 10
#     `parcelad`   morto, e aparece em 1 das 10
#     `engenheir`  morto ("engenheiro", "engenheira")
#     `pel`        morto, dentro de `formad[oa] (?:em|pel)` ("formado pela")
#
# Efeito: pagina COM politica de devolucao era marcada como "e se nao der
# certo: sem resposta". O gate acusava a pagina por uma falta que era do
# medidor. Falso negativo nao aparece como erro: aparece como pagina ruim.
#
# O conserto e' o `\w*` colado no prefixo. A GUARDA nao e' este comentario:
# e' `test_as_dez_perguntas_reconhecem_a_familia_das_palavras`, que exercita
# uma frase de controle por termo e quebra se alguem escrever prefixo morto
# de novo.
_AS_DEZ_C = list(_AS_DEZ_C)

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


def pista_inteira(texto, inicio, casado):
    """A pista, estendida para tras enquanto o caractere anterior for numero.

    🔴 CONSERTO DE CLASSE, E NAO DO CASO. Os padroes daqui escrevem `\\d+`, que
    nao inclui o ponto do milhar. Entao o casamento comeca no MEIO do numero, e
    a pista impressa fica:

        "90.000 alunos"   virava   "000 alunos"
        "1.023 alunos"    virava   "023 alunos"
        "R$37"            virava   "R$3"

    Tres padroes diferentes, o mesmo defeito. O primeiro que eu achei foi o do
    preco, e eu consertei SO ele, alargando aquele `\\d` para `[\\d.,]+`. Os
    outros dois continuaram errados porque ninguem olhou. Catalogar defeito
    para cacar um a um e' o habito errado: a estrutura tem de garantir a
    propriedade.

    Aqui a propriedade e uma so, e vale para qualquer padrao novo que alguem
    escreva depois: **pista nao comeca no meio de um numero**. Numero cortado
    le como fato, e "000 alunos" nao e um numero aproximado, e' outro numero.
    """
    i = inicio
    while i > 0 and (texto[i - 1].isdigit() or
                     (texto[i - 1] in ".," and i > 1 and texto[i - 2].isdigit())):
        i -= 1
    return (texto[i:inicio] + casado) if i < inicio else casado


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
                achou = (pista_inteira(t.texto, m.start(),
                                       m.group(0)).strip(),
                         t.onde(), t.texto[:90])
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
         "  Le o texto da PAGINA. Nome de arquivo e de componente nao entram,"
         " nem comentario,",
         "  nem o que esta dentro de <style> ou <script>.",
         "  LIMITE: nao calcula visibilidade CSS. Resposta de FAQ recolhida"
         " (`max-height: 0`)",
         "  conta como texto, e o visitante que nao clica nao a ve. O placar"
         " pode estar ALTO.",
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

        # 🔴 `--declarado` LIGA a comparacao que da sentido a esta saida.
        # `divergencia_de_publico` existia e nenhum `main()` chegava nela,
        # achado por varredura de alcancabilidade. Sozinha, a lista acima diz
        # com quem a pagina FALA; o achado nasce quando ela e' confrontada com
        # quem o produto DIZ atender. Cada lado, sozinho, parece certo.
        if "--declarado" in argv:
            i = argv.index("--declarado")
            declarado = [x.strip() for x in argv[i + 1].split(",")] \
                if i + 1 < len(argv) else []
            d = divergencia_de_publico(p["publicos"], declarado)
            print()
            if d is None:
                print("  sem publico declarado para comparar.")
                return OK
            print("  PUBLICO DECLARADO PELO PRODUTO: %s"
                  % ", ".join(d["declarado"]))
            print("  PUBLICO QUE A PAGINA MAIS COMUNICA: %s   [%s]"
                  % (d["comunicado"], d["fonte"]))
            if d["diverge"]:
                print()
                print("  ACUSOU (1) — os dois NAO batem. A pagina esta falando")
                print("  com quem o produto nao diz atender, e ninguem dentro")
                print("  do projeto percebe, porque cada lado parece certo.")
                return ACUSOU
            print("  batem.")
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
