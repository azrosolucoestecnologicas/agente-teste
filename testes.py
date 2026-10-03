"""
Portão do deploy. Roda no GitHub Actions ANTES de publicar.
Se qualquer verificação falhar, o processo para e a versão antiga continua no ar.
"""
import ast
import re
import subprocess
import sys
from pathlib import Path

import yaml

erros = []

# 1. O config.yml existe e é um YAML válido?
try:
    config = yaml.safe_load(Path("config.yml").read_text(encoding="utf-8"))
except Exception as e:
    print(f"ERRO: config.yml inválido: {e}")
    sys.exit(1)

# 2. Os campos obrigatórios estão preenchidos?
for campo in ["nome", "descricao", "tema", "prompt_sistema"]:
    if not str(config.get(campo, "")).strip():
        erros.append(f"campo obrigatório vazio no config.yml: {campo}")

# 3. O tema é um dos permitidos? Aceita uma cor ("azul") ou duas ("azul e vermelho").
temas = {"azul", "verde", "vermelho", "laranja", "roxo", "grafite"}
cores = [c.strip() for c in str(config.get("tema", "")).split(" e ")]
if len(cores) > 2 or any(c not in temas for c in cores):
    erros.append(f"tema '{config.get('tema')}' não existe. Use uma ou duas destas cores "
                 f"(ex.: 'azul' ou 'azul e vermelho'): {', '.join(sorted(temas))}")

# 3b. Os provedores de IA estão no formato certo? (provedor: modelo)
provedores_validos = {"openrouter", "anthropic", "openai"}
provedores = config.get("provedores")
if not isinstance(provedores, dict) or not provedores:
    erros.append("provedores: liste pelo menos um, no formato 'openrouter: nome-do-modelo'")
else:
    for nome, modelo in provedores.items():
        if nome not in provedores_validos:
            erros.append(f"provedor '{nome}' não existe. Use: {', '.join(sorted(provedores_validos))}")
        elif not str(modelo or "").strip():
            erros.append(f"provedor '{nome}' está sem modelo")

# 4. O prompt de sistema tem conteúdo de verdade?
if len(str(config.get("prompt_sistema", ""))) < 80:
    erros.append("prompt_sistema curto demais: descreva quem é o assistente, o público e os limites")

# 5. A logo existe e é aceita pelo Hugging Face?
logo = str(config.get("logo", "")).strip()
if logo and not logo.startswith("http"):
    if not Path(logo).exists():
        erros.append(f"logo '{logo}' não encontrada no repositório")
    elif not logo.lower().endswith(".svg"):
        erros.append("logo dentro do repositório precisa ser .svg (ou use um link https)")

# 6. O servidor.py e o chat.py têm sintaxe Python válida? (Parte 3: o app.py saiu)
for nome in ["servidor.py", "chat.py"]:
    try:
        ast.parse(Path(nome).read_text(encoding="utf-8"))
    except FileNotFoundError:
        erros.append(f"{nome} não encontrado")
    except SyntaxError as e:
        erros.append(f"erro de sintaxe no {nome}, linha {e.lineno}: {e.msg}")


def arquivos_do_projeto():
    """Os arquivos do repositório, sem .git, dependências instaladas (node_modules) e o build (frontend/dist)."""
    for arquivo in Path(".").rglob("*"):
        if arquivo.is_file() and not {".git", "node_modules", "dist"} & set(arquivo.parts):
            yield arquivo


TEXTO = {".py", ".yml", ".yaml", ".md", ".txt", ".svg", ".json", ".js", ".jsx", ".html", ".css", ".toml"}

# 7. Nenhuma chave de API foi colocada por engano nos arquivos
padrao = re.compile(r"sk-or-[A-Za-z0-9_\-]{10,}|sk-ant-[A-Za-z0-9_\-]{10,}|sk-proj-[A-Za-z0-9_\-]{10,}|hf_[A-Za-z0-9]{20,}")
for arquivo in arquivos_do_projeto():
    if arquivo.suffix in TEXTO:
        if padrao.search(arquivo.read_text(encoding="utf-8", errors="ignore")):
            erros.append(f"possível chave de API dentro de {arquivo}: remova e REVOGUE a chave")

# ------------------------------------------------------------ Parte 2: base de conhecimento

# T10. O bloco base_conhecimento respeita o contrato, e o prompt tem a frase de "não encontrei"
padroes = {"ativa": True, "pasta": "documentos", "tamanho_trecho": 1200, "sobreposicao": 150,
           "trechos_por_resposta": 4, "peso_palavras": 1, "peso_sentido": 1,
           "mensagem_nao_encontrado": "Não encontrei isso no material do curso."}
base = {**padroes, **(config.get("base_conhecimento") or {})}


def inteiro_entre(campo, minimo, maximo):
    valor = base[campo]
    if not isinstance(valor, int) or isinstance(valor, bool) or not minimo <= valor <= maximo:
        erros.append(f"base_conhecimento.{campo} precisa ser um número inteiro de {minimo} a {maximo} (está: {valor})")
        return False
    return True


if not isinstance(base["ativa"], bool):
    erros.append("base_conhecimento.ativa precisa ser true ou false")
if inteiro_entre("tamanho_trecho", 300, 4000):
    inteiro_entre("sobreposicao", 0, base["tamanho_trecho"] // 2)
inteiro_entre("trechos_por_resposta", 1, 10)
pesos = [base["peso_palavras"], base["peso_sentido"]]
if any(not isinstance(p, (int, float)) or isinstance(p, bool) or p < 0 for p in pesos):
    erros.append("base_conhecimento.peso_palavras e peso_sentido precisam ser números maiores ou iguais a zero")
elif pesos == [0, 0]:
    erros.append("base_conhecimento: peso_palavras e peso_sentido não podem ser zero ao mesmo tempo")
mensagem = str(base["mensagem_nao_encontrado"]).strip()
if base["ativa"] is True and mensagem not in str(config.get("prompt_sistema", "")):
    erros.append(f"o prompt_sistema precisa conter a frase exata de mensagem_nao_encontrado: \"{mensagem}\"")

if base["ativa"] is True:
    # T11. A pasta de documentos existe, só tem .md e .pdf, e cada .md tem título e conteúdo
    # (o .pdf é conferido na indexação, depois de convertido para Markdown: RF31)
    pasta = Path(str(base["pasta"]))
    documentos = sorted(a for a in pasta.iterdir() if a.suffix.lower() in {".md", ".pdf"}
                        and not a.name.startswith(".")) if pasta.is_dir() else []
    if not pasta.is_dir():
        erros.append(f"pasta de documentos '{pasta}' não encontrada")
    elif not documentos:
        erros.append(f"a pasta '{pasta}' não tem nenhum arquivo .md ou .pdf")
    else:
        for arquivo in pasta.iterdir():
            if arquivo.name.startswith("."):
                continue
            if arquivo.suffix.lower() not in {".md", ".pdf"}:
                erros.append(f"'{arquivo}' não é .md nem .pdf: Word e outros formatos ficam fora (salve como PDF)")
            elif arquivo.suffix.lower() == ".pdf" and arquivo.stat().st_size > 50 * 1024 * 1024:
                erros.append(f"'{arquivo}' passa de 50 MB: divida o PDF em partes menores")
        for arquivo in (d for d in documentos if d.suffix.lower() == ".md"):
            texto = arquivo.read_text(encoding="utf-8", errors="ignore")
            if not re.search(r"^#{1,3} \S", texto, re.M):
                erros.append(f"'{arquivo}' não tem nenhum título (linha começando com #)")
            if len(texto.strip()) < 200:
                erros.append(f"'{arquivo}' tem menos de 200 caracteres")

    # T12. As perguntas de teste são válidas e apontam para documentos que existem
    try:
        teste = yaml.safe_load(Path("perguntas_teste.yml").read_text(encoding="utf-8")) or {}
    except Exception as e:
        erros.append(f"perguntas_teste.yml ausente ou inválido: {e}")
        teste = None
    if teste is not None:
        limiar, top_k = teste.get("limiar_hit_rate"), teste.get("top_k")
        if not isinstance(limiar, (int, float)) or isinstance(limiar, bool) or not 0 <= limiar <= 1:
            erros.append("perguntas_teste.yml: limiar_hit_rate precisa ser um número de 0 a 1")
        if not isinstance(top_k, int) or isinstance(top_k, bool) or not 1 <= top_k <= 10:
            erros.append("perguntas_teste.yml: top_k precisa ser um número inteiro de 1 a 10")
        perguntas = teste.get("perguntas") or []
        if len(perguntas) < 5:
            erros.append(f"perguntas_teste.yml precisa de pelo menos 5 perguntas (tem {len(perguntas)})")
        nomes = {d.name for d in documentos}
        for i, p in enumerate(perguntas, start=1):
            if not isinstance(p, dict) or not str(p.get("pergunta", "")).strip() or not p.get("fonte_esperada"):
                erros.append(f"perguntas_teste.yml, pergunta {i}: precisa de 'pergunta' e 'fonte_esperada'")
            elif p["fonte_esperada"] not in nomes:
                erros.append(f"perguntas_teste.yml, pergunta {i}: fonte_esperada '{p['fonte_esperada']}' "
                             f"não existe em {pasta}/")

# T13. Nenhuma chave secreta do Supabase nos arquivos (nem token JWT, formato das chaves antigas)
padrao_supabase = re.compile(r"sb_secret_[A-Za-z0-9_\-]{20,}|eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}")
for arquivo in arquivos_do_projeto():
    if arquivo.suffix in TEXTO | {".sql"}:
        if padrao_supabase.search(arquivo.read_text(encoding="utf-8", errors="ignore")):
            erros.append(f"possível chave do Supabase dentro de {arquivo}: remova e REVOGUE a chave no painel")

# ------------------------------------------------------------ Parte 3: interface e produção

# T15. O bloco interface respeita o contrato (seção 7 da spec da Parte 3). Todos os campos são opcionais.
interface = config.get("interface") or {}
if not isinstance(interface, dict):
    erros.append("interface: precisa ser um bloco com campos (tema_inicial, rodape, ...)")
    interface = {}
conhecidos = {"tema_inicial", "rodape", "limite_caracteres", "perguntas_por_minuto"}
for campo in sorted(set(interface) - conhecidos):
    erros.append(f"interface.{campo} não existe. Campos aceitos: {', '.join(sorted(conhecidos))}")
if "tema_inicial" in interface and interface["tema_inicial"] not in {"claro", "escuro", "sistema"}:
    erros.append("interface.tema_inicial precisa ser claro, escuro ou sistema")
if "rodape" in interface and not (isinstance(interface["rodape"], str) and 0 < len(interface["rodape"]) <= 200):
    erros.append("interface.rodape precisa ser um texto de até 200 caracteres")
for campo, minimo, maximo in [("limite_caracteres", 200, 4000), ("perguntas_por_minuto", 1, 60)]:
    valor = interface.get(campo, minimo)
    if not isinstance(valor, int) or isinstance(valor, bool) or not minimo <= valor <= maximo:
        erros.append(f"interface.{campo} precisa ser um número inteiro de {minimo} a {maximo} (está: {valor})")

# T17. O front-end não carrega segredo: o build não tem chave nem nome de variável secreta,
# e nenhum frontend/.env* está no Git (tudo que vai para o front-end é público)
segredos = re.compile(padrao.pattern + "|" + padrao_supabase.pattern
                      + r"|OPENROUTER_API_KEY|ANTHROPIC_API_KEY|OPENAI_API_KEY|SUPABASE_SECRET_KEY|HF_TOKEN")
dist = Path("frontend/dist")
for arquivo in (dist.rglob("*") if dist.is_dir() else []):
    if arquivo.is_file() and segredos.search(arquivo.read_text(encoding="utf-8", errors="ignore")):
        erros.append(f"o build do front-end ({arquivo}) contém chave ou nome de variável secreta")
try:
    versionados = subprocess.run(["git", "ls-files", "frontend"], capture_output=True, text=True).stdout.split()
except FileNotFoundError:
    versionados = []
for nome in versionados:
    if Path(nome).name.startswith(".env"):
        erros.append(f"{nome} está no Git: o front-end não guarda configuração secreta; apague e revogue as chaves")

if erros:
    print("O portão barrou o deploy:\n")
    for e in erros:
        print(f"  - {e}")
    sys.exit(1)

print("Todas as verificações passaram. Liberado para publicar.")
