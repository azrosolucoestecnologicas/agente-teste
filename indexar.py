"""
Monta o índice da base de conhecimento no Supabase. Roda no GitHub Actions.

  python indexar.py             lê documentos/, gera os embeddings e grava a coleção 'teste'  (RF8)
  python indexar.py --promover  troca a coleção 'producao' pela 'teste', que já passou no portão  (RF9)

Precisa das variáveis de ambiente SUPABASE_URL e SUPABASE_SECRET_KEY (a chave que grava).
"""
import sys

import rag

LOTE = 100  # linhas gravadas por vez


def indexar():
    cfg = rag.carregar_config()
    documentos, trechos = rag.dividir_em_trechos(cfg)
    if not trechos:
        sys.exit(f"ERRO: nenhum trecho encontrado em {cfg['pasta']}/")

    cliente = rag.cliente_supabase("SUPABASE_SECRET_KEY")
    print(f"Gerando embeddings de {len(trechos)} trechos com {cfg['modelo_embedding']}...")
    modelo = rag.carregar_modelo(cfg)
    vetores = rag.gerar_embeddings(modelo, [rag.texto_para_embedding(t["secao"], t["conteudo"]) for t in trechos])

    # A coleção 'teste' é refeita do zero; a 'producao' (o que está no ar) não é tocada aqui
    cliente.table("trechos").delete().eq("colecao", "teste").execute()
    linhas = [{**t, "colecao": "teste", "embedding": v} for t, v in zip(trechos, vetores)]
    for i in range(0, len(linhas), LOTE):
        cliente.table("trechos").insert(linhas[i:i + LOTE]).execute()

    print(f"Índice pronto: {documentos} documentos, {len(trechos)} trechos, matriz ({len(trechos)}, {len(vetores[0])})")


def promover():
    cliente = rag.cliente_supabase("SUPABASE_SECRET_KEY")
    total = cliente.rpc("promover_colecao", {}).execute().data
    print(f"Coleção 'teste' promovida para 'producao': {total} trechos no ar.")


if __name__ == "__main__":
    try:
        promover() if "--promover" in sys.argv else indexar()
    except RuntimeError as e:
        sys.exit(f"ERRO: {e}. No GitHub, cadastre em Settings > Secrets and variables > Actions.")
