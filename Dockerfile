# Imagem do assistente (Parte 3): um único serviço com a API (FastAPI) e o front-end (React) já compilado.

# ---------- Estágio 1: compila o front-end. Só a pasta dist/ segue para a imagem final.
FROM node:20-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------- Estágio 2: o servidor Python
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FASTEMBED_CACHE_PATH=/app/modelos

COPY requirements.txt ./
RUN pip install -r requirements.txt

# Baixa o modelo de embedding durante o build: o servidor sobe sem depender do Hugging Face
COPY config.yml rag.py ./
RUN python -c "import rag; rag.carregar_modelo(rag.carregar_config())"

COPY . .
COPY --from=frontend /frontend/dist ./frontend/dist

# Roda sem ser root
RUN useradd --create-home assistente && chown -R assistente /app
USER assistente

# O Render informa a porta na variável PORT
CMD ["sh", "-c", "uvicorn servidor:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
