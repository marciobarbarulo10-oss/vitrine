# Rotinas por dia

Leia só a seção do dia. Em todas: a missão sai das checagens que `VITRINE hoje`
listou, na ordem, pulando as marcadas com `*`. Se a categoria do dia não tem
perda, use a checagem de maior perda geral e diga isso em "Por quê".

Sumário: [medir](#medir-segunda) · [perfil](#perfil-terça) ·
[vitrine](#vitrine-quarta) · [topico](#topico-quinta) ·
[conexoes](#conexoes-sexta) · [bastidor](#bastidor-sábado) ·
[fechamento](#fechamento-domingo)

## medir (segunda)

É a nova varredura, como o "scan" do Jobscan. Tudo que o usuário fez na semana
aparece aqui sem ele precisar marcar nada.

1. **Perfil.** Se `alvo.json.leitura_navegador` for true, abra `linkedin_url`
   no navegador em que ele está logado (Claude in Chrome; carregue as
   ferramentas com ToolSearch se estiverem adiadas). Role a página três vezes,
   esperando dois segundos entre elas, para as seções carregarem, e leia como
   texto. Uma página basta para título, sobre, destaques, atividade,
   experiências, formação, certificados, projetos e total de competências.
   Feche a aba no fim. Sem Chrome logado, use o navegador embutido: a visão
   pública mostra só parte (atividade, certificados, projetos), então mantenha
   do retrato anterior o que ela esconde. Sem navegador nenhum, mantenha tudo
   e avise.
   Reescreva `perfil.json` no formato de `formatos.md`. Guarde o retrato
   anterior em `perfil.anterior.json` antes, para o passo 4.
2. **Vagas.** Para cada `cargos_alvo`, uma busca. Prefira o conector de vagas
   da conta (ferramentas `search_jobs` e `get_job_details`, via ToolSearch);
   sem ele, WebSearch por vagas abertas em `alvo.json.local`. Abra as
   descrições, escolha de 5 a 8 e reescreva `vagas.json` seguindo as regras de
   extração de `formatos.md`.
3. `VITRINE github`, `VITRINE nota`.
4. **O que mudou.** Compare `perfil.json` com `perfil.anterior.json` e o
   `github.json` de agora com as checagens da semana passada. Liste o que ele
   fez (título novo, projeto cadastrado, README ampliado) e o que continua
   igual apesar de ter sido missão.
5. **Plano da semana.** As três checagens de maior perda que se resolvem em
   menos de quinze minutos cada. Diga em que dia cada uma vai virar missão.
6. **Fatos.** Se a leitura trouxe algo que não está em `fatos.md` (cargo novo,
   certificado), acrescente com a origem.

Mensagem: bloco "SEMANA" com nota, variação, o que mudou e o plano.

## perfil (terça)

Uma correção de texto no perfil, a de maior perda.

- `aderencia_termos` e `aderencia_topo`: pegue os termos ausentes de
  `nota.json.aderencia.ausentes`. Para cada um, procure prova em `fatos.md`.
  Com prova: diga em que seção ele entra (competência, frase de experiência,
  sobre) e escreva a frase. Sem prova: liste em "lacunas reais" com uma linha
  sobre estudar ou ignorar. No máximo cinco termos por missão. Confira
  `competencias_obs`: se a lista de competências não foi lida inteira, peça
  para ele conferir antes de adicionar.
- `headline_*`: escreva o título novo inteiro, até 220 caracteres, com os dois
  termos de maior peso que ele prova.
- `sobre_*`: reescreva o sobre inteiro, não um remendo. Estrutura: problema que
  ele resolve; como; uma prova com número; o que procura; link do GitHub e como
  falar com ele.
- `experiencia_atual`: se `fatos.md` tem um cargo atual que não está no
  perfil, escreva a entrada (cargo, empresa, início, três frases). Se
  `fatos.md` diz para confirmar antes de citar, a missão é a pergunta.
- `experiencia_*`, `verbos_acao`: reescreva a descrição de uma experiência,
  uma frase por linha, verbo no início, número onde houver fato.
- `competencias_qtd`, `foto_banner`, `url_personalizada`: instrução curta e o
  link.

Onde: título e sobre ficam no lápis do topo do perfil e da seção Sobre, em
`linkedin_url`; experiências em `<linkedin_url>details/experience/`;
competências em `<linkedin_url>details/skills/`.

## vitrine (quarta)

Um projeto mais visível, no GitHub e no LinkedIn.

1. Escolha o repositório de vitrine que mais perde ponto (os de
   `alvo.json.repos_estudo` não contam). Se o código está numa pasta de
   `pastas_projetos`, leia-o (só leitura) para escrever com precisão. Nunca
   copie para o texto credencial, dado de cliente ou nome interno.
2. Escreva em `rascunhos/<data>-<repo>/` o que falta, conforme a checagem:
   - `repo_readme`, `repo_visual`: `README.md` completo. Problema, solução,
     captura de tela (peça a imagem se não houver), como rodar, tecnologias,
     resultado medido, contato.
   - `repo_descricao`, `repo_topicos`, `repo_homepage`: uma frase de
     descrição, de 5 a 8 tópicos em minúsculas e o link de demo. Onde: a
     engrenagem ao lado de "About" em `https://github.com/<usuario>/<repo>`.
   - `repo_licenca`: onde,
     `https://github.com/<usuario>/<repo>/community/license/new?template=mit`.
   - `github_bio`: uma linha. Onde: `https://github.com/settings/profile`.
   - `github_readme_perfil`: README do repositório com o nome do usuário.
3. Para o LinkedIn, conforme `projetos_secao`, `destaques`, `github_no_perfil`:
   o texto da entrada em Projetos (nome, período, descrição de até 2000
   caracteres, link) e a instrução para pôr o repositório em Destaques. Onde:
   `<linkedin_url>details/projects/` e `<linkedin_url>details/featured/`.
4. Na mensagem, mostre o texto curto inteiro; para arquivo longo, dê o caminho
   do rascunho e diga que ele pode responder "aplicar".

## topico (quinta)

Um assunto que valha compartilhar, com fonte.

1. Escolha um tema de `alvo.json.temas` que não apareça nas últimas 4 entradas
   de `diario.md`.
2. WebSearch por novidade dos últimos 7 a 14 dias nesse tema. Prefira fonte
   primária (órgão regulador, documentação oficial, release de ferramenta,
   relatório com dados). Abra a página e confirme a data e o fato. Sem
   novidade real, use um aprendizado dele ligado ao tema, tirado de
   `fatos.md`.
3. Escreva o post, de 600 a 1100 caracteres: o que mudou ou o que é, em uma
   frase; o que isso significa na prática, a partir de algo que ele viveu e
   que está em `fatos.md`; uma pergunta de verdade no fim; o link da fonte.
   Não finja opinião de especialista sobre o que ele nunca fez.
4. Dê também uma alternativa de dois minutos: compartilhar a fonte com duas
   linhas de comentário.

Onde: `https://www.linkedin.com/feed/?shareActive=true`.

## conexoes (sexta)

Cinco pessoas e três comentários. Poucos e certos: convite sem motivo é o que
ele já não faz, e convite em massa é o que derruba conta.

**Pessoas.** Procure com WebSearch (`site:linkedin.com/in`), sem usar a busca
do LinkedIn logado. Fontes, nesta ordem:
1. Quem trabalha na área das vagas de `vagas.json`, nas mesmas empresas
   (recrutadores de tecnologia e operações, líderes de automação, dados ou
   logística).
2. Autores de conteúdo sobre os `temas`.
3. Ex-colegas e ex-alunos das empresas e faculdades de `fatos.md`.

Para cada pessoa: nome, cargo, link do perfil, o motivo em uma linha (um fato
verificável: vaga aberta, post, empresa em comum) e a nota de convite com até
200 caracteres. A nota cita o motivo, diz quem ele é em meia frase e não pede
nada. Não repita ninguém que já esteja em `diario.md`.

**Comentários.** Três posts recentes da área (WebSearch com
`site:linkedin.com/posts` e um tema, ou newsletter do setor). Para cada um: o
link e um comentário de duas a quatro frases que acrescente um fato da
experiência dele. "Ótimo post" não é comentário.

Lembre na mensagem que cada convite e cada comentário enviados contam quando
ele responde "feito".

## bastidor (sábado)

O que ele construiu ou aprendeu na semana, em público.

1. Para cada pasta de `pastas_projetos`:
   `git -C "<pasta>" log --since="7 days ago" --pretty="%ad %s" --date=short`.
   Veja também `ultimo_push` em `github.json`. Só leitura.
2. Havendo trabalho na semana: post no molde problema, o que fiz, o que
   aprendi, link do repositório. Fale do problema em termos gerais se o
   trabalho for de empregador, e respeite `nunca_citar`.
3. Não havendo: um ângulo ainda não usado de um projeto de `fatos.md` (uma
   decisão técnica, um erro, um número) ou algo do curso de Engenharia de
   Software. Anote o ângulo em `diario.md`.
4. Sugira uma imagem que ele já tem (captura do dashboard, trecho de código).

Onde: `https://www.linkedin.com/feed/?shareActive=true`.

## fechamento (domingo)

Sem tarefa nova. Bloco "SEMANA":

- nota de segunda e nota de hoje, por categoria (de `historico.jsonl`);
- o que subiu e por quê, em uma linha cada;
- missões entregues que a medição mostra não feitas, sem cobrança, só a lista;
- no máximo uma pergunta, se há um fato faltando que travou alguma missão;
- o que vem na segunda.
