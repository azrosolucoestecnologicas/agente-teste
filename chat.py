"""
Provedores de IA e geração da resposta (RF16). Usado pelo servidor.py.
O comportamento é o mesmo do app.py das Partes 1 e 2: provedores na ordem do config.yml,
troca automática quando um falha, e RAG antes da chamada ao modelo.
"""
import logging
import os
from pathlib import Path

import anthropic
import openai
import yaml

import rag

log = logging.getLogger("assistente")

CONFIG = yaml.safe_load(Path("config.yml").read_text(encoding="utf-8"))

# As chaves NÃO ficam no código: vêm das variáveis de ambiente do servidor (Variables do Railway).
CHAVES = {
    "openrouter": "OPENROUTER_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
}
MAX_TOKENS = int(CONFIG.get("max_tokens", 800))
BASE = rag.carregar_config()


class BaseConhecimento:
    """Conexão com o Supabase e modelo de embedding, carregados uma vez ao iniciar (RF18)."""

    def __init__(self):
        self.banco = None
        self.modelo = None
        self.erro = None       # mensagem para o usuário quando a base não está pronta
        self.trechos = None    # quantos trechos há na produção (para o /api/saude)

    @property
    def pronta(self) -> bool:
        return not BASE["ativa"] or (self.banco is not None and self.modelo is not None)

    def iniciar(self):
        if not BASE["ativa"]:
            return
        try:
            self.banco = rag.cliente_supabase("SUPABASE_PUBLISHABLE_KEY")
            self.modelo = rag.carregar_modelo(BASE)
            self.trechos = (self.banco.table("trechos").select("id", count="exact", head=True)
                            .eq("colecao", "producao").execute().count)
            log.info("Base de conhecimento: modelo %s carregado; %s trechos na produção",
                     BASE["modelo_embedding"], self.trechos)
        except RuntimeError as e:
            self.erro = "A base de conhecimento não está configurada no servidor."
            log.error("Base de conhecimento: %s. Cadastre SUPABASE_URL e SUPABASE_PUBLISHABLE_KEY.", e)
        except Exception as e:
            # Sem banco ou sem modelo, o chat avisa. Se só a contagem falhou, a busca tenta a cada pergunta.
            if self.banco is None or self.modelo is None:
                self.erro = "A base de conhecimento está indisponível no momento."
            log.error("Base de conhecimento: aviso ao iniciar: %s", e)


base = BaseConhecimento()


# ------------------------------------------------------------ provedores

def via_openrouter(modelo, mensagens):
    """OpenRouter: usa o formato da OpenAI, só muda o endereço."""
    cliente = openai.OpenAI(base_url="https://openrouter.ai/api/v1",
                            api_key=os.environ[CHAVES["openrouter"]])
    fluxo = cliente.chat.completions.create(
        model=modelo,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "system", "content": CONFIG["prompt_sistema"]}, *mensagens],
        stream=True,
        # Desliga o "raciocínio" (que gasta o max_tokens) e usa a lista de reserva do OpenRouter.
        extra_body={
            "reasoning": {"enabled": False},
            "models": [modelo, *(CONFIG.get("modelos_reserva") or [])],
        },
    )
    for pedaco in fluxo:
        if pedaco.choices and pedaco.choices[0].delta.content:
            yield pedaco.choices[0].delta.content


def via_openai(modelo, mensagens):
    """OpenAI direto. Os modelos GPT-5 usam max_completion_tokens e raciocinam antes de responder."""
    cliente = openai.OpenAI(api_key=os.environ[CHAVES["openai"]])
    fluxo = cliente.chat.completions.create(
        model=modelo,
        max_completion_tokens=MAX_TOKENS,
        reasoning_effort="low",
        messages=[{"role": "system", "content": CONFIG["prompt_sistema"]}, *mensagens],
        stream=True,
    )
    for pedaco in fluxo:
        if pedaco.choices and pedaco.choices[0].delta.content:
            yield pedaco.choices[0].delta.content


def via_anthropic(modelo, mensagens):
    """Anthropic direto, com o SDK oficial. O prompt de sistema vai em um campo separado."""
    cliente = anthropic.Anthropic(api_key=os.environ[CHAVES["anthropic"]])
    with cliente.messages.stream(
        model=modelo,
        max_tokens=MAX_TOKENS,
        system=CONFIG["prompt_sistema"],
        messages=mensagens,
    ) as fluxo:
        yield from fluxo.text_stream


PROVEDORES = {"openrouter": via_openrouter, "openai": via_openai, "anthropic": via_anthropic}


def provedores_ativos():
    """Os provedores do config.yml que têm chave cadastrada, na ordem do arquivo."""
    return [(nome, modelo) for nome, modelo in (CONFIG.get("provedores") or {}).items()
            if nome in CHAVES and os.environ.get(CHAVES[nome])]


# ------------------------------------------------------------ geração da resposta (RF17)

def gerar_eventos(mensagem: str, historico: list[dict]):
    """Gera os eventos da resposta, na ordem: fontes, texto (vários), e fim ou erro.
    Cada evento é uma tupla (nome, dados). As mensagens de erro são para o usuário;
    o detalhe técnico vai só para o log (RF21)."""
    ativos = provedores_ativos()
    if not ativos:
        log.error("Nenhuma chave de provedor cadastrada (%s)", ", ".join(CHAVES.values()))
        yield "erro", {"mensagem": "O assistente ainda não foi configurado com uma chave de IA."}
        return

    trechos = []
    if BASE["ativa"]:
        if base.erro or not base.pronta:
            yield "erro", {"mensagem": base.erro or "A base de conhecimento ainda está carregando. Tente em instantes."}
            return
        try:
            trechos = rag.buscar(base.banco, base.modelo, mensagem, BASE)
        except Exception as e:
            log.error("Busca falhou: %s", e)
            yield "erro", {"mensagem": "Não consegui consultar a base de conhecimento agora. Tente de novo."}
            return

    yield "fontes", [{"n": n, "fonte": t["fonte"], "secao": t["secao"], "trecho": t["conteudo"]}
                     for n, t in enumerate(trechos, start=1)]

    # O modelo não lembra de nada sozinho: a conversa inteira vai a cada pergunta.
    # Só a pergunta atual leva os trechos.
    mensagens = [{"role": m["role"], "content": m["content"]} for m in historico if m.get("content")]
    conteudo = rag.montar_mensagem(mensagem, trechos, BASE) if BASE["ativa"] else mensagem
    mensagens.append({"role": "user", "content": conteudo})

    for nome, modelo in ativos:
        texto = ""
        try:
            for pedaco in PROVEDORES[nome](modelo, mensagens):
                texto += pedaco
                yield "texto", {"delta": pedaco}
            nao_encontrado = bool(BASE["ativa"] and BASE["mensagem_nao_encontrado"] in texto)
            yield "fim", {"nao_encontrado": nao_encontrado}
            return
        except (openai.APIError, anthropic.APIError) as e:
            log.warning("Provedor %s (%s) falhou: %s", nome, modelo, getattr(e, "message", e))
            if texto:  # caiu no meio da resposta: o que veio fica, e avisamos
                yield "erro", {"mensagem": "A resposta foi interrompida. Tente perguntar de novo."}
                return

    yield "erro", {"mensagem": "O serviço de IA está ocupado ou indisponível agora. Tente de novo em instantes."}
