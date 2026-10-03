# Meu assistente de IA

Chat personalizado com base de conhecimento (RAG), interface própria e deploy automático no Render.

- **Personalização:** edite o `config.yml` (nome, cores, logo, prompt, interface).
- **Material de consulta:** arquivos `.md` e `.pdf` na pasta `documentos/`.
- **Deploy:** cada commit na `main` roda o portão (testes, build do front-end, avaliação da busca) e, se tudo passar, publica no Render pelo Deploy Hook. Um job final confere a versão no ar.
- **Chaves:** ficam no Environment do Render e nos Secrets do GitHub, nunca neste repositório.

## Como as peças se encaixam

| Peça | Arquivo | O que faz |
|---|---|---|
| Interface | `frontend/` (React + Vite + Tailwind) | A página do chat, compilada para `frontend/dist` |
| Servidor | `servidor.py` (FastAPI) | Rotas `/api/saude`, `/api/config`, `/api/perguntar` e o front-end |
| Respostas | `chat.py` | Provedores de IA com troca automática e RAG antes da chamada |
| Busca | `rag.py`, `indexar.py`, `avaliar.py` | Leitura de .md e .pdf, índice no Supabase, portão da busca |
| Portão | `testes.py`, `testes_api.py` | T1 a T17 |
| Produção | `Dockerfile`, `render.yaml`, `.github/workflows/deploy.yml` | Imagem, serviço no Render e pipeline |

## Rodar no computador

```bash
pip install -r requirements.txt
uvicorn servidor:app --reload --port 8000      # terminal 1: a API
cd frontend && npm install && npm run dev      # terminal 2: a página em http://localhost:5173
```

Material do Instituto NTA.
