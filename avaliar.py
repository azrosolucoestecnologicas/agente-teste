"""
Portão da busca (T14). Roda no GitHub Actions, depois do indexar.py.
Faz cada pergunta de perguntas_teste.yml na coleção 'teste' e confere se o trecho esperado veio.
Se o hit rate ficar abaixo do limiar, sai com erro e nada é publicado.  (RF15)

Precisa das variáveis de ambiente SUPABASE_URL e SUPABASE_SECRET_KEY.
"""
import sys
from pathlib import Path

import yaml

import rag


def acertou(trecho: dict, pergunta: dict) -> bool:
    """O trecho é o esperado? Mesma fonte e, se houver secao_esperada, ela aparece no título da seção."""
    if trecho["fonte"] != pergunta["fonte_esperada"]:
        return False
    esperada = str(pergunta.get("secao_esperada") or "").lower()
    return esperada in trecho["secao"].lower()


def curto(texto: str, limite: int) -> str:
    return texto if len(texto) <= limite else texto[: limite - 1] + "…"


def main():
    cfg = rag.carregar_config()
    teste = yaml.safe_load(Path("perguntas_teste.yml").read_text(encoding="utf-8"))
    top_k, limiar = int(teste["top_k"]), float(teste["limiar_hit_rate"])
    perguntas = teste["perguntas"]

    try:
        cliente = rag.cliente_supabase("SUPABASE_SECRET_KEY")
    except RuntimeError as e:
        sys.exit(f"ERRO: {e}. No GitHub, cadastre em Settings > Secrets and variables > Actions.")
    modelo = rag.carregar_modelo(cfg)

    acertos, soma_rr, falhas = 0, 0.0, []
    print(f"\nPerguntas de teste (top {top_k}, coleção 'teste'):\n")
    print(f"  {'':2} {'Pergunta':<58} {'Posição':<9} Veio em 1º lugar")
    for p in perguntas:
        trechos = rag.buscar(cliente, modelo, p["pergunta"], cfg, colecao="teste", quantidade=top_k)
        posicao = next((i for i, t in enumerate(trechos, start=1) if acertou(t, p)), None)
        primeiro = f"{trechos[0]['fonte']} › {trechos[0]['secao']}" if trechos else "(nada)"
        if posicao:
            acertos += 1
            soma_rr += 1 / posicao
        else:
            falhas.append(p)
        marca = "✓" if posicao else "✗"
        print(f"  {marca:2} {curto(p['pergunta'], 58):<58} {(f'{posicao}º' if posicao else 'não veio'):<9} "
              f"{curto(primeiro, 70)}")

    hit_rate, mrr = acertos / len(perguntas), soma_rr / len(perguntas)
    print(f"\nHit rate@{top_k}: {acertos}/{len(perguntas)} = {hit_rate:.2f}   (limiar: {limiar:.2f})")
    print(f"MRR: {mrr:.2f}\n")

    if hit_rate < limiar:
        print("O portão barrou o deploy: a busca não encontrou o trecho esperado nestas perguntas:\n")
        for p in falhas:
            print(f"  - {p['pergunta']}  (esperado: {p['fonte_esperada']} › {p.get('secao_esperada', 'qualquer seção')})")
        print("\nA coleção 'producao' não foi alterada: o assistente no ar continua com o índice anterior.")
        sys.exit(1)
    print("Busca aprovada. Liberado para promover o índice e publicar.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        if "Invalid API key" in str(e) or "401" in str(e):
            sys.exit(f"ERRO: o Supabase recusou a chave (Invalid API key). {rag.diagnostico_supabase('SUPABASE_SECRET_KEY')}")
        raise
