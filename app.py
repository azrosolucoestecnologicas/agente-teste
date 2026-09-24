"""
Assistente de IA personalizado.
Toda a personalização fica no config.yml; este arquivo quase nunca precisa mudar.
"""
import os
from pathlib import Path

import anthropic
import gradio as gr
import openai
import yaml

# O Space roda em hardware ZeroGPU, que exige pelo menos uma função com @spaces.GPU.
# O pacote "spaces" já vem instalado no Hugging Face; no computador local ele não existe,
# então usamos um decorador vazio para o app rodar igual nos dois lugares.
try:
    import spaces
except ImportError:
    class spaces:  # noqa: N801
        @staticmethod
        def GPU(fn=None, **_):
            return fn if fn else (lambda f: f)

CONFIG = yaml.safe_load(Path("config.yml").read_text(encoding="utf-8"))

# Nomes de tema do config.yml traduzidos para as paletas do Gradio
PALETAS = {
    "azul": gr.themes.colors.blue,
    "verde": gr.themes.colors.green,
    "vermelho": gr.themes.colors.red,
    "laranja": gr.themes.colors.orange,
    "roxo": gr.themes.colors.purple,
    "grafite": gr.themes.colors.slate,
}

# As chaves NÃO ficam no código. O Hugging Face injeta como variáveis de ambiente,
# a partir do que você cadastrou em Settings > Variables and secrets.
# Cada provedor do config.yml usa a sua própria chave.
CHAVES = {
    "openrouter": "OPENROUTER_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
}
MAX_TOKENS = int(CONFIG.get("max_tokens", 800))


def logo_html() -> str:
    """Monta o HTML da logo: SVG embutido ou imagem por link."""
    logo = str(CONFIG.get("logo", "")).strip()
    if logo.startswith("http"):
        return f'<img src="{logo}" style="object-fit:contain">'
    if logo and Path(logo).exists():
        return Path(logo).read_text(encoding="utf-8")
    return ""


@spaces.GPU(duration=1)
def gpu_minima():
    """Função mínima só para o ZeroGPU aceitar o Space. Nunca é chamada:
    as respostas vêm da API do OpenRouter e não usam GPU."""
    return None


def via_openrouter(modelo, mensagens):
    """OpenRouter: usa o formato da OpenAI, só muda o endereço."""
    cliente = openai.OpenAI(base_url="https://openrouter.ai/api/v1",
                            api_key=os.environ[CHAVES["openrouter"]])
    fluxo = cliente.chat.completions.create(
        model=modelo,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "system", "content": CONFIG["prompt_sistema"]}, *mensagens],
        stream=True,
        # Alguns modelos "pensam" antes de responder e gastam o max_tokens nisso.
        # Desligamos o raciocínio para a resposta vir direto; quem não tem, ignora.
        # "models" é a lista de reserva do OpenRouter: se um estiver lotado, tenta o próximo.
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
        reasoning_effort="low",  # pouco raciocínio, para sobrar espaço para a resposta
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


def responder(mensagem, historico):
    """Recebe a pergunta e o histórico da sessão e devolve a resposta aos poucos."""
    # Só entram os provedores do config.yml que têm chave cadastrada, na ordem do arquivo.
    ativos = [(nome, modelo) for nome, modelo in (CONFIG.get("provedores") or {}).items()
              if os.environ.get(CHAVES[nome])]
    if not ativos:
        yield ("Nenhuma chave de API foi configurada. No Space, abra Settings, "
               "Variables and secrets, e cadastre pelo menos uma destas: "
               + ", ".join(CHAVES[n] for n in CONFIG.get("provedores") or CHAVES) + ".")
        return

    # O modelo não lembra de nada sozinho: reenviamos a conversa inteira a cada pergunta.
    # No Gradio 6 o "content" chega como lista de partes ({"type": "text", "text": ...}).
    mensagens = []
    for m in historico:
        conteudo = m.get("content")
        if isinstance(conteudo, list):
            conteudo = "".join(p.get("text", "") for p in conteudo if isinstance(p, dict))
        if isinstance(conteudo, str) and conteudo:
            mensagens.append({"role": m["role"], "content": conteudo})
    mensagens.append({"role": "user", "content": mensagem})

    # Tenta cada provedor na ordem. Se um falhar antes de responder, passa para o próximo.
    falhas = []
    for nome, modelo in ativos:
        texto = ""
        try:
            for pedaco in PROVEDORES[nome](modelo, mensagens):
                texto += pedaco
                yield texto
            return
        except (openai.APIError, anthropic.APIError) as e:
            if texto:  # caiu no meio da resposta: mostra o que veio e avisa
                yield f"{texto}\n\n⚠️ A resposta foi interrompida ({nome}): {e.message}"
                return
            falhas.append(f"- {nome} ({modelo}): {e.message}")

    yield "⚠️ Nenhum provedor conseguiu responder agora:\n" + "\n".join(falhas)


# "azul" usa uma cor; "azul e vermelho" usa a primeira como principal e a segunda como secundária
cores = [c.strip() for c in str(CONFIG.get("tema", "azul")).split(" e ")]
principal = PALETAS.get(cores[0], gr.themes.colors.blue)
secundaria = PALETAS.get(cores[-1], principal)
tema = gr.themes.Soft(primary_hue=principal, secondary_hue=secundaria)

# Visual: fundo em degradê com as cores do tema, cabeçalho branco e o chat num cartão
ALTURA_LOGO = int(CONFIG.get("logo_altura", 56))
CSS = f"""
body, .gradio-container {{
  background: linear-gradient(135deg, {principal.c900} 0%, {principal.c700} 45%, {secundaria.c700} 100%) !important;
  background-attachment: fixed !important;
}}
.cabecalho {{ display:flex; align-items:center; gap:16px; padding:12px 4px 20px; color:#fff; }}
.cabecalho h1 {{ margin:0; color:#fff; font-size:1.8rem; }}
.cabecalho p {{ margin:4px 0 0; color:#fff; opacity:.85; }}
.logo svg, .logo img {{ height:{ALTURA_LOGO}px !important; width:auto !important; display:block;
  border-radius:10px; box-shadow:0 4px 14px rgba(0,0,0,.35); }}
.cartao {{ background: var(--background-fill-primary); border-radius:16px; padding:16px;
  box-shadow:0 10px 30px rgba(0,0,0,.30); }}
.cartao .example {{ border:1px solid {principal.c200}; border-left:4px solid {secundaria.c600};
  border-radius:12px; padding:12px 14px; background: var(--background-fill-secondary); }}
.cartao .example:hover {{ border-color:{secundaria.c400}; box-shadow:0 4px 12px rgba(0,0,0,.12); }}
"""

with gr.Blocks(title=CONFIG["nome"]) as demo:
    gr.HTML(
        f"""
        <div class="cabecalho">
          <div class="logo">{logo_html()}</div>
          <div>
            <h1>{CONFIG["nome"]}</h1>
            <p>{CONFIG["descricao"]}</p>
          </div>
        </div>
        """
    )
    with gr.Column(elem_classes="cartao"):
        gr.ChatInterface(
            fn=responder,
            examples=CONFIG.get("exemplos") or None,
            cache_examples=False,
            chatbot=gr.Chatbot(show_label=False, height=480),
            textbox=gr.Textbox(placeholder="Digite sua pergunta...", show_label=False, submit_btn=True),
        )

if __name__ == "__main__":
    # 0.0.0.0 e a porta 7860 são o que o Hugging Face espera
    demo.launch(
        theme=tema,
        css=CSS,
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
    )
