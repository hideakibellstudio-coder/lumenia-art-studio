"""
arccc_coupling_metrics.py
=========================
Mede, arquivo por arquivo, os padrões de acoplamento que transformaram a UI
em espaguete, e mantém a catraca (`arccc_coupling_baseline.json`) usada por
`tests/test_arccc_coupling_ratchet.py`.

Por que existe
--------------
O teto de linhas (arccc_governance_rules.py) foi cumprido durante meses e o
código continuou virando espaguete: arquivos eram fatiados por contagem de
linhas, não por responsabilidade. O resultado foram funções livres que
recebem `panel` e mexem nos atributos privados dele, mixins que perguntam
`hasattr(self, ...)` porque não sabem com quem serão combinados, e um
workspace que "apalpa" os painéis dos outros plugins com `hasattr(dock, ...)`.
Nenhuma dessas coisas aparece numa contagem de linhas. Este módulo mede
exatamente elas.

Categorias medidas (todas em ui/, plugins embutidos incluídos)
--------------------------------------------
hasattr
    `hasattr(obj, "nome")`. Quase sempre é um contrato que não existe:
    o chamador não sabe o tipo do objeto e tateia. Exceção: as guardas sobre
    o binário nativo dentro de ui/infrastructure/bridge_client/, que têm catraca própria
    em test_river_ratchets.py e não são contadas aqui.
getattr_literal
    `getattr(obj, "nome", ...)` com nome literal — o mesmo tatear, com valor
    padrão para esconder a ausência. `getattr(obj, variavel)` (despacho por
    tabela) não conta.
foreign_private
    `outro._atributo` onde `outro` não é `self`/`cls`/`super()`. Um objeto
    lendo ou escrevendo o estado privado de outro: a assinatura da
    decomposição falsa.
silent_except
    `except Exception:` (ou `except:`) cujo corpo é só `pass`/`continue`/
    `return`. Engole erro sem deixar rastro.
reverse_import
    Módulo de ui/ fora de ui/plugins/ importando `ui.plugins.*`. O núcleo não
    pode depender das folhas; só o carregador (ui/core/plugins/) conhece o
    pacote de plugins.

Uso
---
    python -m tests.arccc_coupling_metrics            # relatório por categoria
    python -m tests.arccc_coupling_metrics --tighten  # baixa a catraca (nunca sobe)
    python -m tests.arccc_coupling_metrics --rename velho.py novo.py

A catraca só desce. Subir um número exige editar o JSON à mão — e isso
aparece no diff para quem revisa.
"""
from __future__ import annotations

import argparse
import ast
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = Path(__file__).resolve().parent / "arccc_coupling_baseline.json"
SCANNED_ROOTS = ("ui",)
CATEGORIES = ("hasattr", "getattr_literal", "foreign_private", "silent_except", "reverse_import")

# Receptores das guardas sobre o binário nativo (catraca própria em
# test_river_ratchets.py::NATIVE_GUARDS_PERMITIDOS).
_NATIVE_RECEIVERS = {"self._facade", "facade", "self._native", "native", "f"}
_SELF_NAMES = {"self", "cls"}
# O carregador de plugins é o único ponto de ui/ que pode conhecer `ui.plugins.*`.
_PLUGIN_LOADER_DIR = "ui/core/plugins/"
_PLUGINS_DIR = "ui/plugins/"


@dataclass(frozen=True)
class Occurrence:
    path: str
    line: int
    category: str
    detail: str


def _is_self_receiver(node: ast.AST) -> bool:
    if isinstance(node, ast.Name) and node.id in _SELF_NAMES:
        return True
    return isinstance(node, ast.Call) and getattr(node.func, "id", None) == "super"


def _is_silent_body(body: list[ast.stmt]) -> bool:
    for stmt in body:
        if isinstance(stmt, (ast.Pass, ast.Continue)):
            continue
        if isinstance(stmt, ast.Return) and stmt.value is None:
            continue
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            continue  # docstring/comentário em string
        return False
    return True


def _imported_modules(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
        return [node.module]
    return []


def scan_file(path: Path) -> list[Occurrence]:
    rel = path.relative_to(ROOT).as_posix()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
    in_backends = rel.startswith("ui/infrastructure/bridge_client/")
    found: list[Occurrence] = []

    def add(node: ast.AST, category: str, detail: str) -> None:
        found.append(Occurrence(rel, getattr(node, "lineno", 0), category, detail))

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            args = node.args
            if node.func.id == "hasattr" and len(args) == 2:
                receiver = ast.unparse(args[0])
                if not (in_backends and receiver in _NATIVE_RECEIVERS):
                    add(node, "hasattr", ast.unparse(node))
            elif node.func.id == "getattr" and len(args) >= 2 and isinstance(args[1], ast.Constant):
                add(node, "getattr_literal", ast.unparse(node))
        elif isinstance(node, ast.Attribute):
            name = node.attr
            if name.startswith("_") and not name.startswith("__") and not _is_self_receiver(node.value):
                add(node, "foreign_private", ast.unparse(node))
        elif isinstance(node, ast.ExceptHandler):
            broad = node.type is None or (
                isinstance(node.type, ast.Name) and node.type.id in ("Exception", "BaseException")
            )
            if broad and _is_silent_body(node.body):
                add(node, "silent_except", "except Exception: pass")
        if rel.startswith("ui/") and not rel.startswith((_PLUGIN_LOADER_DIR, _PLUGINS_DIR)):
            for module in _imported_modules(node):
                if module == "ui.plugins" or module.startswith("ui.plugins."):
                    add(node, "reverse_import", module)
    return found


def iter_source_files() -> list[Path]:
    files: list[Path] = []
    for base in SCANNED_ROOTS:
        for path in sorted((ROOT / base).rglob("*.py")):
            if "__pycache__" not in path.parts:
                files.append(path)
    return files


def scan_all() -> list[Occurrence]:
    occurrences: list[Occurrence] = []
    for path in iter_source_files():
        occurrences.extend(scan_file(path))
    return occurrences


def count_by_file(occurrences: list[Occurrence]) -> dict[str, dict[str, int]]:
    counts: dict[str, Counter] = {}
    for occ in occurrences:
        counts.setdefault(occ.path, Counter())[occ.category] += 1
    return {path: dict(sorted(counter.items())) for path, counter in sorted(counts.items())}


def load_baseline() -> dict[str, dict[str, int]]:
    if not BASELINE_PATH.exists():
        return {}
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def save_baseline(baseline: dict[str, dict[str, int]]) -> None:
    cleaned = {
        path: {cat: n for cat, n in sorted(cats.items()) if n > 0}
        for path, cats in sorted(baseline.items())
    }
    cleaned = {path: cats for path, cats in cleaned.items() if cats}
    BASELINE_PATH.write_text(json.dumps(cleaned, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def totals(counts: dict[str, dict[str, int]]) -> dict[str, int]:
    total: Counter = Counter()
    for cats in counts.values():
        total.update(cats)
    return {cat: total.get(cat, 0) for cat in CATEGORIES}


def tighten() -> dict[str, int]:
    """Baixa a catraca até o valor atual. Nunca sobe um número."""
    current = count_by_file(scan_all())
    baseline = load_baseline()
    tightened: dict[str, dict[str, int]] = {}
    for path, cats in baseline.items():
        if not (ROOT / path).exists():
            continue
        now = current.get(path, {})
        tightened[path] = {cat: min(n, now.get(cat, 0)) for cat, n in cats.items()}
    save_baseline(tightened)
    return totals(tightened)


def rename(old: str, new: str) -> None:
    """Carrega a catraca de um arquivo movido/renomeado para o novo caminho."""
    baseline = load_baseline()
    if old not in baseline:
        raise SystemExit(f"{old} não está na catraca")
    merged = Counter(baseline.get(new, {}))
    merged.update(baseline.pop(old))
    baseline[new] = dict(merged)
    save_baseline(baseline)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--tighten", action="store_true", help="baixa a catraca até o valor atual")
    parser.add_argument("--rename", nargs=2, metavar=("VELHO", "NOVO"), help="carrega a catraca de um arquivo movido")
    parser.add_argument("--top", type=int, default=10, help="quantos arquivos listar por categoria")
    args = parser.parse_args()
    if args.rename:
        rename(*args.rename)
        return 0
    if args.tighten:
        print("catraca:", tighten())
        return 0
    current = count_by_file(scan_all())
    print("total atual:", totals(current))
    print("catraca    :", totals(load_baseline()))
    for cat in CATEGORIES:
        ranked = sorted(((cats.get(cat, 0), path) for path, cats in current.items()), reverse=True)
        ranked = [(n, p) for n, p in ranked if n][: args.top]
        if ranked:
            print(f"\n{cat}:")
            for n, path in ranked:
                print(f"  {n:4d}  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
