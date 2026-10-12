# Formatos dos arquivos de estado

O script lê estes campos pelo nome. Campos extras são ignorados, então pode
acrescentar observações (`*_obs`), mas não renomeie nem remova os listados.

## perfil.json

```json
{
  "lido_em": "AAAA-MM-DD",
  "fonte": "navegador logado | visão pública | PDF | colado pelo usuário",
  "url": "https://www.linkedin.com/in/<slug>/",
  "headline": "",
  "sobre": "texto inteiro, com as quebras de linha",
  "local": "",
  "foto": true,
  "banner": true,
  "conexoes": 500,
  "seguidores": 0,
  "recomendacoes": 0,
  "experiencias": [
    {"cargo": "", "empresa": "", "inicio": "AAAA-MM", "fim": "AAAA-MM ou vazio se atual", "descricao": "uma frase por linha"}
  ],
  "formacao": [{"curso": "", "instituicao": "", "inicio": "", "fim": ""}],
  "competencias": ["só as lidas por nome"],
  "competencias_total": 0,
  "destaques": [{"titulo": "", "url": ""}],
  "projetos": [{"nome": "", "url": "", "descricao": ""}],
  "certificados": [{"nome": "", "emissor": "", "data": ""}],
  "links_contato": ["urls da caixa Dados de contato"],
  "atividade": {"ultimo_post": "AAAA-MM-DD ou null", "posts_30d": 0, "comentarios_7d": 0}
}
```

Regras de preenchimento:

- `experiencias` da mais recente para a mais antiga. A primeira com `fim`
  vazio conta como cargo atual.
- "Mais de 500 conexões" vira `500`.
- `ultimo_post` é o último post **próprio**, não compartilhamento. "há 6 m"
  vira a data de hoje menos seis meses; diga em `ultimo_post_obs` que é
  aproximada.
- Se uma leitura não mostrar um campo (visão pública esconde título e
  experiências), **mantenha o valor do retrato anterior** e anote em `fonte`
  que a leitura foi parcial. Zerar o campo derrubaria a nota por um problema
  de leitura, não do perfil.
- Texto de terceiros que aparece na página (posts compartilhados, "pessoas que
  talvez você conheça") não entra no retrato.

## vagas.json

```json
{
  "atualizado_em": "AAAA-MM-DD",
  "fonte": "de onde vieram",
  "vagas": [{"id": "v1", "titulo": "", "empresa": "", "url": "", "coletada_em": ""}],
  "termos": [
    {"termo": "Python", "sinonimos": ["python3"], "tipo": "hard | soft | cargo | formacao",
     "vagas": ["v1", "v3"], "obrigatorio_em": ["v1"]}
  ]
}
```

Como o script pesa: cada vaga que cita o termo vale 1, ou 2 se o termo está
nos requisitos obrigatórios dela; termo `soft` vale metade. A aderência é o
peso dos termos encontrados no perfil dividido pelo peso total. A busca ignora
acentos e maiúsculas e exige a palavra inteira (`Git` não casa com `GitHub`;
por isso `GitHub` vai em `sinonimos`).

Regras de extração:

- De 5 a 8 vagas, publicadas nos últimos 30 dias quando houver, cobrindo os
  `cargos_alvo`. Troque no máximo metade das vagas por semana e reaproveite a
  grafia dos termos da semana anterior: trocar tudo de uma vez faz a nota
  variar por causa da amostra, não do perfil.
- Um termo só entra se estiver escrito na vaga. Não complete com o que "vaga
  assim costuma pedir".
- `obrigatorio_em` é para o que a vaga lista em requisitos; "diferencial" e
  "desejável" ficam só em `vagas`.
- Em `sinonimos`, ponha as formas que o perfil poderia usar com honestidade
  para a mesma coisa (`dashboard` para `Dashboards`, `REST API` para `APIs`).
  Não ponha um termo mais fraco como sinônimo de um mais forte.
- De 25 a 40 termos. Benefícios, frases de cultura e nome da empresa não são
  termos.

## registro.jsonl

Uma linha por evento, escrita por `VITRINE registrar`:
`{"data": "AAAA-MM-DD", "tipo": "missao|post|comentario|convite|perfil|repo", "nota": "", "checagem": ""}`.
As checagens de atividade contam `post` em 30 dias e `comentario` e `convite`
em 7 dias.

## diario.md

Mais nova em cima:

```
## AAAA-MM-DD (dia) · rotina · nota N
Missão: <resumo em uma linha por ação>
Checagem: <id>
Ângulo ou fonte usada: <para não repetir>
```
