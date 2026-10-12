"""Leitura ampliada do GitHub para o painel (só leitura, API e páginas públicas).

Uso: python painel/ler_github.py
Complementa o github.json da rotina com o que ele não traz: dados do perfil,
linguagens por repositório, commits das últimas 12 semanas, contribuições do
ano, repositórios fixados e em que parte do GitHub cada termo das vagas aparece.
Grava <estado>/painel/github_extra.json. Não entra no cálculo da nota.
"""
import base64
import datetime as dt
import importlib.util
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = Path(os.environ.get("VITRINE_HOME") or Path.home() / ".claude" / "vitrine")
MOTOR = Path(__file__).resolve().parent.parent / "skill" / "scripts" / "vitrine.py"
JANELA_DIAS = 84  # 12 semanas

spec = importlib.util.spec_from_file_location("vitrine", MOTOR)
motor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(motor)  # reaproveita norm/achou: a mesma regra de casamento da nota


def baixar(url, json_=True):
    cab = {"User-Agent": "vitrine-painel", "Accept": "application/vnd.github+json" if json_ else "text/html"}
    with urllib.request.urlopen(urllib.request.Request(url, headers=cab), timeout=25) as r:
        corpo = r.read().decode("utf-8", "replace")
    return json.loads(corpo) if json_ else corpo


def tentar(fn, padrao=None):
    try:
        return fn()
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as e:
        print(f"AVISO: {e}", file=sys.stderr)
        return padrao


def main():
    alvo = json.loads((BASE / "alvo.json").read_text(encoding="utf-8"))
    gh = json.loads((BASE / "github.json").read_text(encoding="utf-8"))
    vagas = json.loads((BASE / "vagas.json").read_text(encoding="utf-8"))
    u = alvo["github_user"]
    estudo = {x.lower() for x in alvo.get("repos_estudo") or []}
    hoje = dt.date.today()
    desde = hoje - dt.timedelta(days=JANELA_DIAS)

    perfil = baixar(f"https://api.github.com/users/{u}")
    saida = {
        "lido_em": hoje.isoformat(),
        "janela_desde": desde.isoformat(),
        "perfil": {
            "criado_em": (perfil.get("created_at") or "")[:10],
            "seguindo": perfil.get("following"),
            "local": perfil.get("location"),
            "empresa": perfil.get("company"),
            "email_publico": bool(perfil.get("email")),
            "disponivel_para_contratacao": perfil.get("hireable"),
        },
        "repos": {},
        "commits": [],
    }

    html = tentar(lambda: baixar(f"https://github.com/users/{u}/contributions", json_=False), "")
    m = re.search(r"([\d,.]+)\s+contributions?\s+in the last year", re.sub(r"\s+", " ", html or ""))
    saida["perfil"]["contribuicoes_ano"] = int(re.sub(r"[,.]", "", m[1])) if m else None

    html = tentar(lambda: baixar(f"https://github.com/{u}", json_=False), "")
    fix = re.findall(r'pinned-item-list-item-content.*?<span class="repo"[^>]*>\s*([^<\s]+)', html or "", re.S)
    saida["perfil"]["fixados"] = fix if "pinned-item-list-item-content" in (html or "") or fix else None

    corpus = {}  # repo -> {parte: texto}
    for r in gh["repos"]:
        nome = r["nome"]
        papel = "perfil" if nome.lower() == u.lower() else ("estudo" if nome.lower() in estudo else "vitrine")
        linguagens = tentar(lambda: baixar(f"https://api.github.com/repos/{u}/{nome}/languages"), {}) or {}
        commits = tentar(lambda: baixar(
            f"https://api.github.com/repos/{u}/{nome}/commits?since={desde.isoformat()}T00:00:00Z&per_page=100"), []) or []
        datas = sorted((c.get("commit", {}).get("author", {}).get("date") or "")[:10] for c in commits)
        saida["repos"][nome] = {"papel": papel, "linguagens": linguagens, "commits_janela": len(datas)}
        saida["commits"] += [{"repo": nome, "data": d} for d in datas if d]
        if papel != "estudo":
            readme = tentar(lambda: base64.b64decode(
                baixar(f"https://api.github.com/repos/{u}/{nome}/readme").get("content") or "").decode("utf-8", "replace"), "")
            corpus[nome] = {
                "nome ou descrição": f"{nome} {r.get('descricao') or ''}",
                "tópicos": " ; ".join(r.get("topicos") or []),
                "linguagens": " ; ".join(linguagens),
                "README": readme or "",
            }

    termos = []
    for t in vagas["termos"]:
        onde = []
        for nome, partes in corpus.items():
            achadas = [parte for parte, texto in partes.items() if motor.achou(motor.norm(texto), t)]
            if achadas:
                onde.append(f"{nome}: {', '.join(achadas)}")
        termos.append({"termo": t["termo"], "no_github": bool(onde), "onde": "; ".join(onde) or None})
    saida["termos"] = termos

    (BASE / "painel").mkdir(parents=True, exist_ok=True)
    (BASE / "painel" / "github_extra.json").write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"GitHub ampliado: {len(saida['commits'])} commit(s) desde {desde}, "
          f"{sum(1 for t in termos if t['no_github'])} de {len(termos)} termos com prova.")


if __name__ == "__main__":
    main()
