# De onde vem cada checagem

A nota segue a mecânica de dez otimizadores de perfil e currículo, analisados
em outubro de 2026. Consulte quando o usuário perguntar por que uma checagem existe ou
quiser mudar um peso (os pesos estão em `scripts/vitrine.py`, um por chamada
de `chk`).

| categoria (pontos) | checagens | inspirada em |
| --- | --- | --- |
| Aderência às vagas (30) | `aderencia_termos`, `aderencia_topo` | Jobscan (perfil comparado a 3 ou mais vagas; termos no título, sobre e competências) e Resume Worded (requisito obrigatório pesa mais que desejável) |
| Perfil (25) | `headline_*`, `sobre_*`, `experiencia_*`, `verbos_acao`, `sem_cliches`, `competencias_qtd`, `foto_banner`, `url_personalizada` | Resume Worded (impacto, brevidade, estilo), Enhancv (quantificar impacto, verbos de ação, repetição), Rezi (critérios nomeados com correção priorizada), Teal (checklist por seção, com "checar de novo") |
| Vitrine de projetos (25) | `github_no_perfil`, `destaques`, `projetos_secao`, `github_bio`, `github_readme_perfil`, `linkedin_no_github`, `repo_*` | Não existe nos dez produtos: nenhum olha o GitHub. É a parte própria desta skill, no mesmo molde de checklist |
| Atividade e rede (20) | `post_recente`, `ritmo_posts`, `comentarios`, `convites`, `conexoes`, `recomendacoes` | Jobscan (dicas de rede) e o rastreador de Teal e Huntr (registro do que foi feito) |

O que não foi copiado, de propósito:

- Nota de "ATS". Os próprios produtos admitem que não há nota universal; aqui
  a aderência é declarada como contagem de termos e nada mais.
- Reescrita em um clique. O texto é escrito a partir de `fatos.md`, e termo
  sem prova não entra.
- Limite de varreduras e bloqueio de palavras-chave: não há o que vender.
