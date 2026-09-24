"""Catraca de idioma: nenhum arquivo ganha identificador com palavra em português.

Seção 14 do ARCcC: nomes de pasta, arquivo, classe, função, variável e
constante são em inglês; português só em comentários, documentação e textos
para o usuário (`tr(...)`). O que é medido e como está em
tests/arccc_identifier_language.py. A catraca só desce.
"""
from __future__ import annotations

from tests import arccc_identifier_language as language


def test_no_file_gets_more_portuguese_identifiers():
    baseline = language.load_baseline()
    worse = []
    for path, names in language.scan_all().items():
        limit = baseline.get(path, 0)
        if len(names) > limit:
            worse.append(f"  {path}: {len(names)} > catraca {limit} ({', '.join(names)})")
    assert not worse, (
        "Identificador novo em português (nome de código é em inglês; português só em comentário,"
        " documentação e tr(...)):\n" + "\n".join(worse)
        + "\n\nMoveu ou renomeou um arquivo? python -m tests.arccc_identifier_language --rename VELHO NOVO"
    )


def test_ratchet_is_tight():
    baseline = language.load_baseline()
    current = {path: len(names) for path, names in language.scan_all().items()}
    loose = [f"  {path}: catraca {limit}, atual {current.get(path, 0)}"
             for path, limit in baseline.items() if current.get(path, 0) < limit]
    assert not loose, (
        "Menos nomes em português -- ótimo. Registre a melhoria para travá-la:\n"
        + "\n".join(loose) + "\n\n    python -m tests.arccc_identifier_language --tighten"
    )
