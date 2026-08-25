import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

print("=== VERIFICAÇÃO DE REGRA DE OURO 4 (ARCcC LOC CHECK) ===")
large_files = []

for root, dirs, files in os.walk(PROJECT_ROOT):
    # Ignora pastas de build, cache, .git, venv
    if any(ignore in root for ignore in [".git", "__pycache__", "build", ".pytest_cache", ".venv", "env", "node_modules"]):
        continue
    for f in files:
        if f.endswith((".py", ".cpp", ".hpp", ".h", ".c")):
            path = os.path.join(root, f)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as file:
                    lines = file.readlines()
                    count = len(lines)
                    rel_path = os.path.relpath(path, PROJECT_ROOT)
                    if count > 500:
                        large_files.append((count, rel_path))
            except Exception as e:
                pass

large_files.sort(key=lambda x: x[0], reverse=True)
if not large_files:
    print("Nenhum arquivo acima de 500 LOC! Todos os módulos respeitam a Regra 4 de Ouro do ARCcC.")
else:
    print(f"Encontrados {len(large_files)} arquivos com > 500 LOC:")
    for count, rel in large_files:
        print(f"  - {count:4d} LOC : {rel}")
