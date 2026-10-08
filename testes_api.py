"""
T16: testes da API, sem rede. A busca e os provedores de IA são simulados.
Rodar: pytest testes_api.py
"""
import json
import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("OPENROUTER_API_KEY", "chave-de-teste")

import chat  # noqa: E402
import rag  # noqa: E402
import servidor  # noqa: E402

TRECHOS = [{"fonte": "parte1-cicd-deploy.md", "secao": "08 GitHub Actions: a máquina descartável",
            "conteudo": "O runner é uma máquina descartável.", "similaridade": 0.9, "nota_rrf": 0.03}]


def provedor_falso(modelo, mensagens):
    if "Austrália" in mensagens[-1]["content"]:
        yield chat.BASE["mensagem_nao_encontrado"]
        return
    yield "O runner é "
    yield "descartável."


@pytest.fixture
def cliente(monkeypatch):
    def iniciar_falso():
        chat.base.banco, chat.base.modelo, chat.base.trechos, chat.base.erro = object(), object(), 136, None

    monkeypatch.setattr(chat.base, "iniciar", iniciar_falso)
    monkeypatch.setattr(rag, "buscar", lambda *a, **k: TRECHOS)
    monkeypatch.setitem(chat.PROVEDORES, "openrouter", provedor_falso)
    monkeypatch.setattr(servidor, "limite", servidor.LimitePorMinuto())  # contador zerado a cada teste
    with TestClient(servidor.app) as c:
        yield c


def eventos(resposta):
    """Lê o texto SSE e devolve a lista de (evento, dados)."""
    saida = []
    for bloco in resposta.text.strip().split("\n\n"):
        linhas = dict(linha.split(": ", 1) for linha in bloco.splitlines())
        saida.append((linhas["event"], json.loads(linhas["data"])))
    return saida


def test_saude(cliente):
    r = cliente.get("/api/saude")
    assert r.status_code == 200
    assert r.json()["status"] == "ok" and r.json()["trechos_na_producao"] == 136


def test_config_sem_segredos(cliente):
    texto = cliente.get("/api/config").text
    for proibido in ("prompt_sistema", "provedores", "modelo", "chave-de-teste", "API_KEY", chat.CONFIG["prompt_sistema"][:40]):
        assert proibido not in texto, f"/api/config expõe {proibido!r}"


def test_perguntar_ordem_dos_eventos(cliente):
    r = cliente.post("/api/perguntar", json={"mensagem": "O que é o runner?", "historico": []})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    ev = eventos(r)
    assert [e for e, _ in ev] == ["fontes", "texto", "texto", "fim"]
    assert ev[0][1][0]["fonte"] == "parte1-cicd-deploy.md" and ev[0][1][0]["trecho"]
    assert ev[-1][1] == {"nao_encontrado": False}


def test_nao_encontrado(cliente):
    ev = eventos(cliente.post("/api/perguntar", json={"mensagem": "Qual a capital da Austrália?"}))
    assert ev[-1] == ("fim", {"nao_encontrado": True})


def test_pergunta_vazia_422(cliente):
    assert cliente.post("/api/perguntar", json={"mensagem": ""}).status_code == 422


def test_pergunta_longa_413(cliente):
    tamanho = servidor.INTERFACE["limite_caracteres"] + 1
    assert cliente.post("/api/perguntar", json={"mensagem": "x" * tamanho}).status_code == 413


def test_limite_por_minuto_429(cliente):
    limite = servidor.INTERFACE["perguntas_por_minuto"]
    for _ in range(limite):
        assert cliente.post("/api/perguntar", json={"mensagem": "oi"}).status_code == 200
    r = cliente.post("/api/perguntar", json={"mensagem": "oi"})
    assert r.status_code == 429 and int(r.headers["Retry-After"]) > 0


def test_sem_chave_de_ia_vira_erro_amigavel(cliente, monkeypatch):
    for nome in chat.CHAVES.values():
        monkeypatch.delenv(nome, raising=False)
    ev = eventos(cliente.post("/api/perguntar", json={"mensagem": "oi"}))
    assert ev[0][0] == "erro" and "API_KEY" not in ev[0][1]["mensagem"]


def test_historico_limitado(cliente, monkeypatch):
    recebido = {}

    def provedor_espiao(modelo, mensagens):
        recebido["n"] = len(mensagens)
        yield "ok"

    monkeypatch.setitem(chat.PROVEDORES, "openrouter", provedor_espiao)
    historico = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"} for i in range(40)]
    cliente.post("/api/perguntar", json={"mensagem": "oi", "historico": historico})
    assert recebido["n"] == servidor.MAX_HISTORICO + 1  # 20 do histórico + a pergunta atual
