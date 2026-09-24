"""
test_arccc_coupling_ratchet.py
==============================
Catraca de acoplamento da UI: nenhum arquivo de ui/ ou plugins/ pode ganhar
mais `hasattr`, `getattr("literal")`, acesso a privado alheio, `except`
silencioso ou import de `plugins.*` a partir do núcleo do que já tinha.

O que medir e por quê está em tests/arccc_coupling_metrics.py. Como corrigir
cada categoria (em vez de só contornar o teste) está em
docs/02-arquitetura/06-contratos-entre-componentes.md.
"""
from __future__ import annotations

from tests import arccc_coupling_metrics as metrics

_HOW_TO_FIX = {
    "hasattr": (
        "Não tateie objetos. Se o objeto é seu, declare o atributo no __init__; "
        "se é de outro componente, peça um contrato (Protocol/ABC ou sinal) e "
        "chame o método direto."
    ),
    "getattr_literal": (
        "getattr com nome fixo e valor padrão esconde um contrato ausente. "
        "Declare o atributo ou exponha um método/propriedade no dono."
    ),
    "foreign_private": (
        "Um objeto não lê nem escreve `_privado` de outro. Mova o estado para "
        "quem o usa, ou exponha um método público no dono."
    ),
    "silent_except": (
        "Capture a exceção específica, ou registre com logger.exception(...). "
        "Erro engolido em silêncio é bug escondido."
    ),
    "reverse_import": (
        "ui/ não importa plugins/: o núcleo não depende das folhas. Publique um "
        "contrato em ui/core/ e deixe o plugin registrá-lo no ServiceRegistry."
    ),
}


def test_no_file_gets_more_coupled():
    occurrences = metrics.scan_all()
    current = metrics.count_by_file(occurrences)
    baseline = metrics.load_baseline()

    worse: list[str] = []
    for path, cats in current.items():
        allowed = baseline.get(path, {})
        for cat, count in cats.items():
            limit = allowed.get(cat, 0)
            if count > limit:
                where = [o for o in occurrences if o.path == path and o.category == cat]
                lines = "\n".join(f"      {o.path}:{o.line}  {o.detail[:90]}" for o in where)
                worse.append(f"  {path}  [{cat}] {count} > catraca {limit}\n{lines}\n    -> {_HOW_TO_FIX[cat]}")

    assert not worse, (
        "Acoplamento novo em ui/ ou plugins/ (a catraca só desce):\n"
        + "\n".join(worse)
        + "\n\nMoveu ou renomeou um arquivo? python -m tests.arccc_coupling_metrics --rename VELHO NOVO"
    )


def test_ratchet_is_tight():
    """Toda melhoria tem de ser registrada, senão o próximo agente pode desfazê-la."""
    current = metrics.count_by_file(metrics.scan_all())
    baseline = metrics.load_baseline()

    loose: list[str] = []
    for path, cats in baseline.items():
        for cat, limit in cats.items():
            now = current.get(path, {}).get(cat, 0)
            if now < limit:
                loose.append(f"  {path}  [{cat}] catraca {limit}, atual {now}")

    assert not loose, (
        "Acoplamento diminuiu -- ótimo. Registre a melhoria para travá-la:\n"
        "  python -m tests.arccc_coupling_metrics --tighten\n" + "\n".join(loose)
    )
