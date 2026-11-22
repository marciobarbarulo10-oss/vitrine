#!/usr/bin/env python3
"""Motor de nota da skill vitrine.

Faz a parte determinística do ciclo: lê o GitHub público, compara o perfil
com os termos das vagas-alvo, roda as checagens e grava a nota. Quem lê o
LinkedIn, extrai termos das vagas e escreve os textos é o Claude; aqui só
entra o que precisa dar o mesmo resultado todo dia para a nota ser comparável.

Só biblioteca padrão. Estado em ~/.claude/vitrine (ou VITRINE_HOME).
"""
import argparse
import base64
import datetime as dt
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(os.environ.get("VITRINE_HOME") or Path.home() / ".claude" / "vitrine")

ROTINAS = {
    0: ("medir", None, "Segunda: medir de novo e montar o plano da semana"),
    1: ("perfil", "perfil", "Terça: corrigir um trecho do perfil"),
    2: ("vitrine", "vitrine", "Quarta: arrumar um projeto no GitHub e no LinkedIn"),
    3: ("topico", "atividade", "Quinta: compartilhar um tópico da sua área"),
    4: ("conexoes", "atividade", "Sexta: conexões e comentários"),
    5: ("bastidor", "atividade", "Sábado: contar o que você construiu na semana"),
    6: ("fechamento", None, "Domingo: fechamento da semana"),
}

CATEGORIAS = [
    ("aderencia", "Aderência às vagas", 30),
    ("perfil", "Perfil", 25),
    ("vitrine", "Vitrine de projetos", 25),
    ("atividade", "Atividade e rede", 20),
]

VERBOS = (
    "desenvolv", "implement", "automatiz", "reduz", "aument", "lider", "gerenci",
    "coorden", "negoci", "estrutur", "integr", "constru", "otimiz", "entreg",
    "migr", "analis", "mape", "conduz", "condu", "trein", "implant", "projet",
    "model", "public", "control", "elabor", "garant", "criei", "criou", "criar",
    "criacao", "criando", "acompanh", "monitor", "padroniz", "organiz", "planej",
    "execut", "atend", "resolv", "corrig", "econom", "eliminei", "eliminou",
    "built", "created", "led", "reduced", "increased", "automated", "designed",
    "shipped", "managed", "launched",
)

CLICHES = (
    "proativo", "proativa", "dinamico", "dinamica", "apaixonado", "apaixonada",
    "focado em resultados", "focada em resultados", "fora da caixa", "sinergia",
    "mindset", "hands on", "hands-on", "resiliente", "comprometido com resultados",
    "em busca de novos desafios", "em busca de novas oportunidades",
    "facilidade de aprendizado", "perfil multidisciplinar",
)

CHAMADAS = ("github.com", "http", "@", "me chame", "me chama", "fale comigo",
            "entre em contato", "vamos conversar", "manda mensagem", "mande mensagem")


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return s.lower()


def contem(texto_norm, termo):
    t = norm(termo).strip()
    if not t:
        return False
    return re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", texto_norm) is not None


def carregar(nome, padrao=None):
    p = BASE / nome
    if not p.exists():
        return padrao
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        print(f"AVISO: não consegui ler {p}: {e}", file=sys.stderr)
        return padrao


def salvar(nome, dado):
    BASE.mkdir(parents=True, exist_ok=True)
    (BASE / nome).write_text(json.dumps(dado, ensure_ascii=False, indent=2), encoding="utf-8")


def linhas_jsonl(nome):
    p = BASE / nome
    if not p.exists():
        return []
    saida = []
    for linha in p.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha:
            try:
                saida.append(json.loads(linha))
            except ValueError:
                pass
    return saida


def hoje():
    forcada = os.environ.get("VITRINE_HOJE")
    return dt.date.fromisoformat(forcada) if forcada else dt.date.today()


def dias_desde(iso):
    try:
        return (hoje() - dt.date.fromisoformat(str(iso)[:10])).days
    except (ValueError, TypeError):
        return None


def dentro_de(iso, dias):
    """Data nos últimos `dias` dias, contando hoje (dias_desde == 0)."""
    d = dias_desde(iso)
    return d is not None and d <= dias


# ---------------------------------------------------------------- GitHub

def api(url):
    cab = {"User-Agent": "vitrine-skill", "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        cab["Authorization"] = "Bearer " + token
    with urllib.request.urlopen(urllib.request.Request(url, headers=cab), timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))


def ler_readme(dono, repo):
    try:
        d = api(f"https://api.github.com/repos/{dono}/{repo}/readme")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    try:
        return base64.b64decode(d.get("content") or "").decode("utf-8", "replace")
    except ValueError:
        return ""


def cmd_github(_):
    alvo = carregar("alvo.json", {})
    usuario = alvo.get("github_user")
    if not usuario:
        print("ERRO: falta github_user em alvo.json")
        return 1
    try:
        u = api(f"https://api.github.com/users/{usuario}")
        repos = api(f"https://api.github.com/users/{usuario}/repos?per_page=100&sort=pushed")
        saida = {
            "lido_em": hoje().isoformat(),
            "usuario": usuario,
            "nome": u.get("name"),
            "bio": u.get("bio"),
            "blog": u.get("blog"),
            "seguidores": u.get("followers"),
            "readme_perfil_chars": 0,
            "repos": [],
        }
        for r in repos:
            if r.get("fork"):
                continue
            readme = ler_readme(usuario, r["name"])
            item = {
                "nome": r["name"],
                "url": r.get("html_url"),
                "descricao": r.get("description"),
                "homepage": r.get("homepage") or None,
                "topicos": r.get("topics") or [],
                "licenca": (r.get("license") or {}).get("spdx_id"),
                "linguagem": r.get("language"),
                "estrelas": r.get("stargazers_count", 0),
                "ultimo_push": (r.get("pushed_at") or "")[:10],
                "readme_chars": len(readme or ""),
                "readme_imagem": bool(readme and re.search(r"!\[[^\]]*\]\(|<img\s", readme)),
            }
            if r["name"].lower() == usuario.lower():
                saida["readme_perfil_chars"] = item["readme_chars"]
            saida["repos"].append(item)
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        print(f"AVISO: GitHub não respondeu ({e}). Mantive o github.json anterior.")
        return 0
    salvar("github.json", saida)
    print(f"GitHub lido: {len(saida['repos'])} repositórios próprios de {usuario}.")
    return 0


# ---------------------------------------------------------------- Checagens

def chk(cid, cat, titulo, maximo, fracao, detalhe, como):
    fracao = max(0.0, min(1.0, float(fracao)))
    return {
        "id": cid, "categoria": cat, "titulo": titulo, "max": maximo,
        "pontos": round(maximo * fracao, 1), "detalhe": detalhe, "como_subir": como,
    }


def texto_perfil(p):
    topo = " \n ".join([p.get("headline") or "", p.get("sobre") or "",
                        " ; ".join(p.get("competencias") or [])])
    resto = []
    for e in p.get("experiencias") or []:
        resto += [e.get("cargo") or "", e.get("descricao") or ""]
    for pr in p.get("projetos") or []:
        resto += [pr.get("nome") or "", pr.get("descricao") or ""]
    for c in p.get("certificados") or []:
        resto.append(c.get("nome") or "")
    for f in p.get("formacao") or []:
        resto.append(f.get("curso") or "")
    return norm(topo), norm(topo + " \n " + " \n ".join(resto))


def peso_termo(t):
    obrig = set(t.get("obrigatorio_em") or [])
    p = sum(2 if v in obrig else 1 for v in (t.get("vagas") or [])) or 1
    return p * (0.5 if t.get("tipo") == "soft" else 1.0)


def achou(texto, t):
    return any(contem(texto, x) for x in [t.get("termo")] + list(t.get("sinonimos") or []))


def checar_aderencia(p, vagas):
    termos = (vagas or {}).get("termos") or []
    if not p or not termos:
        falta = "perfil ainda não lido" if not p else "vagas-alvo ainda não coletadas"
        return [chk("aderencia_termos", "aderencia", "Termos das vagas presentes no perfil", 24, 0,
                    f"Sem medição: {falta}.", "Rodar a rotina de segunda (medir)."),
                chk("aderencia_topo", "aderencia", "Termos principais no título, sobre ou competências", 6, 0,
                    f"Sem medição: {falta}.", "Rodar a rotina de segunda (medir).")], {}
    topo, tudo = texto_perfil(p)
    total = sum(peso_termo(t) for t in termos)
    presentes = [t for t in termos if achou(tudo, t)]
    ausentes = sorted([t for t in termos if not achou(tudo, t)], key=peso_termo, reverse=True)
    taxa = sum(peso_termo(t) for t in presentes) / total if total else 0
    fortes = sorted([t for t in termos if t.get("tipo") != "soft"], key=peso_termo, reverse=True)[:5]
    no_topo = [t for t in fortes if achou(topo, t)]
    fora = [t["termo"] for t in fortes if t not in no_topo]
    n_vagas = len((vagas or {}).get("vagas") or [])
    extra = {
        "taxa": round(taxa, 3),
        "ausentes": [{"termo": t["termo"], "tipo": t.get("tipo"), "peso": peso_termo(t)} for t in ausentes[:15]],
        "presentes": [t["termo"] for t in presentes],
    }
    return [
        chk("aderencia_termos", "aderencia", "Termos das vagas presentes no perfil", 24, taxa,
            f"{round(taxa * 100)}% do peso dos termos de {n_vagas} vagas. Faltam: "
            + (", ".join(t["termo"] for t in ausentes[:8]) or "nenhum") + ".",
            "Incluir só os termos que você de fato domina, onde houver prova (experiência, projeto, competência)."),
        chk("aderencia_topo", "aderencia", "Termos principais no título, sobre ou competências", 6,
            len(no_topo) / len(fortes) if fortes else 0,
            f"{len(no_topo)} de {len(fortes)} no topo do perfil. Fora do topo: " + (", ".join(fora) or "nenhum") + ".",
            "Levar esses termos para o título, o primeiro parágrafo do sobre ou a lista de competências."),
    ], extra


def frases(texto):
    partes = re.split(r"[\n\r•·▪◦]+|(?<=[.;])\s+", texto or "")
    return [x.strip(" -–*\t") for x in partes if len(x.strip(" -–*\t")) > 12]


def checar_perfil(p, vagas):
    if not p:
        return [chk("perfil_lido", "perfil", "Perfil lido", 25, 0, "O perfil do LinkedIn ainda não foi lido.",
                    "Rodar a rotina de segunda (medir) ou colar o PDF do perfil.")]
    out = []
    head = (p.get("headline") or "").strip()
    sobre = (p.get("sobre") or "").strip()
    n = len(head)
    out.append(chk("headline_tamanho", "perfil", "Título com 60 a 220 caracteres", 2,
                   1 if 60 <= n <= 220 else (n / 60 if n < 60 else 0.5),
                   f"Título com {n} caracteres.", "Usar o espaço: função, especialidade e prova, separados por | ."))
    fortes = sorted([t for t in ((vagas or {}).get("termos") or []) if t.get("tipo") != "soft"],
                    key=peso_termo, reverse=True)[:12]
    hn = norm(head)
    if fortes:
        qtd = sum(1 for t in fortes if achou(hn, t))
        fr, det = min(qtd, 2) / 2, f"{qtd} termo(s) das vagas no título."
    else:
        palavras = len(head.split())
        fr, det = min(palavras, 8) / 8, f"Título com {palavras} palavras (sem vagas para comparar)."
    out.append(chk("headline_valor", "perfil", "Título diz o que você faz, não só cargo e empresa", 3, fr, det,
                   "Pôr no título pelo menos dois termos que recrutadores buscam para as vagas-alvo."))
    out.append(chk("sobre_tamanho", "perfil", "Sobre com 600 caracteres ou mais", 2, min(len(sobre), 600) / 600,
                   f"Sobre com {len(sobre)} caracteres (o limite do LinkedIn é 2600).",
                   "Escrever: o problema que você resolve, como, uma prova com número e o que você procura."))
    numeros = [x for x in re.findall(r"\d[\d.,]*", sobre) if not re.fullmatch(r"(19|20)\d\d", x)]
    out.append(chk("sobre_numeros", "perfil", "Sobre com resultados em número", 2, min(len(numeros), 2) / 2,
                   f"{len(numeros)} número(s) no sobre, sem contar anos.",
                   "Trocar adjetivo por medida: volume, prazo, economia, quantidade."))
    sn = norm(sobre)
    out.append(chk("sobre_chamada", "perfil", "Sobre termina com link ou convite ao contato", 2,
                   1 if any(c in sn for c in CHAMADAS) else 0,
                   "Tem link ou convite." if any(c in sn for c in CHAMADAS) else "Sem link nem convite ao contato.",
                   "Fechar o sobre com o link do GitHub e como falar com você."))
    exps = (p.get("experiencias") or [])[:3]
    if exps:
        com_desc = sum(1 for e in exps if len((e.get("descricao") or "").strip()) >= 200)
        com_num = sum(1 for e in exps if re.search(r"\d", e.get("descricao") or ""))
        fr_desc, fr_num = com_desc / len(exps), com_num / len(exps)
        det_desc = f"{com_desc} de {len(exps)} experiências recentes com descrição de 200+ caracteres."
        det_num = f"{com_num} de {len(exps)} experiências recentes com algum número."
        todas = [f for e in exps for f in frases(e.get("descricao"))]
        com_verbo = sum(1 for f in todas if norm(f.split()[0]).startswith(VERBOS)) if todas else 0
        fr_verbo = com_verbo / len(todas) if todas else 0
        det_verbo = f"{com_verbo} de {len(todas)} frases começam por verbo de ação."
    else:
        fr_desc = fr_num = fr_verbo = 0
        det_desc = det_num = det_verbo = "Nenhuma experiência no perfil."
    todas_exps = p.get("experiencias") or []
    fim = (todas_exps[0].get("fim") or "").strip().lower() if todas_exps else None
    atual = fim in ("", "atual", "o momento", "presente")
    out.append(chk("experiencia_atual", "perfil", "Cargo atual no perfil", 2, 1 if (todas_exps and atual) else 0,
                   "A experiência mais recente está em aberto." if (todas_exps and atual) else
                   ("Nenhuma experiência no perfil." if not todas_exps else
                    f"A experiência mais recente termina em {todas_exps[0].get('fim')}. Se há cargo atual, ele não aparece."),
                   "Cadastrar o cargo atual, com o que você faz e com que ferramentas."))
    out.append(chk("experiencia_descricao", "perfil", "Experiências recentes com descrição", 3, fr_desc, det_desc,
                   "Descrever as três últimas: o que fazia, com que ferramenta, com que resultado."))
    out.append(chk("experiencia_numeros", "perfil", "Experiências com resultado medido", 2, fr_num, det_num,
                   "Em cada experiência, pelo menos uma frase com número real."))
    out.append(chk("verbos_acao", "perfil", "Frases começam por verbo de ação", 2, min(fr_verbo / 0.5, 1), det_verbo,
                   "Começar por automatizei, reduzi, implantei, e não por 'responsável por'."))
    achados = [c for c in CLICHES if c in norm(head + " " + sobre)]
    out.append(chk("sem_cliches", "perfil", "Sem clichês no título e no sobre", 1, 0 if achados else 1,
                   ("Clichês: " + ", ".join(achados) + ".") if achados else "Nenhum clichê da lista.",
                   "Cortar o adjetivo e pôr o fato que o provaria."))
    comp = max(len(p.get("competencias") or []), int(p.get("competencias_total") or 0))
    out.append(chk("competencias_qtd", "perfil", "15 competências ou mais", 2, min(comp, 15) / 15,
                   f"{comp} competências listadas.", "Completar com os termos das vagas que você domina."))
    visual = (1 if p.get("foto") else 0) + (1 if p.get("banner") else 0)
    out.append(chk("foto_banner", "perfil", "Foto e imagem de capa", 1, visual / 2,
                   f"Foto: {'sim' if p.get('foto') else 'não'}. Capa: {'sim' if p.get('banner') else 'não'}.",
                   "Capa simples com o que você faz e o endereço do GitHub."))
    slug = urllib.parse.unquote((p.get("url") or "").rstrip("/").rsplit("/", 1)[-1])
    ruim = bool(re.search(r"-(?=[0-9a-z]*\d)[0-9a-z]{7,}$", slug)) or not slug
    out.append(chk("url_personalizada", "perfil", "Endereço do perfil personalizado", 1, 0 if ruim else 1,
                   f"Endereço atual termina em '{slug}'.",
                   "Em 'Editar perfil público e URL', trocar por nome-sobrenome, sem o código no fim."))
    return out


def checar_vitrine(p, gh, alvo):
    out = []
    usuario = (alvo.get("github_user") or "").lower()
    p = p or {}
    campos = [p.get("sobre") or "", " ".join(p.get("links_contato") or [])]
    campos += [d.get("url") or "" for d in p.get("destaques") or []]
    campos += [d.get("url") or "" for d in p.get("projetos") or []]
    tem_link = bool(usuario) and ("github.com/" + usuario) in " ".join(campos).lower()
    out.append(chk("github_no_perfil", "vitrine", "Link do GitHub no perfil do LinkedIn", 3, 1 if tem_link else 0,
                   "Link encontrado." if tem_link else "Nenhum link para o seu GitHub no perfil.",
                   "Pôr o link em Informações de contato e no fim do sobre."))
    dest = len(p.get("destaques") or [])
    out.append(chk("destaques", "vitrine", "Dois itens ou mais em Destaques", 3, min(dest, 2) / 2,
                   f"{dest} item(ns) em Destaques.", "Destacar o repositório principal e um post ou demo dele."))
    proj = sum(1 for x in (p.get("projetos") or []) if x.get("url"))
    out.append(chk("projetos_secao", "vitrine", "Dois projetos com link na seção Projetos", 3, min(proj, 2) / 2,
                   f"{proj} projeto(s) com link.", "Cadastrar cada repositório de vitrine como projeto, com o link."))
    if not gh:
        out.append(chk("github_lido", "vitrine", "GitHub lido", 16, 0, "O GitHub ainda não foi lido.",
                       "Rodar: vitrine.py github"))
        return out
    out.append(chk("github_bio", "vitrine", "Bio preenchida no GitHub", 1, 1 if gh.get("bio") else 0,
                   "Bio preenchida." if gh.get("bio") else "Bio vazia no GitHub.",
                   "Uma linha: o que você constrói e para quem."))
    rp = gh.get("readme_perfil_chars") or 0
    out.append(chk("github_readme_perfil", "vitrine", "README de perfil no GitHub", 2, min(rp, 300) / 300,
                   f"README de perfil com {rp} caracteres.",
                   "No repositório com o seu nome de usuário: quem é, o que constrói, projetos e contato."))
    blog = (gh.get("blog") or "").lower()
    out.append(chk("linkedin_no_github", "vitrine", "Link do LinkedIn no GitHub", 2, 1 if "linkedin.com" in blog else 0,
                   "Link presente." if "linkedin.com" in blog else "O campo de site do GitHub não aponta para o LinkedIn.",
                   "Pôr o endereço do LinkedIn no campo de site do perfil do GitHub."))
    estudo = {x.lower() for x in alvo.get("repos_estudo") or []}
    vit = [r for r in gh.get("repos") or [] if r["nome"].lower() not in estudo and r["nome"].lower() != usuario]
    if not vit:
        out.append(chk("repos", "vitrine", "Repositórios de vitrine", 11, 0, "Nenhum repositório de vitrine.",
                       "Publicar pelo menos um projeto próprio fora dos repositórios de estudo."))
        return out
    itens = [
        ("repo_descricao", "Repositórios com descrição", 2, lambda r: bool(r.get("descricao")),
         "Uma frase: o que faz e para quem."),
        ("repo_readme", "README com 1500 caracteres ou mais", 3, lambda r: (r.get("readme_chars") or 0) >= 1500,
         "README com problema, solução, como rodar, tecnologias e resultado."),
        ("repo_visual", "README com imagem ou demo", 1.5, lambda r: r.get("readme_imagem") or bool(r.get("homepage")),
         "Captura de tela ou GIF no topo do README, ou link de demo."),
        ("repo_homepage", "Link de demo ou site no repositório", 1, lambda r: bool(r.get("homepage")),
         "Preencher o campo Website do repositório."),
        ("repo_topicos", "Três tópicos ou mais", 1.5, lambda r: len(r.get("topicos") or []) >= 3,
         "Tópicos em minúsculas: linguagem, domínio e tipo de projeto."),
        ("repo_licenca", "Licença definida", 1, lambda r: bool(r.get("licenca")),
         "Adicionar um arquivo LICENSE (MIT é o usual em projeto pessoal)."),
        ("repo_recente", "Atualizado nos últimos 90 dias", 1,
         lambda r: dentro_de(r.get("ultimo_push"), 90),
         "Um commit de melhoria real: README, teste ou correção."),
    ]
    for cid, titulo, maximo, teste, como in itens:
        ok = [r["nome"] for r in vit if teste(r)]
        falta = [r["nome"] for r in vit if r["nome"] not in ok]
        out.append(chk(cid, "vitrine", titulo, maximo, len(ok) / len(vit),
                       f"{len(ok)} de {len(vit)}." + (" Faltam: " + ", ".join(falta) + "." if falta else ""), como))
    return out


def checar_atividade(p, registro):
    p = p or {}
    atv = p.get("atividade") or {}

    def reg(tipo, dias):
        return sum(1 for r in registro if r.get("tipo") == tipo and dentro_de(r.get("data"), dias))

    datas_post = [r.get("data") for r in registro if r.get("tipo") == "post"]
    if atv.get("ultimo_post"):
        datas_post.append(atv["ultimo_post"])
    idades = [d for d in (dias_desde(x) for x in datas_post) if d is not None and d >= 0]
    ultimo = min(idades) if idades else None
    fr = 0 if ultimo is None else (1 if ultimo <= 14 else (0.5 if ultimo <= 30 else 0))
    out = [chk("post_recente", "atividade", "Post nos últimos 14 dias", 5, fr,
               "Nenhum post registrado." if ultimo is None else f"Último post há {ultimo} dia(s).",
               "Publicar o rascunho da missão de quinta ou de sábado.")]
    posts30 = max(reg("post", 30), int(atv.get("posts_30d") or 0))
    out.append(chk("ritmo_posts", "atividade", "Quatro posts em 30 dias", 4, min(posts30, 4) / 4,
                   f"{posts30} post(s) em 30 dias.", "Um por semana basta: quinta ou sábado."))
    com7 = max(reg("comentario", 7), int(atv.get("comentarios_7d") or 0))
    out.append(chk("comentarios", "atividade", "Cinco comentários em 7 dias", 4, min(com7, 5) / 5,
                   f"{com7} comentário(s) em 7 dias.", "Usar os comentários prontos da missão de sexta."))
    conv7 = reg("convite", 7)
    out.append(chk("convites", "atividade", "Cinco convites com nota em 7 dias", 3, min(conv7, 5) / 5,
                   f"{conv7} convite(s) registrados em 7 dias.", "Enviar os convites da missão de sexta."))
    con = int(p.get("conexoes") or 0)
    out.append(chk("conexoes", "atividade", "500 conexões", 2, min(con, 500) / 500, f"{con} conexões.",
                   "Cinco convites certos por semana, não cinquenta aleatórios."))
    rec = int(p.get("recomendacoes") or 0)
    out.append(chk("recomendacoes", "atividade", "Duas recomendações recebidas", 2, min(rec, 2) / 2,
                   f"{rec} recomendação(ões).", "Pedir a um gestor e a um colega, com o projeto que eles viram."))
    return out


def calcular():
    alvo = carregar("alvo.json", {}) or {}
    p = carregar("perfil.json")
    vagas = carregar("vagas.json")
    gh = carregar("github.json")
    registro = linhas_jsonl("registro.jsonl")
    ader, extra = checar_aderencia(p, vagas)
    checagens = ader + checar_perfil(p, vagas) + checar_vitrine(p, gh, alvo) + checar_atividade(p, registro)
    cats = {}
    for cid, nome, maximo in CATEGORIAS:
        pts = round(sum(c["pontos"] for c in checagens if c["categoria"] == cid), 1)
        cats[cid] = {"nome": nome, "pontos": pts, "max": maximo}
    total = round(sum(c["pontos"] for c in cats.values()), 1)
    return {
        "data": hoje().isoformat(),
        "total": total,
        "categorias": cats,
        "checagens": checagens,
        "aderencia": extra,
        "fontes": {
            "perfil_lido_em": (p or {}).get("lido_em"),
            "vagas_em": (vagas or {}).get("atualizado_em"),
            "github_lido_em": (gh or {}).get("lido_em"),
        },
    }


def deltas(total, data):
    hist = [h for h in linhas_jsonl("historico.jsonl") if h.get("data", "") < data]
    if not hist:
        return None, None
    hist.sort(key=lambda h: h["data"])
    ontem = round(total - hist[-1]["total"], 1)
    limite = (dt.date.fromisoformat(data) - dt.timedelta(days=7)).isoformat()
    antigos = [h for h in hist if h["data"] <= limite]
    base = antigos[-1] if antigos else hist[0]
    return ontem, round(total - base["total"], 1)


def sinal(x):
    return "sem histórico" if x is None else (f"+{x:g}" if x >= 0 else f"{x:g}")


def cmd_nota(args):
    n = calcular()
    d1, d7 = deltas(n["total"], n["data"])
    n["delta_anterior"], n["delta_semana"] = d1, d7
    salvar("nota.json", n)
    hist = [h for h in linhas_jsonl("historico.jsonl") if h.get("data") != n["data"]]
    hist.append({"data": n["data"], "total": n["total"],
                 "categorias": {k: v["pontos"] for k, v in n["categorias"].items()}})
    hist.sort(key=lambda h: h["data"])
    BASE.mkdir(parents=True, exist_ok=True)
    (BASE / "historico.jsonl").write_text(
        "\n".join(json.dumps(h, ensure_ascii=False) for h in hist) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(n, ensure_ascii=False, indent=2))
        return 0
    print(f"Nota: {n['total']:g}/100 ({sinal(d1)} desde a medição anterior, {sinal(d7)} na semana)")
    print(" · ".join(f"{c['nome']} {c['pontos']:g}/{c['max']}" for c in n["categorias"].values()))
    f = n["fontes"]
    print(f"Fontes: perfil {f['perfil_lido_em'] or 'não lido'} · vagas {f['vagas_em'] or 'não coletadas'}"
          f" · GitHub {f['github_lido_em'] or 'não lido'}")
    perdas = sorted([c for c in n["checagens"] if c["max"] - c["pontos"] > 0.05],
                    key=lambda c: c["max"] - c["pontos"], reverse=True)
    print(f"\nOnde a nota está sendo perdida ({len(perdas)} checagens):")
    for c in perdas[: args.top]:
        print(f"- [{c['categoria']}] {c['titulo']}: {c['pontos']:g}/{c['max']:g}. {c['detalhe']}")
    return 0


def cmd_hoje(_):
    n = carregar("nota.json")
    rotina, cat, titulo = ROTINAS[hoje().weekday()]
    print(f"Rotina de hoje: {rotina}")
    print(titulo)
    if not n:
        print("Ainda não há nota. Rode: vitrine.py nota")
        return 0
    perdas = sorted([c for c in n["checagens"] if c["max"] - c["pontos"] > 0.05 and (cat is None or c["categoria"] == cat)],
                    key=lambda c: c["max"] - c["pontos"], reverse=True)
    feitas = {r.get("checagem") for r in linhas_jsonl("registro.jsonl")
              if r.get("tipo") == "missao" and dentro_de(r.get("data"), 6)}
    print("\nChecagens candidatas (maior perda primeiro; * = já foi missão nos últimos 6 dias):")
    for c in perdas[:6]:
        marca = "*" if c["id"] in feitas else " "
        print(f"{marca} {c['id']} (+{c['max'] - c['pontos']:g}): {c['detalhe']} Como subir: {c['como_subir']}")
    if not perdas:
        print("  Nenhuma perda nesta categoria. Use a de maior perda geral.")
    return 0


def cmd_registrar(args):
    BASE.mkdir(parents=True, exist_ok=True)
    item = {"data": args.data or hoje().isoformat(), "tipo": args.tipo, "nota": args.nota or ""}
    if args.checagem:
        item["checagem"] = args.checagem
    with open(BASE / "registro.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Registrado: {item['tipo']} em {item['data']}.")
    return 0


def cmd_init(_):
    BASE.mkdir(parents=True, exist_ok=True)
    (BASE / "rascunhos").mkdir(exist_ok=True)
    if not (BASE / "alvo.json").exists():
        salvar("alvo.json", {
            "nome": "", "linkedin_url": "", "github_user": "", "posicionamento": "",
            "cargos_alvo": [], "local": "", "temas": [], "repos_estudo": [],
            "pastas_projetos": [], "nunca_citar": [], "leitura_navegador": True,
        })
        print("Criei alvo.json vazio. Preencha antes da primeira medição.")
    print(f"Pasta de estado: {BASE}")
    return 0


def main():
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Motor de nota da skill vitrine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init").set_defaults(fn=cmd_init)
    sub.add_parser("github").set_defaults(fn=cmd_github)
    pn = sub.add_parser("nota")
    pn.add_argument("--json", action="store_true")
    pn.add_argument("--top", type=int, default=10)
    pn.set_defaults(fn=cmd_nota)
    sub.add_parser("hoje").set_defaults(fn=cmd_hoje)
    pr = sub.add_parser("registrar")
    pr.add_argument("--tipo", required=True,
                    choices=["post", "comentario", "convite", "perfil", "repo", "missao"])
    pr.add_argument("--nota", default="")
    pr.add_argument("--checagem", default="")
    pr.add_argument("--data", default="")
    pr.set_defaults(fn=cmd_registrar)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
