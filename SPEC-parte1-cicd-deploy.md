# SPEC 1 — CI/CD e deploy inicial

> Documento de partida para construir o projeto do zero no formato spec-driven.
> Fluxo: ler a spec → gerar o plano de tarefas → implementar uma tarefa por vez → validar pelos critérios de aceite.
> Toda mudança de comportamento começa aqui, não no código.

---

## 1. Objetivo

Publicar na internet um chat com IA personalizado, que qualquer pessoa sem conhecimento de programação consiga adaptar editando **um único arquivo de configuração**. Cada alteração enviada ao GitHub deve ser testada e publicada automaticamente.

## 2. Público

- **Quem configura:** aluno ou profissional sem experiência com código. Edita o `config.yml` pelo lápis do GitHub.
- **Quem usa o chat:** o público final do assistente, definido no prompt de sistema.

## 3. Escopo

**Dentro:**
- Chat web com respostas em streaming e histórico durante a sessão.
- Personalização por arquivo: nome, descrição, cores, logo, modelo, limite de resposta, prompt de sistema e perguntas de exemplo.
- Portão de testes que bloqueia deploys com configuração inválida.
- Deploy automático no Hugging Face Spaces a cada commit na branch `main`.

**Fora (ver seção 13 — Próximas partes):**
- Base de conhecimento e RAG → parte 2.
- Front-end próprio em React, domínio próprio e hospedagem de produção → parte 3.
- Login de usuários e histórico salvo entre sessões.

## 4. Stack e restrições

| Item | Decisão | Motivo |
|---|---|---|
| Linguagem | Python 3.11 | Simples para alunos |
| Interface | Gradio 6 (`gr.ChatInterface`) | Chat pronto, roda nativo no Hugging Face |
| Modelo | OpenRouter (SDK `openai` com `base_url=https://openrouter.ai/api/v1`) | Uma chave dá acesso a modelos de vários fornecedores; sem GPU própria |
| Hospedagem | Hugging Face Spaces | Grátis, sem cartão |
| CI/CD | GitHub Actions | Testa e publica a cada commit |

**Restrições conhecidas (aprendidas na prática):**
- R1. A chave da API **nunca** entra no repositório. Ela vem da variável de ambiente `OPENROUTER_API_KEY`, cadastrada nos secrets do Space.
- R2. O Hugging Face recusa `.png`/`.jpg` versionados no repositório do Space. A logo precisa ser `.svg` ou um link `https`.
- R3. A versão do Gradio em `README.md` (`sdk_version`) precisa ser **a mesma** usada localmente. O Gradio 5 e o 6 têm APIs diferentes (`theme`/`css` ficam em `launch()` no 6).
- R4. Sem plano PRO, um Space em ZeroGPU não volta para CPU basic. Nesse hardware, o app precisa ter ao menos uma função com `@spaces.GPU`. O pacote `spaces` não existe localmente, então é preciso um decorador vazio como alternativa.
- R5. O Hugging Face espera o app em `0.0.0.0:7860`. A porta deve poder ser trocada pela variável `PORT` para rodar duas cópias localmente.

## 5. Arquivos do projeto

```
config.yml                  # única coisa que o aluno edita
app.py                      # lê o config e monta o chat; quase nunca muda
testes.py                   # portão do deploy
requirements.txt            # openai, pyyaml
logo.svg                    # logo padrão
README.md                   # cabeçalho YAML exigido pelo Hugging Face
.gitignore                  # __pycache__/, *.pyc, .env
.github/workflows/deploy.yml
```

## 6. Contrato do `config.yml`

| Campo | Obrigatório | Tipo / valores | Padrão |
|---|---|---|---|
| `nome` | sim | texto | — |
| `descricao` | sim | texto | — |
| `tema` | sim | uma cor (`azul`) ou duas (`azul e vermelho`) entre: `azul`, `verde`, `vermelho`, `laranja`, `roxo`, `grafite` | — |
| `logo` | não | caminho `.svg` no repositório ou link `https` | sem logo |
| `logo_altura` | não | inteiro em pixels | 56 |
| `modelo` | sim | ID de modelo do OpenRouter, no formato `fornecedor/modelo` (ex.: `google/gemma-4-31b-it:free`; gratuitos terminam em `:free`) | — |
| `modelos_reserva` | não | lista de IDs do OpenRouter tentados em ordem se o `modelo` estiver lotado (só modelos de conversa; evite `openrouter/free`, que pode cair num modelo de moderação) | nenhum |
| `max_tokens` | não | inteiro | 800 |
| `prompt_sistema` | sim | texto com pelo menos 80 caracteres: quem é, para quem fala, o que não faz | — |
| `exemplos` | não | lista de perguntas curtas | nenhum |

Todo campo novo deve entrar nesta tabela **antes** de ir para o código, com um comentário explicativo no próprio `config.yml`.

## 7. Requisitos funcionais

- **RF1 — Cabeçalho:** exibe logo, nome e descrição do `config.yml`. A logo respeita `logo_altura`, com largura proporcional, qualquer que seja o tamanho original do SVG.
- **RF2 — Chat:** envia a conversa inteira a cada pergunta (o modelo não guarda memória) e mostra a resposta em streaming.
- **RF3 — Exemplos:** as perguntas de `exemplos` aparecem como cartões clicáveis.
- **RF4 — Tema:** a primeira cor é a principal e a segunda, se existir, é a secundária. O fundo da página é um degradê entre elas, e o chat fica num cartão legível por cima.
- **RF5 — Sem chave:** se `OPENROUTER_API_KEY` não existir, o chat responde com uma mensagem explicando onde cadastrá-la, em vez de quebrar.
- **RF6 — Idioma:** os textos da interface (placeholder, rótulos) ficam em português.

## 8. Portão de testes (`testes.py`)

O deploy **não acontece** se qualquer item falhar. Cada erro deve dizer o que corrigir.

- **T1:** `config.yml` existe e é YAML válido.
- **T2:** os campos obrigatórios estão preenchidos.
- **T3:** o `tema` usa uma ou duas cores permitidas, no formato `cor` ou `cor e cor`.
- **T4:** o `prompt_sistema` tem pelo menos 80 caracteres.
- **T5:** a logo local existe e é `.svg`. Links `https` são aceitos sem checagem.
- **T6:** o `app.py` tem sintaxe Python válida.
- **T7:** nenhum arquivo contém algo com cara de chave (`sk-or-...`, `sk-ant-...`, `hf_...`).

## 9. Pipeline de deploy

1. **Gatilho:** push na `main` ou o botão "Run workflow".
2. **Job `testar`:** instala o `pyyaml` e roda `python testes.py`.
3. **Job `publicar`:** só roda se `testar` passar (`needs: testar`). Faz o checkout com `fetch-depth: 0` e dá `git push --force` para `huggingface.co/spaces/<HF_USUARIO>/<HF_SPACE>`, usando o secret `HF_TOKEN`.
4. **Configuração obrigatória antes do primeiro deploy:**
   - Em `deploy.yml`: `HF_USUARIO` e `HF_SPACE` com os valores reais (o nome exato do Space).
   - No GitHub: secret `HF_TOKEN`, um token do Hugging Face com permissão de escrita.
   - No Space: secret `OPENROUTER_API_KEY`.

## 10. Critérios de aceite

- [ ] **CA1:** `python testes.py` imprime "Liberado para publicar" com o config padrão.
- [ ] **CA2:** trocar `tema` para `rosa` faz o portão barrar, com mensagem clara.
- [ ] **CA3:** `python app.py` abre em `localhost:7860`, e `PORT=7861 python app.py` abre em outra porta.
- [ ] **CA4:** uma logo SVG de 588×380 aparece com a altura de `logo_altura`.
- [ ] **CA5:** sem `OPENROUTER_API_KEY`, o chat mostra a mensagem de RF5.
- [ ] **CA6:** com a chave, uma pergunta de exemplo recebe resposta em streaming e dentro do assunto do prompt.
- [ ] **CA7:** um commit na `main` alterando só o `config.yml` termina com o Space em `RUNNING` e a mudança visível.
- [ ] **CA8:** um commit com config inválido falha no job `testar`, e a versão anterior continua no ar.

## 11. Ordem sugerida de tarefas

1. Criar o `config.yml` com o contrato da seção 6 e comentários para leigos.
2. Criar o `app.py` mínimo: ler o config e montar o `ChatInterface` com streaming (RF2, RF5).
3. Adicionar cabeçalho, logo, tema e CSS (RF1, RF3, RF4, RF6).
4. Adicionar a compatibilidade com ZeroGPU (R4).
5. Escrever o `testes.py` (T1 a T7) e validar CA1 e CA2.
6. Criar o `README.md` com o cabeçalho do Space (R3), o `requirements.txt` e o `.gitignore`.
7. Criar o `deploy.yml` (seção 9).
8. Criar o Space, cadastrar os secrets e fazer o primeiro commit e push.
9. Rodar os critérios de aceite CA3 a CA8.

## 12. Erros comuns e como resolver

| Sintoma | Causa | Solução |
|---|---|---|
| `src refspec main does not match any` | Repositório sem nenhum commit | `git add .` e `git commit` antes do `push` |
| `Cannot find empty port 7860` | Outra cópia do app ainda rodando | `Ctrl+C` na outra cópia ou `PORT=7861` |
| `Authentication failed` no job publicar | Secret `HF_TOKEN` ausente | Cadastrar em Settings → Secrets and variables → Actions |
| `Repository not found` no job publicar | `HF_USUARIO`/`HF_SPACE` errados ou editados só localmente | Corrigir o `deploy.yml` e fazer commit e push |
| Portão barra o `tema` | Cor fora da lista ou formato errado | Usar `azul` ou `azul e vermelho` |
| Space não sobe no ZeroGPU | Nenhuma função com `@spaces.GPU` | Ver R4 |

## 13. Próximas partes (fora do escopo desta spec)

Esta seção só registra a direção do projeto. **Não implemente nada daqui na parte 1.** Cada parte terá a sua própria spec, que parte desta.

**Parte 2 — Base de conhecimento e RAG** (`SPEC-parte2-rag.md`)
- O assistente responde com base em documentos do curso, não só no conhecimento geral do modelo.
- Ficam para a spec da parte 2: formato dos documentos, divisão em trechos, embeddings, onde guardar os vetores, como citar as fontes e como avaliar a qualidade das respostas.

**Parte 3 — Front-end em React e produção** (`SPEC-parte3-frontend.md`)
- O Gradio é substituído por um back-end com API e um front-end próprio em React.
- A hospedagem sai do Hugging Face para uma plataforma de aplicação (ex.: Render), com domínio próprio.
- Ficam para a spec da parte 3: formato da API, streaming no front, design, domínio, variáveis de ambiente e custos.

**Decisões da parte 1 que preparam as próximas:**
- D1. A chamada ao modelo fica isolada numa função (`responder`). Na parte 2, o RAG entra antes dessa chamada, sem reescrever a interface.
- D2. Chaves e configuração ficam fora do código (variáveis de ambiente e `config.yml`), para o back-end da parte 3 reaproveitar o mesmo padrão.
- D3. O portão de testes e o GitHub Actions são o modelo de deploy das próximas partes. Muda o destino, não o fluxo.
