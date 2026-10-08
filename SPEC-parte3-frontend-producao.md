# SPEC 3 — Front-end próprio e deploy em produção

> Continuação da `SPEC-parte1-cicd-deploy.md` e da `SPEC-parte2-rag.md`, que já estão implementadas.
> Fluxo: ler a spec → gerar o plano de tarefas → implementar uma tarefa por vez → validar pelos critérios de aceite.
> Toda mudança de comportamento começa aqui, não no código.

---

## 1. Objetivo

Dar ao assistente **cara de produto**: uma interface própria, bonita e responsiva, servida junto com uma API num único serviço no **Railway**, com HTTPS no subdomínio `<servico>.up.railway.app`. A base de conhecimento passa a aceitar **PDF**, convertido para Markdown na indexação. O deploy continua passando pelo portão: o Railway só publica depois que os testes e a avaliação da busca passam, e o health check confere o site antes de trocar a versão.

## 2. Público

- **Quem configura:** aluno de nível intermediário. Continua editando o `config.yml` e a pasta `documentos/`; ajusta a interface com o assistente de programação.
- **Quem usa:** o público final do assistente, agora num endereço próprio, no computador e no celular.

## 3. Escopo

**Dentro:**
- Front-end em React + Vite, com Tailwind CSS: chat com streaming, cartões de fonte com o trecho usado, sugestões iniciais, modo claro e escuro, responsivo, estados de vazio, carregando, erro e "não encontrei".
- Servidor FastAPI que expõe a API e serve o front-end compilado, no mesmo endereço.
- PDF na pasta `documentos/`, convertido para Markdown na indexação.
- Limites de uso: tamanho da pergunta, tamanho do histórico e perguntas por minuto por visitante.
- Deploy no Railway com Docker, configuração em `railway.json`, com **Wait for CI** ligado: o Railway só publica o commit depois que todos os jobs do GitHub Actions passam.
- Verificação pós-deploy: o pipeline confere que a versão nova está no ar e saudável.

**Fora:**
- Login, conversas salvas, painel administrativo, pagamento.
- Envio de documentos pela interface.
- Domínio próprio (fica o subdomínio do Railway; a apostila explica o caminho).
- OCR para PDF escaneado.

## 4. Arquitetura

```
Navegador ──HTTPS──► Railway (um serviço, contêiner Docker)
  React (estático)      ├── /            front-end compilado (frontend/dist)
                        └── /api/...     FastAPI: busca no Supabase, monta o prompt,
                                         chama o provedor de IA, devolve em streaming
                                  │                         │
                                  ▼                         ▼
                        Supabase (trechos)        OpenRouter / Anthropic / OpenAI

GitHub Actions: testar ──► avaliar ──► publicar ──► Railway (Wait for CI)
                T1…T17     índice +    promove       build da imagem, health check
                + build    T14         o índice      /api/saude e troca de versão
```

| Peça | Onde roda | O que guarda de segredo |
|---|---|---|
| Interface React | Navegador do visitante | **Nada.** Todo código do front-end é público |
| API FastAPI | Railway | `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, chaves dos provedores |
| Indexação e avaliação | GitHub Actions | `SUPABASE_URL`, `SUPABASE_SECRET_KEY` |
| Trechos e busca híbrida | Supabase | — (inalterado da parte 2) |

## 5. Stack e restrições

| Item | Decisão | Motivo |
|---|---|---|
| Front-end | React 19 + Vite, JavaScript (JSX), Tailwind CSS 4 (plugin `@tailwindcss/vite`, sem arquivo de configuração), `react-markdown`, ícones `lucide-react` | Componentes, build rápido, visual moderno sem CSS manual |
| Servidor | FastAPI + Uvicorn | API com validação (Pydantic), streaming e arquivos estáticos no mesmo app |
| Streaming | Server-Sent Events (SSE) sobre `POST /api/perguntar` | Texto chega aos poucos; mais simples que WebSocket |
| Provedores | Os da parte 1, reaproveitados em `chat.py` | Nada muda no comportamento |
| Busca | `rag.buscar` da parte 2 | Nada muda |
| PDF → Markdown | `pymupdf4llm`, só na indexação (GitHub Actions) | Preserva títulos e tabelas. Licença AGPL: fica fora do servidor; alternativa MIT: `markitdown` |
| Contêiner | Docker multi-stage: Node compila o front, Python roda o servidor | Mesmo ambiente no computador e no Railway |
| Hospedagem | Railway, builder Docker, definido em `railway.json` | HTTPS automático, logs, health check, rollback, build em máquina separada |

**Restrições conhecidas:**
- R13. **Memória.** O modelo de embedding é baixado **durante o build da imagem** e carregado uma vez, ao iniciar. Primeira tentativa no Render: nos planos de 512 MB, o próprio build da imagem estourou a memória (o Render limita o build à RAM do plano). No Railway, o build roda em máquinas separadas e o serviço usa a memória que precisar, cobrada por uso.
- R14. **Custo.** O Railway cobra por uso (CPU e memória por minuto), com um valor mínimo mensal no plano Hobby. O serviço fica sempre ligado; para pausar, remova o deploy ou desligue o serviço no painel.
- R15. **Wait for CI ligado.** Se o Railway publicasse a cada commit, o portão seria ignorado. Com **Wait for CI** (Settings → Source), ele espera o GitHub Actions: se algum job falhar, o deploy daquele commit é pulado e a versão anterior continua no ar.
- R16. **Nada de segredo no front-end.** Variáveis com prefixo `VITE_` são embutidas no JavaScript entregue ao navegador. Nenhuma chave pode usar esse prefixo, e o front-end só conhece rotas relativas (`/api/...`).
- R17. **Porta.** O Railway informa a porta na variável `PORT`; o servidor escuta em `0.0.0.0:$PORT`.
- R18. **Binários.** Com o deploy fora do Hugging Face, PDFs podem ficar no repositório (limite do GitHub: 100 MB por arquivo). A regra de não versionar outros binários continua.

## 6. Arquivos do projeto

```
frontend/                    NOVO   interface React + Vite
  index.html, package.json, package-lock.json, vite.config.js, .gitignore
  src/main.jsx, src/App.jsx, src/api.js, src/index.css
  src/components/ Cabecalho.jsx, Conversa.jsx, Mensagem.jsx, CartaoFonte.jsx,
                  Sugestoes.jsx, CaixaPergunta.jsx, AlternarTema.jsx
servidor.py                  NOVO   FastAPI: rotas /api e o front-end compilado
chat.py                      NOVO   provedores e geração da resposta (vem do app.py)
testes_api.py                NOVO   testes da API com provedores e busca simulados (T16)
Dockerfile, .dockerignore    NOVOS  imagem do serviço
railway.json                 NOVO   o serviço do Railway como código (build e health check)
rag.py                       MUDA   lê .pdf além de .md
testes.py                    MUDA   T11 aceita .pdf; T6 confere servidor.py e chat.py; + T15, T17
config.yml                   MUDA   bloco opcional interface (seção 7)
requirements.txt             MUDA   + fastapi, uvicorn; − gradio (não é mais usado)
.github/workflows/deploy.yml MUDA   build do front no testar; publicar só promove o índice; sai o envio ao Hugging Face
app.py                       REMOVIDO  substituído por servidor.py + chat.py
README.md                    MUDA   sem o cabeçalho do Hugging Face; como rodar e publicar
```

## 7. Contrato do `config.yml` (campos novos)

Os campos das partes 1 e 2 não mudam. A interface usa `nome`, `descricao`, `tema`, `logo`, `logo_altura` e `exemplos` que já existem. Entra um bloco opcional:

| Campo | Obrigatório | Tipo / valores | Padrão |
|---|---|---|---|
| `interface.tema_inicial` | não | `claro`, `escuro` ou `sistema` (segue o dispositivo) | `sistema` |
| `interface.rodape` | não | texto curto exibido no rodapé | `Respostas geradas por IA com base no material de consulta.` |
| `interface.limite_caracteres` | não | inteiro de 200 a 4000: tamanho máximo da pergunta | 2000 |
| `interface.perguntas_por_minuto` | não | inteiro de 1 a 60, por visitante | 10 |

As cores da interface vêm do `tema` da parte 1: o servidor traduz cada nome (`azul`, `verde`...) para uma escala de cores hexadecimais e entrega ao front-end.

## 8. Contrato da API

Todas as rotas ficam sob `/api`. O front-end usa caminhos relativos.

| Rota | Recebe | Devolve | Erros |
|---|---|---|---|
| `GET /api/saude` | — | `{"status": "ok", "versao": "<commit>", "trechos_na_producao": N}` | 503 se o banco ou o modelo de embedding não estiverem prontos |
| `GET /api/config` | — | `{nome, descricao, exemplos, logo_url, logo_altura, cores: {principal, secundaria}, interface: {...}}`. **Nunca** inclui chaves, modelos, prompt ou provedores | — |
| `POST /api/perguntar` | `{"mensagem": "...", "historico": [{"role": "user"\|"assistant", "content": "..."}]}` | `text/event-stream` com os eventos abaixo | 422 entrada inválida; 413 pergunta acima do limite; 429 limite por minuto (com `Retry-After`) |
| `GET /api/logo` | — | a logo do `config.yml` (arquivo .svg ou redirecionamento para o link https) | 404 |

**Eventos do `/api/perguntar`**, nesta ordem:

```
event: fontes      data: [{"n": 1, "fonte": "...", "secao": "...", "trecho": "..."}]
event: texto       data: {"delta": "pedaço da resposta"}        (repete)
event: fim         data: {"nao_encontrado": false}
event: erro        data: {"mensagem": "texto para o usuário"}   (em vez de fim, se falhar)
```

`versao` vem da variável `RAILWAY_GIT_COMMIT_SHA`, que o Railway preenche; localmente, `dev`. As fontes só aparecem na interface se `nao_encontrado` for `false`. O histórico aceito tem no máximo 20 mensagens; o excedente mais antigo é descartado.

## 9. Requisitos funcionais

Continuação da numeração da parte 2.

**Servidor**
- **RF16 — Reaproveitamento:** `chat.py` concentra o que o `app.py` fazia com os provedores (ordem do `config.yml`, troca automática em caso de falha, desligar raciocínio). Nenhum comportamento das partes 1 e 2 muda.
- **RF17 — Streaming:** `POST /api/perguntar` busca os trechos (RF10), envia o evento `fontes`, transmite a resposta em eventos `texto` e termina com `fim` ou `erro`.
- **RF18 — Inicialização:** ao iniciar, o servidor carrega o modelo de embedding e conecta ao Supabase uma vez; o log mostra `Base de conhecimento: ... trechos na produção` (como o RF14).
- **RF19 — Limites:** perguntas acima de `limite_caracteres` recebem 413; mais de `perguntas_por_minuto` do mesmo visitante (IP do cabeçalho `X-Forwarded-For`, primeiro valor) recebem 429 com `Retry-After`. O contador fica em memória.
- **RF20 — Front-end estático:** o servidor entrega `frontend/dist` em `/` e responde `index.html` para caminhos que não sejam `/api`.
- **RF21 — Erros amigáveis:** falhas de banco, chave ou provedor viram um evento `erro` com mensagem em português, sem detalhes internos, e o detalhe técnico vai para o log.

**Interface**
- **RF22 — Identidade:** cabeçalho com logo, nome e descrição; cores do `tema`; título da aba com o `nome`.
- **RF23 — Tela inicial:** sem conversa, mostra uma saudação curta e as `exemplos` como sugestões clicáveis.
- **RF24 — Conversa:** mensagens do usuário e do assistente em balões distintos; a resposta aparece aos poucos, em Markdown (listas, negrito, código); rolagem acompanha a resposta; botão de copiar.
- **RF25 — Fontes:** abaixo da resposta, cartões numerados com `fonte › seção`; ao clicar, o cartão expande e mostra o trecho usado.
- **RF26 — Estados:** indicador de "pensando" até o primeiro pedaço; mensagem de erro com botão "tentar de novo"; resposta "não encontrei" sem cartões; aviso amigável no 429 com o tempo de espera.
- **RF27 — Caixa de pergunta:** Enter envia, Shift+Enter quebra linha; contador de caracteres perto do limite; botão desabilitado enquanto responde.
- **RF28 — Tema e celular:** alternância claro/escuro lembrada no navegador; layout funcional a partir de 360 px de largura.
- **RF29 — Acessibilidade:** contraste adequado nos dois temas, navegação por teclado, rótulos nos botões só com ícone.

**PDF**
- **RF30 — Leitura de PDF:** `rag.py` lê `.md` e `.pdf` da pasta. O PDF é convertido para Markdown com `pymupdf4llm`; linhas que se repetem em mais da metade das páginas (cabeçalhos e rodapés) e números de página soltos são removidos. Depois disso, a divisão em trechos (RF7) e as fontes (RF12) funcionam igual, com `fonte` sendo o nome do `.pdf`.
- **RF31 — PDF sem texto:** se a conversão de um PDF gerar menos de 200 caracteres, a indexação para com a mensagem `PDF sem texto extraível (escaneado?): <arquivo>`.

## 10. Segurança

- **Chaves só no servidor (R16).** O front-end não lê variáveis de ambiente com segredo e só chama `/api`. O T17 procura padrões de chave no build.
- **Chaves no Railway:** cadastradas em Variables do serviço, nunca no `railway.json` nem no código.
- **Menor privilégio:** o servidor usa a chave publicável do Supabase (só lê a produção). A chave secreta continua só no GitHub.
- **Abuso e custo:** limites do RF19; sem endpoint que aceite prompt de sistema ou modelo vindos do navegador.
- **Injeção de prompt:** mantidas as regras da parte 2 (trechos delimitados, instrução para ignorar ordens dentro deles).
- **Logs:** não registrar o texto completo das perguntas; registrar só tamanho, tempo e erros. Se um dia guardar conversas, isso é LGPD (fora do escopo).

## 11. Portão de testes

Os testes das partes 1 e 2 continuam valendo, com dois ajustes: o **T6** confere a sintaxe de `servidor.py` e `chat.py` (o `app.py` deixa de existir) e o **T11** aceita `.md` e `.pdf` na pasta de documentos (o `.pdf` dispensa a checagem de título, feita depois da conversão).

**No `testes.py`** (job `testar`):
- **T15:** o bloco `interface` respeita o contrato da seção 7.
- **T17:** o front-end compilado (`frontend/dist`) não contém padrões de chave (`sk-or-`, `sk-ant-`, `sk-proj-`, `sb_secret_`, `hf_`, JWT) nem nomes de variáveis secretas; nenhum arquivo `frontend/.env*` está versionado.

**No `testes_api.py`** (job `testar`, com `pytest`, busca e provedores simulados):
- **T16:** `/api/saude` responde; `/api/config` não contém chaves, modelos nem prompt; `/api/perguntar` emite `fontes`, `texto` e `fim` nessa ordem; pergunta vazia dá 422, longa dá 413, a 11ª pergunta no mesmo minuto dá 429.

**No job `testar`**, antes do `testes.py`: `npm ci` e `npm run build` no `frontend/`. Se o build falhar, nada é publicado.

**No `avaliar.py`** (job `avaliar`): o **T14** continua, agora com a conversão de PDF instalada (`pymupdf4llm`). PDF sem texto para a indexação (RF31).

## 12. Pipeline de deploy

```
testar ──► avaliar ──► publicar ──► Railway (Wait for CI + health check)
```

Num **pull request**, só `testar` e `avaliar` rodam: o portão responde antes do merge e nada é publicado. `publicar` roda apenas em commits na `main`.

1. **testar:** Python 3.11 e Node 20; `npm ci && npm run build`; `pip install -r requirements.txt pytest`; `python testes.py` (T1 a T17, exceto T14); `pytest testes_api.py` (T16).
2. **avaliar:** como na parte 2, instalando também `pymupdf4llm`.
3. **publicar:** promove a coleção (`python indexar.py --promover`). O envio ao Hugging Face sai do workflow.
4. **Railway:** com **Wait for CI**, o Railway espera os jobs do commit passarem, monta a imagem pelo `Dockerfile` e só troca a versão no ar quando `/api/saude` responde 200 (até 300 segundos). Se o portão falhar, o deploy do commit é pulado.

**`railway.json`:**

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": { "builder": "DOCKERFILE", "dockerfilePath": "Dockerfile" },
  "deploy": { "healthcheckPath": "/api/saude", "healthcheckTimeout": 300,
              "restartPolicyType": "ON_FAILURE", "restartPolicyMaxRetries": 3 }
}
```

**`Dockerfile` (ideia):** estágio 1 com `node:20` roda `npm ci && npm run build`; estágio 2 com `python:3.11-slim` instala o `requirements.txt`, baixa o modelo de embedding durante o build, copia o código e o `frontend/dist`, e inicia com `uvicorn servidor:app --host 0.0.0.0 --port ${PORT:-8000}`. Os estágios rodam um depois do outro (o estágio Python copia o `dist` antes de instalar as dependências) e o modelo é só baixado no build (`lazy_load=True`), para poupar memória.

**Configuração manual antes do primeiro deploy:**
- **Railway:** criar a conta (entrando com o GitHub), **New Project → Deploy from GitHub repo**, escolher o repositório e a branch `main`. Em **Variables**, cadastrar as chaves. Em **Settings → Source**, ligar **Wait for CI**. Em **Settings → Networking**, **Generate Domain**.
- **GitHub:** `SUPABASE_URL` e `SUPABASE_SECRET_KEY` continuam. `HF_TOKEN` deixa de ser usado; não há segredo novo.
- **Hugging Face:** o Space pode ser pausado ou apagado depois que o Railway estiver no ar.

| Chave | Onde fica | Quem usa |
|---|---|---|
| `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, chave do provedor | Variables do Railway | servidor.py |
| `SUPABASE_URL`, `SUPABASE_SECRET_KEY` | Secrets do GitHub | avaliar e publicar |

## 13. Critérios de aceite

- [ ] **CA20:** `npm run dev` (front) com `uvicorn servidor:app --reload` (API) funciona localmente, com o Vite repassando `/api` para a porta 8000.
- [ ] **CA21:** `docker build` e `docker run -p 8000:8000 --env-file .env` sobem o serviço completo em `localhost:8000`.
- [ ] **CA22:** no Railway, `https://<servico>.up.railway.app` abre a interface com logo, nome e cores do `config.yml`.
- [ ] **CA23:** uma pergunta do material é respondida aos poucos, com cartões de fonte que mostram o trecho.
- [ ] **CA24:** "Qual a capital da Austrália?" recebe a frase de "não encontrei", sem cartões.
- [ ] **CA25:** a interface funciona num celular (ou na largura de 360 px do navegador) e nos dois temas.
- [ ] **CA26:** o código-fonte da página e os arquivos JavaScript não contêm chave nenhuma (T17 e conferência manual).
- [ ] **CA27:** um PDF com texto colocado em `documentos/`, com uma pergunta de teste sobre ele, passa no portão e passa a ser citado nas respostas.
- [ ] **CA28:** um PDF escaneado barra a indexação com a mensagem do RF31.
- [ ] **CA29:** 11 perguntas seguidas no mesmo minuto: a 11ª recebe o aviso de espera.
- [ ] **CA30:** as perguntas de teste impossíveis barram o deploy; o Railway pula o deploy e continua com a versão anterior.
- [ ] **CA31:** depois de um push válido, os três jobs ficam verdes, o Railway publica o commit e `/api/saude` mostra a `versao` nova.

## 14. Ordem sugerida de tarefas

1. **Chat sem Gradio:** extrair os provedores para `chat.py` e criar `servidor.py` com `/api/saude`, `/api/config` e `/api/perguntar` (RF16 a RF21). Testar com `curl`.
2. **Testes da API:** `testes_api.py` (T16).
3. **Front-end base:** projeto Vite + React + Tailwind em `frontend/`, consumindo `/api/config` e `/api/perguntar` com streaming (RF22 a RF24, RF27).
4. **Front-end completo:** cartões de fonte, estados, tema escuro, celular e acessibilidade (RF25, RF26, RF28, RF29).
5. **PDF:** leitura de PDF em `rag.py` e ajuste do T11 (RF30, RF31). Acrescentar um PDF de exemplo e uma pergunta de teste sobre ele.
6. **Portão:** T6 ajustado, T15, T17; build do front no `testar`.
7. **Contêiner:** `Dockerfile` e `.dockerignore` (CA21).
8. **Railway:** `railway.json`, criação do serviço, variáveis e Wait for CI (manual).
9. **Pipeline:** `publicar` só promove o índice; remover o envio ao Hugging Face e o `app.py`.
10. Commit, push e critérios de aceite CA22 a CA31.

## 15. Erros comuns e como resolver

| Sintoma | Causa | Solução |
|---|---|---|
| Build no Render para com `Out of memory (used over 512Mi)` | O Render limita o build à RAM do plano (R13) | Usar o Railway (build em máquina separada) ou um plano com mais memória |
| Railway publicou sem passar no portão | Wait for CI desligado (R15) | Ligar em Settings → Source |
| Deploy falha no health check | Serviço não subiu ou `/api/saude` responde 503 (Supabase) | Ver os Deploy Logs no Railway; conferir as variáveis do Supabase |
| Página abre, mas o chat dá erro de rede | Rota `/api` errada ou servidor sem o `frontend/dist` atualizado | Conferir o proxy do Vite (local) e o estágio de build do Dockerfile |
| Página em branco no Railway | `index.html` não encontrado ou caminho base do Vite errado | `base: "/"` no `vite.config.js`; conferir se o `dist` foi copiado na imagem |
| Chave aparece no JavaScript | Variável com prefixo `VITE_` (R16) | Remover do front, revogar a chave e manter o segredo só no servidor |
| `PDF sem texto extraível` | PDF escaneado (RF31) | Usar um PDF com texto ou converter com OCR fora do projeto |
| 429 em uso normal | Vários usuários atrás do mesmo IP (escola, empresa) | Aumentar `perguntas_por_minuto` no `config.yml` |
| Respostas sem cartões de fonte | Resposta era "não encontrei", ou o evento `fontes` não foi tratado no front | Conferir `nao_encontrado` no evento `fim` e o parser de SSE |

## 16. Próximos passos (fora do escopo)

- Domínio próprio no Railway (Custom Domain: CNAME no DNS e certificado automático).
- Conversas salvas e login, com aviso de LGPD.
- Envio de PDF pela interface, com área restrita.
- Reranker e avaliação automática das respostas (LLM como juiz).
