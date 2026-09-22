# -*- coding: utf-8 -*-
"""CAMADA 1, varredura de PROJETO — o que um arquivo sozinho nao mostra.

CHAMADOR: `esteira/gabarito.py` (o reencontro da F3) e `testar_varredura.py`.

Os gates de `gate.py` olham UM arquivo. Tres achados do gabarito de num caso medido so
existem quando se olha o projeto inteiro:

  · "4 links da home exigem login"   -> precisa saber quais rotas sao privadas
  · "zero link quebrado em 93 rotas" -> precisa do mapa de rotas
  · "FAQ ausente, e o produto prescreve" -> precisa comparar o que o proprio
    produto declara com o que ele entrega

JA EXISTIA? `gate.py:167` tem `gate_caminhos`, mas ele le UM arquivo e procura
a rota varrendo nomes de pasta. Nao monta mapa de rotas, nao sabe o que e'
rota dinamica e nao sabe o que exige sessao.

FERRAMENTA APROVADA? O `lychee` foi adotado na F0 para link quebrado, mas ele
checa URL VIVA por HTTP. Aqui se le codigo em disco, offline, de projeto de
terceiro que nao esta no ar para nos.

🔴 O detector mais interessante e' o `prescrito_e_ausente`: ele nao compara a
pagina com regra externa nenhuma. Compara o produto com o que o PROPRIO
produto declara que deveria existir. Isso e' regua que nao precisa do corpus
de ninguem, e por isso e' universal (D-03).
"""
import os
import re

IGNORA = {"node_modules", ".git", "dist", "build", ".next", ".turbo", "out"}

# Next.js App Router: `app/<rota>/page.tsx`. Pages Router: `pages/<rota>.tsx`.
_PAGE = re.compile(r"[\\/](?:app|pages)[\\/](.+?)[\\/]?page\.(?:tsx|jsx|js|ts)$")
_GRUPO = re.compile(r"\((?:[^)]*)\)")          # `(public)` nao entra na URL
_HREF = re.compile(r"""href\s*=\s*["']([^"']+)["']""")
_HREF_OBJ = re.compile(r"""href\s*:\s*["']([^"']+)["']""")

# marcas de que a rota exige sessao
MARCAS_DE_SESSAO = (
    "getServerSession", "requireAuth", "redirect('/login",
    'redirect("/login', "useSession", "withAuth", "currentUser",
    "unauthorized", "signIn(", "isAuthenticated",
)


def _e_teste(nome, base):
    """Arquivo de teste ou fixture nao descreve a navegacao da pagina.

    🔴 Medido em num caso medido: um `href="/detalle-innovador/?empresa=203"` dentro de
    um teste de scraping de site DE TERCEIRO foi contado como link interno e
    reportado como rota quebrada. O site nao tem esse defeito — o medidor
    e' que estava lendo ficcao de teste como se fosse pagina.
    """
    n = nome.lower()
    return (".test." in n or ".spec." in n or n.endswith(".d.ts")
            or "__tests__" in base.replace("\\", "/").lower()
            or "__mocks__" in base.replace("\\", "/").lower())


def _arquivos(raiz, exts=(".tsx", ".jsx", ".ts", ".js"), com_teste=False):
    for base, dirs, arqs in os.walk(raiz):
        dirs[:] = [d for d in dirs if d not in IGNORA]
        for a in arqs:
            if a.endswith(exts) and (com_teste or not _e_teste(a, base)):
                yield os.path.join(base, a)


def _ler(caminho):
    try:
        return open(caminho, encoding="utf-8").read()
    except (OSError, UnicodeDecodeError):
        return ""


def _texto_de(caminho_ou_texto):
    """Le o arquivo se for caminho; senao devolve o proprio texto.

    🔴 A versao anterior perguntava `os.path.sep in caminho`. No Windows o
    separador e' a barra invertida, entao caminho escrito com barra normal
    caia no `else` e o medidor MEDIA O NOME DO ARQUIVO como se fosse a
    pagina. Efeito: zero achado, em silencio — o pior tipo, porque le como
    "a pagina esta limpa". Medido em num caso medido contra o alvo do gabarito, que
    voltou vazio quando deveria ter 1 achado.
    """
    try:
        if os.path.isfile(caminho_ou_texto):
            return _ler(caminho_ou_texto)
    except (OSError, ValueError):
        pass
    return caminho_ou_texto


def rotas(raiz):
    """{rota_url: caminho_do_arquivo}. Le a arvore, nao o roteador.

    🔴 Ancora no ULTIMO `app/` ou `pages/` do caminho, nunca no primeiro.
    Medido em num caso medido sobre um projeto real: a raiz passada era `artifacts/app`,
    o regex casou com AQUELE `app`, e as 95 rotas sairam como `/src/app/...`.
    Efeito: 65 links apareceram como quebrados, e nenhum estava. Um detector
    de link quebrado que erra o prefixo acusa o site inteiro — que e' o
    alarme falso que ensina a ignorar a linha.
    """
    achadas = {}
    for caminho in _arquivos(raiz):
        nome = os.path.basename(caminho)
        if not nome.startswith("page."):
            continue
        p = os.path.dirname(caminho).replace("\\", "/")
        # a ancora mais INTERNA, nunca a primeira que aparecer no caminho
        corte = max(p.rfind("/app/"), p.rfind("/pages/"),
                    len(p) - 4 if p.endswith("/app") else -1,
                    len(p) - 6 if p.endswith("/pages") else -1)
        if corte < 0:
            continue
        resto = p[corte:].split("/", 2)
        cru = resto[2] if len(resto) > 2 else ""
        partes = [x for x in cru.split("/") if x and not _GRUPO.fullmatch(x)]
        achadas["/" + "/".join(partes)] = caminho
    return achadas


def links_internos(caminho_ou_texto):
    """Links que apontam para dentro do proprio site."""
    txt = _texto_de(caminho_ou_texto)
    brutos = set(_HREF.findall(txt)) | set(_HREF_OBJ.findall(txt))
    saida = set()
    for h in brutos:
        if h.startswith("/") and not h.startswith("//"):
            saida.add(h.split("?")[0].split("#")[0].rstrip("/") or "/")
    return sorted(saida)


def _casa_dinamica(link, rota):
    a, b = link.strip("/").split("/"), rota.strip("/").split("/")
    if len(a) != len(b):
        return False
    return all(y.startswith("[") or x == y for x, y in zip(a, b))


def quebrados(links, mapa_de_rotas):
    """Link que nao tem rota. Dinamico (`[id]`) nao conta como quebrado."""
    dinamicas = [r for r in mapa_de_rotas if "[" in r]
    faltando = []
    for l in links:
        if l in mapa_de_rotas or l == "/":
            continue
        if any(_casa_dinamica(l, r) for r in dinamicas):
            continue
        faltando.append(l)
    return faltando


def exigem_sessao(links, mapa_de_rotas):
    """Dos links dados, quais caem em rota que pede login.

    Olha o arquivo da rota E as pastas acima, porque em Next o layout protege
    a subarvore inteira — e e' assim que a protecao costuma ser feita.
    """
    privados = []
    for l in links:
        arquivo = mapa_de_rotas.get(l)
        if not arquivo:
            continue
        alvos = [arquivo]
        pasta = os.path.dirname(arquivo)
        for _ in range(4):
            for viz in ("layout.tsx", "layout.jsx", "middleware.ts"):
                p = os.path.join(pasta, viz)
                if os.path.isfile(p):
                    alvos.append(p)
            pai = os.path.dirname(pasta)
            if pai == pasta:
                break
            pasta = pai
        for alvo in alvos:
            txt = _ler(alvo)
            if any(marca in txt for marca in MARCAS_DE_SESSAO):
                privados.append((l, os.path.basename(alvo)))
                break
    return privados


def prescrito_e_ausente(raiz, mapa_de_rotas):
    """O que o PROPRIO produto declara que deve existir, e nao existe."""
    faltando = []
    for caminho in _arquivos(raiz, (".ts", ".tsx", ".js", ".json")):
        txt = _ler(caminho)
        if not txt:
            continue
        for m in re.finditer(
                r'(?:rota|route|path)\s*:\s*["\'](/[a-z0-9\-/]*)["\']', txt):
            rota = m.group(1).rstrip("/") or "/"
            if rota in mapa_de_rotas or rota == "/":
                continue
            if any(_casa_dinamica(rota, r) for r in mapa_de_rotas if "[" in r):
                continue
            linha = txt.count("\n", 0, m.start()) + 1
            faltando.append((rota, "%s:%d" % (os.path.basename(caminho), linha)))
    vistos = {}
    for rota, onde in faltando:
        vistos.setdefault(rota, onde)
    return sorted(vistos.items())


# ── contraste declarado no estilo ───────────────────────────────────────────
# Tailwind escreve a opacidade na propria classe: `text-white/50`.
_COR_COM_ALPHA = re.compile(r"\btext-(white|black)/(\d{1,3})\b")


def texto_sobre_fundo(caminho_ou_texto):
    """Acha texto com opacidade declarada, que e' o caso do gabarito.

    Devolve [(cor_base, alpha, linha, trecho)]. Nao decide nada: quem decide
    e' o gate, que precisa dos fundos reais para compor a cor.
    """
    txt = _texto_de(caminho_ou_texto)
    saida = []
    for m in _COR_COM_ALPHA.finditer(txt):
        base = (255, 255, 255) if m.group(1) == "white" else (0, 0, 0)
        alpha = int(m.group(2)) / 100.0
        linha = txt.count("\n", 0, m.start()) + 1
        saida.append((base, alpha, linha, m.group(0)))
    return saida


def fundo_externo(raiz):
    """URL absoluta servindo midia. O achado do CDN de terceiro."""
    achados = []
    for caminho in _arquivos(raiz):
        txt = _ler(caminho)
        for m in re.finditer(r'["\'](https?://[^"\'\s]+)["\']', txt):
            u = m.group(1)
            if u.startswith(("https://fonts.g", "http://www.w3.org",
                             "https://www.w3.org")):
                continue
            linha = txt.count("\n", 0, m.start()) + 1
            achados.append((u, "%s:%d" % (os.path.basename(caminho), linha)))
    return achados
