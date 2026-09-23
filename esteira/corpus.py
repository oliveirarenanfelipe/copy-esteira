# -*- coding: utf-8 -*-
"""CAMADA 0 — a entrada vira corpus, e nada mais.

    from esteira.corpus import colher

Ela nao interpreta, nao julga e nao mede. So transforma um caminho em trechos
de texto que alguem VERIA, cada um sabendo de onde veio.

🔴 A TRAVA DESTA CAMADA (F1, e ela e' o motivo da peca existir separada)
------------------------------------------------------------------------
E' proibido usar nome de componente, nome de arquivo ou comentario de codigo
como fonte de compreensao.

O que a pagina comunica e' o que ela MOSTRA, nao como o programador batizou as
coisas. Um arquivo `pricing-table.tsx` nao prova que a pagina comunica preco;
um componente `TrustBadges` nao prova que alguem confia. Aceitar esses nomes
faz a esteira entender a pagina pelo vocabulario de quem a construiu — que e'
exatamente o contexto que o visitante NAO tem.

Vale com mais forca para a Camada 2: leitor frio que leu o nome do arquivo
deixou de ser frio.

CODIGOS DE SAIDA (a taxonomia da maquina, igual em toda peca daqui)
    0  colheu
    2  nao deu para USAR — caminho que nao existe, extensao sem leitor
    3  nao deu para MEDIR — arquivo ilegivel, corpus vazio. NAO e' um verde.
"""
import json
import os
import re

# as propriedades que carregam classe, rota e configuracao — nunca copy
PROPS_NAO_COPY = {
    "className", "class", "href", "src", "key", "id", "type", "rel", "target",
    "path", "count", "index", "name", "value", "width", "height", "style",
    "viewBox", "d", "fill", "stroke", "xmlns", "alt", "role", "as", "variant",
}

# o que nunca e' copy, mesmo aparecendo entre tags
TAGS_SEM_COPY = ("script", "style", "svg", "noscript", "head", "template")

_COMENT_BLOCO = re.compile(r"/\*.*?\*/", re.S)
_COMENT_LINHA = re.compile(r"^\s*//.*$", re.M)
_COMENT_HTML = re.compile(r"<!--.*?-->", re.S)
_TAG = re.compile(r"<[^>]+>")

# 🔴 TIRAR A TAG NAO BASTA: A ENTIDADE CONTINUA LA, E ELA CONTA COMO PALAVRA.
# Achado ao rodar a Camada 0 sobre paginas reais da web, e nao sobre arquivo de
# teste: o texto saia com `&quot;`, `&#x27;` e `&nbsp;` no meio das frases.
# Cada um vira "palavra" na contagem, infla palavras-por-frase e move o indice
# de legibilidade — um erro que so aparece em material de fora, porque o codigo
# que nos escrevemos usa aspas de verdade.
_ENTIDADE_NUM = re.compile(r"&#(\d+);|&#x([0-9a-fA-F]+);")
_ENTIDADES = (
    ("&quot;", '"'), ("&apos;", "'"), ("&nbsp;", " "), ("&ndash;", "–"),
    ("&mdash;", "—"), ("&hellip;", "…"), ("&lsquo;", "‘"),
    ("&rsquo;", "’"), ("&ldquo;", "“"), ("&rdquo;", "”"),
    ("&lt;", "<"), ("&gt;", ">"), ("&amp;", "&"),
)


def _sem_entidade(s):
    """Devolve a letra que a entidade representa. `&amp;` fica por ultimo, de
    proposito: trocar antes transformaria `&amp;quot;` em aspas."""
    def _num(m):
        codigo = int(m.group(1)) if m.group(1) else int(m.group(2), 16)
        try:
            return chr(codigo)
        except (ValueError, OverflowError):
            return " "
    s = _ENTIDADE_NUM.sub(_num, s)
    for entidade, letra in _ENTIDADES:
        s = s.replace(entidade, letra)
    return s


class Trecho:
    """Um pedaco de texto visivel, e a linha de onde ele saiu."""

    __slots__ = ("texto", "fonte", "linha")

    def __init__(self, texto, fonte, linha):
        self.texto = texto
        self.fonte = fonte
        self.linha = linha

    def onde(self):
        return "%s:%d" % (self.fonte, self.linha)

    def __repr__(self):
        return "Trecho(%r, %s)" % (self.texto[:40], self.onde())


def _sem_comentarios(fonte):
    """Tira comentario de bloco, de linha e de HTML.

    Faz parte da trava: comentario e' conversa do programador com ele mesmo.
    """
    s = _COMENT_BLOCO.sub(" ", fonte)
    s = _COMENT_LINHA.sub(" ", s)
    s = _COMENT_HTML.sub(" ", s)
    return s


def _tira_blocos_sem_copy(s):
    for tag in TAGS_SEM_COPY:
        s = re.sub(r"<%s\b.*?</%s>" % (tag, tag), " ", s, flags=re.S | re.I)
    return s


def _e_frase(t):
    """Texto que um humano leria, e nao um identificador solto.

    Exige espaco ou pontuacao final. `TrustBadges` e `px-4` morrem aqui, e
    morrer aqui e' a trava funcionando.
    """
    t = t.strip()
    if len(t) < 3:
        return False
    if "{" in t or "}" in t or "=>" in t:
        return False
    return (" " in t) or t.endswith((".", "!", "?", ":"))


def _linha_de(fonte, pos):
    return fonte.count("\n", 0, pos) + 1


def colher_marcado(fonte, nome):
    """Colhe de .tsx/.jsx/.ts/.js/.html — o que aparece na tela.

    A entidade e' desfeita ANTES do casamento, e nao depois: `&quot;` vira
    aspa, e aspa e' o caractere que o padrao de propriedade usa para delimitar
    o valor. Desfazer depois deixaria o padrao lendo um texto e a medicao
    contando outro.
    """
    limpo = _sem_entidade(_tira_blocos_sem_copy(_sem_comentarios(fonte)))
    achados = []

    # 1. valor de propriedade de objeto:  titulo: "...", body: '...'
    for m in re.finditer(r'(\w+)\s*:\s*["\']([^"\']{3,})["\']', limpo):
        if m.group(1) not in PROPS_NAO_COPY and _e_frase(m.group(2)):
            achados.append((m.group(2), _linha_de(limpo, m.start())))

    # 2. texto solto entre tags:  >Texto aqui<
    for m in re.finditer(r">([^<>{}\n]{3,})<", limpo):
        if _e_frase(m.group(1)):
            achados.append((m.group(1).strip(), _linha_de(limpo, m.start())))

    vistos = set()
    saida = []
    for texto, linha in achados:
        t = re.sub(r"\s+", " ", texto).strip()
        if t.lower() in vistos:
            continue
        vistos.add(t.lower())
        saida.append(Trecho(t, nome, linha))
    return saida


def colher_texto(fonte, nome):
    """Colhe de .md/.txt — cada paragrafo e' um trecho."""
    limpo = _COMENT_HTML.sub(" ", fonte)
    saida = []
    linha = 1
    for bloco in limpo.split("\n\n"):
        cru = bloco.strip()
        if cru and not cru.startswith(("```", "|", "---")):
            t = re.sub(r"\s+", " ", _TAG.sub(" ", cru)).strip()
            t = re.sub(r"^#+\s*", "", t)
            if _e_frase(t):
                saida.append(Trecho(t, nome, linha))
        linha += bloco.count("\n") + 2
    return saida


# ── copy que mora em DADOS, e nao no componente ─────────────────────────────
# 🔴 SITE MODERNO NAO GUARDA A COPY NO COMPONENTE, E A CAMADA 0 NAO LIA ISSO.
# Medido num site real em producao: a pagina "sobre" tem 20 KB de arquivo e a
# Camada 0 extraia 150 caracteres dela; a home extraia ZERO. O texto inteiro,
# 240 KB, morava em `data/*.json`, e o componente so o renderizava.
#
# Uma esteira de copy que nao le a copy devolve "nao deu para medir" sobre um
# site inteiro, e quem clonou conclui que a ferramenta nao serve — quando o
# que faltava era um leitor.
#
# 🔴 A TRAVA VALE COM MAIS FORCA AQUI: so o VALOR entra, nunca a CHAVE.
# `"titulo"`, `"cta_primario"`, `"hero_subtitle"` sao vocabulario de quem
# construiu o arquivo, igual a nome de componente. O visitante le o valor.
_SLUG = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")
_COR = re.compile(r"^#[0-9a-fA-F]{3,8}$")
_CAMINHO_OU_URL = re.compile(r"^(?:https?:)?//|^/|^\.{1,2}/|\.(?:png|jpe?g|svg"
                             r"|webp|gif|mp4|pdf|ico|css|js)$", re.I)
_SO_NUMERO_OU_DATA = re.compile(r"^[\d\s.,:/+-]+$")


def _valor_e_copy(s):
    """O texto que alguem LE, separado do que so configura a pagina.

    Sem este corte, o corpus fica cheio de `primary`, `num caso medido`, `pt-BR` e
    `/imagens/telhado.png` — e a regua sai medindo o arquivo de configuracao.
    """
    t = s.strip()
    if not _e_frase(t):
        return False
    if _COR.match(t) or _CAMINHO_OU_URL.search(t) or _SO_NUMERO_OU_DATA.match(t):
        return False
    if _SLUG.match(t):
        return False
    return True


def _andar(no, saida):
    """Desce pela estrutura recolhendo so os valores de texto."""
    if isinstance(no, str):
        if _valor_e_copy(no):
            saida.append(no.strip())
    elif isinstance(no, list):
        for item in no:
            _andar(item, saida)
    elif isinstance(no, dict):
        for chave, item in no.items():
            # a CHAVE nunca entra: e' o vocabulario de quem montou o arquivo
            if chave in PROPS_NAO_COPY:
                continue
            _andar(item, saida)


def colher_json(fonte, nome):
    """Colhe de .json — a copy que mora em dados, com a linha de onde saiu.

    A linha vem de procurar o texto no arquivo bruto. O parser perde a
    posicao, e `arquivo:linha` e' o que torna o achado conferivel: achado sem
    fonte nao existe.
    """
    try:
        dados = json.loads(fonte)
    except ValueError:
        return []
    cruas = []
    _andar(dados, cruas)
    achados = []
    procurado_de = 0
    for texto in cruas:
        pedaco = texto[:40].replace("\\", "\\\\").replace('"', '\\"')
        pos = fonte.find(pedaco, procurado_de)
        if pos < 0:
            pos = fonte.find(pedaco)
        if pos >= 0:
            procurado_de = pos + 1
        achados.append(Trecho(texto, nome, _linha_de(fonte, max(pos, 0))))
    return achados


LEITORES = {
    ".tsx": colher_marcado, ".jsx": colher_marcado, ".ts": colher_marcado,
    ".js": colher_marcado, ".html": colher_marcado, ".htm": colher_marcado,
    ".md": colher_texto, ".txt": colher_texto,
    ".json": colher_json,
}


def colher(caminho):
    """(trechos, codigo). `codigo` 0 colheu, 2 nao da para usar, 3 nao mediu."""
    if not os.path.exists(caminho):
        return [], 2
    ext = os.path.splitext(caminho)[1].lower()
    leitor = LEITORES.get(ext)
    if leitor is None:
        return [], 2
    try:
        fonte = open(caminho, encoding="utf-8").read()
    except (OSError, UnicodeDecodeError):
        return [], 3
    if fonte.count("�"):
        # texto ja chegou corrompido: medir isso produziria numero errado
        return [], 3
    trechos = leitor(fonte, os.path.basename(caminho))
    return (trechos, 0) if trechos else ([], 3)


# 🔴 O QUE RENDERIZA UMA PAGINA, E O QUE E' CONVERSA INTERNA DO PROJETO
# ----------------------------------------------------------------------
# `.md` e `.txt` sao copy quando alguem aponta o caminho PARA ELES: o rascunho
# de um e-mail, o roteiro de um anuncio. Dentro de uma PASTA de projeto eles
# sao outra coisa — README, auditoria, lista de pendencias, nota de decisao.
#
# Medido: a Camada 2 apontada para a pasta de um projeto respondeu NOVE das
# dez perguntas do visitante, e sete delas vieram de arquivo de documentacao
# interna. "Por que confiar" foi respondida por uma linha de pendencia sobre
# migracao de banco. O placar ficou alto e a pagina continuava sem dizer o que
# a empresa faz.
#
# E' a mesma trava do topo deste arquivo, um nivel acima: nao basta ignorar o
# NOME do arquivo se o CONTEUDO lido e' a conversa do time com ele mesmo.
EXT_DE_PAGINA = frozenset((".tsx", ".jsx", ".ts", ".js", ".html", ".htm"))


def colher_pasta(raiz, limite=400, so_pagina=True):
    """Colhe a pasta inteira. Devolve (trechos, codigo).

    `so_pagina` deixa de fora `.md` e `.txt`, que dentro de um projeto sao
    documentacao e nao copy. Quem quiser medir a pasta inteira, inclusive a
    documentacao, passa False — e sabe o que esta contando.
    """
    if not os.path.isdir(raiz):
        return [], 2
    aceitos = EXT_DE_PAGINA if so_pagina else set(LEITORES)
    todos = []
    for base, dirs, arquivos in os.walk(raiz):
        dirs[:] = [d for d in dirs
                   if d not in ("node_modules", ".git", "dist", "build", ".next")]
        for a in sorted(arquivos):
            if os.path.splitext(a)[1].lower() in aceitos:
                trechos, _ = colher(os.path.join(base, a))
                todos.extend(trechos)
                if len(todos) >= limite:
                    return todos[:limite], 0
    return (todos, 0) if todos else ([], 3)
