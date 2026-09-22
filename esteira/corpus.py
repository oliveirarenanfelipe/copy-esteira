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
    """Colhe de .tsx/.jsx/.ts/.js/.html — o que aparece na tela."""
    limpo = _tira_blocos_sem_copy(_sem_comentarios(fonte))
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


LEITORES = {
    ".tsx": colher_marcado, ".jsx": colher_marcado, ".ts": colher_marcado,
    ".js": colher_marcado, ".html": colher_marcado, ".htm": colher_marcado,
    ".md": colher_texto, ".txt": colher_texto,
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


def colher_pasta(raiz, limite=400):
    """Colhe a pasta inteira. Devolve (trechos, codigo)."""
    if not os.path.isdir(raiz):
        return [], 2
    todos = []
    for base, dirs, arquivos in os.walk(raiz):
        dirs[:] = [d for d in dirs
                   if d not in ("node_modules", ".git", "dist", "build", ".next")]
        for a in sorted(arquivos):
            if os.path.splitext(a)[1].lower() in LEITORES:
                trechos, _ = colher(os.path.join(base, a))
                todos.extend(trechos)
                if len(todos) >= limite:
                    return todos[:limite], 0
    return (todos, 0) if todos else ([], 3)
