"""Superfície do contrato do motor: o que ninguém chama e quem consome cada papel (ARCcC S2.3).

O `EngineBackend` tem um método por capacidade que a facade do motor expõe. A 4.4.9 pede contrato
menor que a implementação e nenhum mecanismo para possibilidade que não aconteceu; esta medição
dá a conta a cada rodada:

- métodos do contrato sem chamador em produção (a interface, fora da ponte e do próprio contrato);
- papéis (`Protocol`s de `backend_protocols*.py`) sem consumidor em produção;
- módulos que dependem do `EngineBackend` inteiro em vez de um papel.

`python -m tests.arccc_engine_roles` imprime o relatório; `tests/test_engine_contract_surface.py`
falha se o número piorar.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Iterable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
ENGINE_PACKAGE = "ui/core/engine/"
BRIDGE_PACKAGE = "ui/infrastructure/bridge_client/"
CONTRACT_FILE = "ui/core/engine/backend.py"
PROTOCOL_FILES = ("ui/core/engine/backend_protocols.py", "ui/core/engine/backend_protocols_selection.py")
CONTRACT_CLASS = "EngineBackend"


def _parse(relative: str) -> ast.Module:
    return ast.parse((REPO_ROOT / relative).read_text(encoding="utf-8"))


def contract_methods() -> list[str]:
    """Nomes públicos do `EngineBackend` (métodos e propriedades), na ordem do arquivo."""
    for node in _parse(CONTRACT_FILE).body:
        if isinstance(node, ast.ClassDef) and node.name == CONTRACT_CLASS:
            return [n.name for n in node.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")]
    raise LookupError(f"{CONTRACT_CLASS} não está em {CONTRACT_FILE}")


def role_members() -> dict[str, list[str]]:
    """Cada `Protocol` de papel e os nomes públicos que ele declara."""
    roles: dict[str, list[str]] = {}
    for relative in PROTOCOL_FILES:
        for node in _parse(relative).body:
            if isinstance(node, ast.ClassDef) and node.name.endswith("Protocol"):
                roles[node.name] = [n.name for n in node.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")]
    return roles


def production_texts() -> dict[str, str]:
    """O código da interface que usa o motor: `ui/`, sem a ponte e sem os arquivos do contrato."""
    skipped = (BRIDGE_PACKAGE, CONTRACT_FILE, *PROTOCOL_FILES)
    texts: dict[str, str] = {}
    for path in sorted((REPO_ROOT / "ui").rglob("*.py")):
        relative = path.relative_to(REPO_ROOT).as_posix()
        if not relative.startswith(skipped[0]) and relative not in skipped[1:]:
            texts[relative] = path.read_text(encoding="utf-8")
    return texts


def unused_methods(methods: Iterable[str], texts: Mapping[str, str]) -> list[str]:
    """Métodos que nenhum arquivo cita como `.nome` nem como texto "nome" (tabelas de nomes)."""
    unused = []
    for name in methods:
        pattern = re.compile(r"[.\"']%s\b" % re.escape(name))
        if not any(pattern.search(text) for text in texts.values()):
            unused.append(name)
    return unused


def role_consumers(roles: Iterable[str], texts: Mapping[str, str]) -> dict[str, list[str]]:
    """Arquivos de produção que citam cada papel (os do próprio contrato e da ponte não entram)."""
    consumers: dict[str, list[str]] = {}
    for role in roles:
        pattern = re.compile(r"\b%s\b" % re.escape(role))
        consumers[role] = [rel for rel, text in texts.items() if pattern.search(text)]
    return consumers


def whole_contract_users(texts: Mapping[str, str]) -> list[str]:
    """Arquivos fora do pacote do contrato que importam o `EngineBackend` inteiro."""
    pattern = re.compile(r"^\s*from\s+ui\.core\.engine\.backend\s+import\s+[^\n]*\b%s\b" % CONTRACT_CLASS, re.MULTILINE)
    return [rel for rel, text in texts.items() if not rel.startswith(ENGINE_PACKAGE) and pattern.search(text)]


def report() -> str:
    methods = contract_methods()
    texts = production_texts()
    roles = role_members()
    lines = [f"métodos do contrato: {len(methods)}", f"sem chamador em produção: {len(unused_methods(methods, texts))}"]
    for name in unused_methods(methods, texts):
        lines.append(f"  - {name}")
    for role, files in role_consumers(roles, texts).items():
        lines.append(f"{role}: {len(roles[role])} membros, {len(files)} consumidor(es) em produção")
    lines.append(f"dependem do EngineBackend inteiro: {len(whole_contract_users(texts))}")
    for rel in whole_contract_users(texts):
        lines.append(f"  - {rel}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(report())
