"""Exporta o estado da vitrine em tabelas JSON para o painel (Artifact "Vitrine").

Uso: python painel/exportar.py
Lê a pasta de estado (~/.claude/vitrine, ou a que VITRINE_HOME indicar) e grava
em <estado>/painel/dados/ uma lista de linhas por arquivo, mais pagina.json com
a página do painel. Só leitura sobre o estado; não calcula nota.
"""
import datetime as dt
import json
import os
import re
from pathlib import Path

BASE = Path(os.environ.get("VITRINE_HOME") or Path.home() / ".claude" / "vitrine")
SAIDA = BASE / "painel" / "dados"


def ler(nome):
    return json.loads((BASE / nome).read_text(encoding="utf-8"))


def gravar(nome, linhas):
    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / nome).write_text(json.dumps(linhas, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{nome}: {len(linhas)} linha(s)")


def sim_nao(v):
    return "sim" if v else "não"


GITHUB_IDS = re.compile(r"^(github_bio|github_readme|repo_|linkedin_no_github)")
GRUPOS_LINKEDIN = {"aderencia": "Aderência às vagas", "perfil": "Perfil",
                   "vitrine": "Projetos no LinkedIn", "atividade": "Atividade e rede"}


def canal_grupo(c):
    """De que lado a checagem é resolvida (GitHub ou LinkedIn) e o grupo dentro dele."""
    if GITHUB_IDS.match(c["id"]):
        return "github", "Repositórios de vitrine" if c["id"].startswith("repo_") else "Perfil do GitHub"
    return "linkedin", GRUPOS_LINKEDIN[c["categoria"]]


def main():
    alvo, perfil, gh, nota, vagas = (ler(n) for n in
                                     ("alvo.json", "perfil.json", "github.json", "nota.json", "vagas.json"))
    extra_p = BASE / "painel" / "github_extra.json"  # gravado por ler_github.py; opcional
    extra = json.loads(extra_p.read_text(encoding="utf-8")) if extra_p.exists() else {}

    gravar("nota.json", [
        {"categoria": k, "nome": c["nome"], "pontos": c["pontos"], "max": c["max"], "data": nota["data"]}
        for k, c in nota["categorias"].items()])

    gravar("checagens.json", [
        {"id": c["id"], "categoria": c["categoria"], "categoria_nome": nota["categorias"][c["categoria"]]["nome"],
         "canal": canal_grupo(c)[0], "grupo": canal_grupo(c)[1],
         "titulo": c["titulo"], "pontos": c["pontos"], "max": c["max"],
         "detalhe": c["detalhe"], "como_subir": c["como_subir"]}
        for c in nota["checagens"]])

    presentes = set(nota["aderencia"]["presentes"])
    prova = {t["termo"]: t for t in extra.get("termos", [])}
    gravar("termos.json", [
        {"termo": t["termo"], "tipo": t["tipo"], "vagas": len(t["vagas"]),
         "obrigatorio": len(t["obrigatorio_em"]), "no_perfil": sim_nao(t["termo"] in presentes),
         "no_github": sim_nao(prova.get(t["termo"], {}).get("no_github")),
         "onde_github": prova.get(t["termo"], {}).get("onde"),
         "vagas_ids": ",".join(t["vagas"])}
        for t in vagas["termos"]])

    gravar("vagas.json", [
        {"id": v["id"], "titulo": v["titulo"], "empresa": v["empresa"], "url": v["url"],
         "coletada_em": v["coletada_em"]}
        for v in vagas["vagas"]])

    estudo = {x.lower() for x in alvo.get("repos_estudo") or []}
    usuario = gh["usuario"]

    def papel(nome):
        if nome.lower() == usuario.lower():
            return "perfil"
        return "estudo" if nome.lower() in estudo else "vitrine"

    gravar("repos.json", [
        {"nome": r["nome"], "url": r["url"], "papel": papel(r["nome"]), "descricao": r["descricao"],
         "linguagem": r["linguagem"], "topicos": len(r["topicos"]), "licenca": sim_nao(r["licenca"]),
         "demo": sim_nao(r["homepage"]), "readme_chars": r["readme_chars"],
         "readme_imagem": sim_nao(r["readme_imagem"]), "estrelas": r["estrelas"],
         "linguagens": ", ".join(extra.get("repos", {}).get(r["nome"], {}).get("linguagens", {})) or None,
         "commits_12s": extra.get("repos", {}).get(r["nome"], {}).get("commits_janela"),
         "ultimo_push": r["ultimo_push"]}
        for r in gh["repos"]])

    ep = extra.get("perfil", {})
    gravar("github.json", [{
        "usuario": usuario, "url": f"https://github.com/{usuario}", "nome": gh["nome"],
        "bio": gh["bio"], "site": gh.get("blog"), "link_linkedin": sim_nao("linkedin.com" in (gh.get("blog") or "")),
        "seguidores": gh["seguidores"], "repos_publicos": len(gh["repos"]),
        "readme_perfil_chars": gh["readme_perfil_chars"],
        "criado_em": ep.get("criado_em"), "local": ep.get("local"), "seguindo": ep.get("seguindo"),
        "contribuicoes_ano": ep.get("contribuicoes_ano"),
        "fixados": len(ep["fixados"]) if ep.get("fixados") is not None else None,
        "fixados_lista": ", ".join(ep.get("fixados") or []) or None,
        "commits_12s": len(extra["commits"]) if "commits" in extra else None,
        "ultimo_push": max((r["ultimo_push"] for r in gh["repos"]), default=None),
        "lido_em": gh["lido_em"]}])

    # commits públicos por semana (segunda a domingo), 12 semanas até a leitura
    if extra:
        fim = dt.date.fromisoformat(extra["lido_em"])
        seg = fim - dt.timedelta(days=fim.weekday())
        semanas = [seg - dt.timedelta(days=7 * i) for i in range(11, -1, -1)]
        linhas = []
        for s in semanas:
            da = [c for c in extra["commits"] if s <= dt.date.fromisoformat(c["data"]) < s + dt.timedelta(days=7)]
            por = {}
            for c in da:
                por[c["repo"]] = por.get(c["repo"], 0) + 1
            linhas.append({"semana": s.isoformat(), "commits": len(da),
                           "repos": ", ".join(f"{k} ({v})" for k, v in por.items()) or None})
        gravar("gh_commits.json", linhas)

        ling = {}
        for nome, r in extra["repos"].items():
            for l, b in r["linguagens"].items():
                ling.setdefault(l, {"bytes": 0, "repos": []})
                ling[l]["bytes"] += b
                ling[l]["repos"].append(nome)
        gravar("gh_linguagens.json", [
            {"linguagem": l, "bytes": v["bytes"], "repos": ", ".join(v["repos"])}
            for l, v in sorted(ling.items(), key=lambda kv: -kv[1]["bytes"])])

    at, an = perfil.get("atividade", {}), perfil.get("analise_7d", {})
    gravar("linkedin.json", [{
        "url": perfil["url"], "headline": perfil["headline"], "local": perfil["local"],
        "conexoes": perfil["conexoes"], "seguidores": perfil["seguidores"],
        "recomendacoes": perfil["recomendacoes"], "competencias": perfil["competencias_total"],
        "destaques": len(perfil["destaques"]), "projetos": len(perfil["projetos"]),
        "certificados": len(perfil["certificados"]), "ultimo_post": at.get("ultimo_post"),
        "posts_30d": at.get("posts_30d"), "comentarios_7d": at.get("comentarios_7d"),
        "visualizacoes_perfil_7d": an.get("visualizacoes_perfil"),
        "impressoes_posts_7d": an.get("impressoes_posts"),
        "aparicoes_em_busca_7d": an.get("aparicoes_em_busca"), "lido_em": perfil["lido_em"]}])

    hist = [json.loads(l) for l in (BASE / "historico.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    gravar("historico.json", [{"data": h["data"], "total": h["total"], **h["categorias"]} for h in hist])

    # diario.md: "## 2026-10-11 (domingo) · instalação · nota 57.3" e linhas "Chave: valor"
    diario, atual = [], None
    for linha in (BASE / "diario.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"##\s+(\d{4}-\d{2}-\d{2})\s+\(([^)]+)\)\s*·\s*(.+?)\s*·\s*nota\s+([\d.]+)", linha)
        if m:
            atual = {"data": m[1], "dia": m[2], "rotina": m[3], "nota": float(m[4]), "missao": None, "checagem": None}
            diario.append(atual)
        elif atual and linha.startswith("Missão:"):
            atual["missao"] = linha.split(":", 1)[1].strip()
        elif atual and linha.startswith("Checagem:"):
            atual["checagem"] = linha.split(":", 1)[1].strip()
    gravar("diario.json", diario)

    # a página do painel, no formato que o Artifact guarda: {"text": "<html>"}
    pagina = (Path(__file__).resolve().parent / "index.html").read_text(encoding="utf-8")
    (BASE / "painel" / "pagina.json").write_text(json.dumps({"text": pagina}, ensure_ascii=False), encoding="utf-8")
    print("pagina.json: página do painel")


if __name__ == "__main__":
    main()
