"""
Base de conhecimento (RAG): funções usadas por indexar.py, avaliar.py e app.py.
Tudo que é ajustável fica no bloco base_conhecimento do config.yml.
"""
import os
import re
from pathlib import Path

import yaml

# Valores usados quando o campo não existe no config.yml (contrato da seção 6 da spec)
PADROES = {
    "ativa": True,
    "pasta": "documentos",
    "modelo_embedding": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "tamanho_trecho": 1200,
    "sobreposicao": 150,
    "trechos_por_resposta": 4,
    "peso_palavras": 1,
    "peso_sentido": 1,
    "mensagem_nao_encontrado": "Não encontrei isso no material do curso.",
}


def carregar_config(caminho="config.yml") -> dict:
    """Lê o bloco base_conhecimento do config.yml e completa com os padrões."""
    config = yaml.safe_load(Path(caminho).read_text(encoding="utf-8")) or {}
    return {**PADROES, **(config.get("base_conhecimento") or {})}


# ------------------------------------------------------------ divisão em trechos (RF7)

def dividir_em_secoes(texto: str) -> list[tuple[str, str]]:
    """Divide um Markdown pelos títulos (#, ## e ###), ignorando o que está dentro de blocos de código.
    A seção de cada pedaço é o título de nível 2 e, se houver, o de nível 3: "09 Segredos › Chaves"."""
    secoes, linhas = [], []
    titulos = {1: "", 2: "", 3: ""}
    em_codigo = False

    def fechar():
        conteudo = "\n".join(linhas).strip()
        nome = " › ".join(t for t in (titulos[2], titulos[3]) if t) or titulos[1]
        if conteudo:
            secoes.append((nome, conteudo))
        linhas.clear()

    for linha in texto.splitlines():
        if linha.strip().startswith("```"):
            em_codigo = not em_codigo
        titulo = None if em_codigo else re.match(r"^(#{1,3})\s+(.+)$", linha)
        if titulo:
            fechar()
            nivel = len(titulo.group(1))
            titulos[nivel] = titulo.group(2).strip()
            for abaixo in range(nivel + 1, 4):  # um título novo zera os de nível abaixo
                titulos[abaixo] = ""
        else:
            linhas.append(linha)
    fechar()
    return secoes


def subdividir(texto: str, tamanho: int, sobreposicao: int) -> list[str]:
    """Corta um texto longo em pedaços de até `tamanho` caracteres, de preferência entre parágrafos.
    Cada pedaço começa repetindo o fim do anterior (a sobreposição)."""
    if len(texto) <= tamanho:
        return [texto]

    # Parágrafos maiores que o tamanho são cortados no último espaço antes do limite
    blocos = []
    for paragrafo in re.split(r"\n\s*\n", texto):
        paragrafo = paragrafo.strip()
        while len(paragrafo) > tamanho - sobreposicao:
            corte = paragrafo.rfind(" ", 0, tamanho - sobreposicao)
            corte = corte if corte > 0 else tamanho - sobreposicao
            blocos.append(paragrafo[:corte].strip())
            paragrafo = paragrafo[corte:].strip()
        if paragrafo:
            blocos.append(paragrafo)

    pedacos, atual = [], ""
    for bloco in blocos:
        candidato = f"{atual}\n\n{bloco}" if atual else bloco
        if len(candidato) <= tamanho:
            atual = candidato
            continue
        pedacos.append(atual)
        cauda = atual[-sobreposicao:] if sobreposicao else ""
        if " " in cauda:  # começa a sobreposição numa palavra inteira
            cauda = cauda[cauda.index(" ") + 1:]
        atual = f"{cauda}\n\n{bloco}" if cauda else bloco
        if len(atual) > tamanho:
            atual = bloco
    if atual:
        pedacos.append(atual)
    return pedacos


def dividir_em_trechos(cfg: dict) -> tuple[int, list[dict]]:
    """Lê todos os .md da pasta e devolve (quantidade de documentos, lista de trechos)."""
    arquivos = sorted(Path(cfg["pasta"]).glob("*.md"))
    trechos = []
    for arquivo in arquivos:
        for secao, conteudo in dividir_em_secoes(arquivo.read_text(encoding="utf-8")):
            for pedaco in subdividir(conteudo, cfg["tamanho_trecho"], cfg["sobreposicao"]):
                trechos.append({"fonte": arquivo.name, "secao": secao, "conteudo": pedaco})
    return len(arquivos), trechos


def texto_para_embedding(secao: str, conteudo: str) -> str:
    """O título vai junto com o texto: dá contexto a trechos que, sozinhos, seriam ambíguos."""
    return f"{secao}\n{conteudo}"


# ------------------------------------------------------------ embeddings e banco

def carregar_modelo(cfg: dict):
    """Carrega o modelo de embedding. Na primeira vez, o fastembed baixa o modelo (cerca de 220 MB)."""
    from fastembed import TextEmbedding  # importado aqui: o --promover não precisa dele

    return TextEmbedding(cfg["modelo_embedding"])


def gerar_embeddings(modelo, textos: list[str]) -> list[list[float]]:
    """Transforma cada texto num vetor (lista de 384 números)."""
    return [[round(float(x), 6) for x in vetor] for vetor in modelo.embed(textos)]


def cliente_supabase(nome_da_chave: str):
    """Conecta ao Supabase com a URL e a chave vindas das variáveis de ambiente (nunca do código)."""
    from supabase import create_client

    # strip(): um espaço ou quebra de linha colado junto com a chave já basta para o Supabase recusar
    url = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
    chave = (os.environ.get(nome_da_chave) or "").strip()
    faltando = [nome for nome, valor in (("SUPABASE_URL", url), (nome_da_chave, chave)) if not valor]
    if faltando:
        raise RuntimeError(f"variável de ambiente ausente: {', '.join(faltando)}")
    return create_client(url, chave)


def diagnostico_supabase(nome_da_chave: str) -> str:
    """Descreve a URL e a chave em uso sem revelar a chave: ajuda a achar o erro 'Invalid API key'."""
    url = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
    chave = (os.environ.get(nome_da_chave) or "").strip()
    projeto = re.match(r"^https://([a-z0-9]+)\.supabase\.co$", url)
    tipo = next((t for t in ("sb_secret_", "sb_publishable_", "eyJ") if chave.startswith(t)), "formato desconhecido")
    return (f"URL aponta para o projeto '{projeto.group(1) if projeto else url}'; "
            f"{nome_da_chave} começa com '{tipo}' e tem {len(chave)} caracteres. "
            "Confira se a chave foi copiada inteira (pelo botão de copiar) e é do MESMO projeto da URL.")


def buscar(cliente, modelo, pergunta: str, cfg: dict, colecao="producao", quantidade=None) -> list[dict]:
    """Busca híbrida (RF10): gera o vetor da pergunta e chama a função buscar_hibrido do banco.
    É a mesma função no app e no portão, para o portão avaliar exatamente a busca que vai para o ar."""
    vetor = gerar_embeddings(modelo, [pergunta])[0]
    resposta = cliente.rpc("buscar_hibrido", {
        "texto_pergunta": pergunta,
        "vetor_pergunta": vetor,
        "quantidade": quantidade or cfg["trechos_por_resposta"],
        "colecao_alvo": colecao,
        "peso_palavras": cfg["peso_palavras"],
        "peso_sentido": cfg["peso_sentido"],
    }).execute()
    return resposta.data or []


# ------------------------------------------------------------ prompt e fontes (RF11 e RF12)

def montar_mensagem(pergunta: str, trechos: list[dict], cfg: dict) -> str:
    """Monta a mensagem enviada ao modelo: os trechos delimitados, a regra e a pergunta."""
    partes = ["Trechos do material de consulta:", ""]
    for n, t in enumerate(trechos, start=1):
        partes += [f'<trecho n="{n}" fonte="{t["fonte"]}" secao="{t["secao"]}">', t["conteudo"], "</trecho>"]
    partes += ["", "Use somente os trechos acima. Se a resposta não estiver neles, responda exatamente:",
               cfg["mensagem_nao_encontrado"], "", f"Pergunta: {pergunta}"]
    return "\n".join(partes)


def listar_fontes(trechos: list[dict]) -> str:
    """Lista de fontes escrita pelo app (não pelo modelo), sem repetição."""
    fontes = list(dict.fromkeys(f"{t['fonte']} › {t['secao']}" for t in trechos))
    return "**Fontes consultadas:**\n" + "\n".join(f"- {f}" for f in fontes)
