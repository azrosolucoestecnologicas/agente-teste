"""
Servidor do assistente (Parte 3): a API em /api e o front-end compilado em /.
Rodar localmente:  uvicorn servidor:app --reload --port 8000
"""
import json
import logging
import os
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field

import chat

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("assistente")

CONFIG = chat.CONFIG
DIST = Path("frontend/dist")

# Bloco interface do config.yml (seção 7 da spec), com os padrões
INTERFACE = {
    "tema_inicial": "sistema",
    "rodape": "Respostas geradas por IA com base no material de consulta.",
    "limite_caracteres": 2000,
    "perguntas_por_minuto": 10,
    "mascote": True,
    **(CONFIG.get("interface") or {}),
}
MAX_HISTORICO = 20

# Os nomes de tema do config.yml traduzidos para escalas de cor (mesmos tons do Tailwind)
PALETAS = {
    "azul":     {"50": "#eff6ff", "100": "#dbeafe", "500": "#3b82f6", "600": "#2563eb", "700": "#1d4ed8", "900": "#1e3a8a"},
    "verde":    {"50": "#f0fdf4", "100": "#dcfce7", "500": "#22c55e", "600": "#16a34a", "700": "#15803d", "900": "#14532d"},
    "vermelho": {"50": "#fef2f2", "100": "#fee2e2", "500": "#ef4444", "600": "#dc2626", "700": "#b91c1c", "900": "#7f1d1d"},
    "laranja":  {"50": "#fff7ed", "100": "#ffedd5", "500": "#f97316", "600": "#ea580c", "700": "#c2410c", "900": "#7c2d12"},
    "roxo":     {"50": "#faf5ff", "100": "#f3e8ff", "500": "#a855f7", "600": "#9333ea", "700": "#7e22ce", "900": "#581c87"},
    "grafite":  {"50": "#f8fafc", "100": "#f1f5f9", "500": "#64748b", "600": "#475569", "700": "#334155", "900": "#0f172a"},
}


def cores_do_tema():
    nomes = [c.strip() for c in str(CONFIG.get("tema", "azul")).split(" e ")]
    principal = PALETAS.get(nomes[0], PALETAS["azul"])
    return {"principal": principal, "secundaria": PALETAS.get(nomes[-1], principal)}


@asynccontextmanager
async def ciclo_de_vida(_app):
    chat.base.iniciar()  # carrega o modelo de embedding e conecta ao Supabase uma vez (RF18)
    yield


app = FastAPI(title=CONFIG.get("nome", "Assistente"), lifespan=ciclo_de_vida, docs_url=None, redoc_url=None)


# ------------------------------------------------------------ limites de uso (RF19)

class LimitePorMinuto:
    """Conta as perguntas de cada visitante numa janela de 60 segundos, em memória."""

    def __init__(self):
        self.pedidos = defaultdict(deque)
        self.trava = threading.Lock()

    def segundos_de_espera(self, visitante: str, limite: int) -> int:
        """0 se pode perguntar agora; senão, quantos segundos esperar."""
        agora = time.monotonic()
        with self.trava:
            fila = self.pedidos[visitante]
            while fila and agora - fila[0] >= 60:
                fila.popleft()
            if len(fila) >= limite:
                return max(1, int(60 - (agora - fila[0])) + 1)
            fila.append(agora)
            return 0


limite = LimitePorMinuto()


def ip_do_visitante(request: Request) -> str:
    """Atrás do proxy do Railway, o IP real do visitante vem no cabeçalho X-Forwarded-For (o primeiro valor)."""
    encaminhado = request.headers.get("x-forwarded-for", "")
    return encaminhado.split(",")[0].strip() or (request.client.host if request.client else "desconhecido")


# ------------------------------------------------------------ rotas da API (seção 8)

class Mensagem(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class Pergunta(BaseModel):
    mensagem: str = Field(min_length=1)
    historico: list[Mensagem] = []


@app.get("/api/saude")
def saude():
    base = chat.base
    # O Railway informa o commit publicado em RAILWAY_GIT_COMMIT_SHA; localmente, "dev"
    corpo = {"versao": os.environ.get("RAILWAY_GIT_COMMIT_SHA", "dev"), "trechos_na_producao": base.trechos}
    if not base.pronta:
        return JSONResponse({"status": "indisponivel", **corpo}, status_code=503)
    return {"status": "ok", **corpo}


@app.get("/api/config")
def config_publica():
    """Só o que a interface precisa. Nunca chaves, modelos, provedores ou prompt."""
    return {
        "nome": CONFIG.get("nome", "Assistente"),
        "descricao": CONFIG.get("descricao", ""),
        "exemplos": CONFIG.get("exemplos") or [],
        "logo_url": "/api/logo" if CONFIG.get("logo") else None,
        "logo_altura": int(CONFIG.get("logo_altura", 56)),
        "cores": cores_do_tema(),
        "interface": INTERFACE,
    }


@app.get("/api/logo")
def logo():
    caminho = str(CONFIG.get("logo", "")).strip()
    if caminho.startswith("https://"):
        return RedirectResponse(caminho)
    arquivo = Path(caminho)
    if not caminho or not arquivo.is_file():
        raise HTTPException(404, "logo não encontrada")
    return FileResponse(arquivo, media_type="image/svg+xml" if arquivo.suffix == ".svg" else None)


def em_sse(eventos):
    """Converte os eventos do chat.py para o formato Server-Sent Events."""
    inicio, tamanho = time.monotonic(), 0
    for nome, dados in eventos:
        if nome == "texto":
            tamanho += len(dados["delta"])
        yield f"event: {nome}\ndata: {json.dumps(dados, ensure_ascii=False)}\n\n"
    # Log sem o texto da pergunta nem da resposta: só tamanho e tempo (seção 10)
    log.info("resposta: %d caracteres em %.1fs", tamanho, time.monotonic() - inicio)


@app.post("/api/perguntar")
def perguntar(dados: Pergunta, request: Request):
    if len(dados.mensagem) > int(INTERFACE["limite_caracteres"]):
        raise HTTPException(413, f"A pergunta passa de {INTERFACE['limite_caracteres']} caracteres.")
    espera = limite.segundos_de_espera(ip_do_visitante(request), int(INTERFACE["perguntas_por_minuto"]))
    if espera:
        return JSONResponse({"detail": f"Muitas perguntas seguidas. Tente de novo em {espera} segundos."},
                            status_code=429, headers={"Retry-After": str(espera)})
    historico = [m.model_dump() for m in dados.historico][-MAX_HISTORICO:]
    return StreamingResponse(em_sse(chat.gerar_eventos(dados.mensagem.strip(), historico)),
                             media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ------------------------------------------------------------ front-end compilado (RF20)

@app.get("/{caminho:path}", include_in_schema=False)
def front_end(caminho: str):
    if caminho.startswith("api/"):
        raise HTTPException(404)
    arquivo = (DIST / caminho).resolve()
    if caminho and arquivo.is_file() and DIST.resolve() in arquivo.parents:
        return FileResponse(arquivo)
    indice = DIST / "index.html"
    if indice.is_file():
        return FileResponse(indice)
    return HTMLResponse("<h1>Front-end não compilado</h1><p>Rode <code>npm run build</code> em frontend/.</p>",
                        status_code=503)
