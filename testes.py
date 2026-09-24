"""
Portão do deploy. Roda no GitHub Actions ANTES de publicar.
Se qualquer verificação falhar, o processo para e a versão antiga continua no ar.
"""
import ast
import re
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
for campo in ["nome", "descricao", "tema", "modelo", "prompt_sistema"]:
    if not str(config.get(campo, "")).strip():
        erros.append(f"campo obrigatório vazio no config.yml: {campo}")

# 3. O tema é um dos permitidos? Aceita uma cor ("azul") ou duas ("azul e vermelho").
temas = {"azul", "verde", "vermelho", "laranja", "roxo", "grafite"}
cores = [c.strip() for c in str(config.get("tema", "")).split(" e ")]
if len(cores) > 2 or any(c not in temas for c in cores):
    erros.append(f"tema '{config.get('tema')}' não existe. Use uma ou duas destas cores "
                 f"(ex.: 'azul' ou 'azul e vermelho'): {', '.join(sorted(temas))}")

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

# 6. O app.py tem sintaxe Python válida?
try:
    ast.parse(Path("app.py").read_text(encoding="utf-8"))
except SyntaxError as e:
    erros.append(f"erro de sintaxe no app.py, linha {e.lineno}: {e.msg}")

# 7. Nenhuma chave de API foi colocada por engano nos arquivos
padrao = re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}|hf_[A-Za-z0-9]{20,}")
for arquivo in Path(".").rglob("*"):
    if ".git" in arquivo.parts or not arquivo.is_file():
        continue
    if arquivo.suffix in {".py", ".yml", ".yaml", ".md", ".txt", ".svg", ".json"}:
        if padrao.search(arquivo.read_text(encoding="utf-8", errors="ignore")):
            erros.append(f"possível chave de API dentro de {arquivo}: remova e REVOGUE a chave")

if erros:
    print("O portão barrou o deploy:\n")
    for e in erros:
        print(f"  - {e}")
    sys.exit(1)

print("Todas as verificações passaram. Liberado para publicar.")
