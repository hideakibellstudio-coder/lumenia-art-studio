"""Each method of the .pyi takes what the binary takes: how many arguments and of what kind.

`test_pyi_contract_matches_binary.py` compares NAMES. It did not see that
`BezierCurve.set_control_points` takes four `Point2D` while the stub said four
floats, nor that `commit_transform` has two optional flags, `DynamicStabilizer.update`
takes a pressure, `end_stroke_raw` returns the stroke rectangle, `apply_prepared_geometry`
takes the prepared facade and the viewport tile queries take three arguments
(11 of 192 methods, found on 2026-10-01). A stub that lies about a signature is
worse than none: type checkers and readers trust it.

The comparison reads the signature pybind11 writes in each method's docstring, so it
needs no hand-kept table. Numeric kinds (int, float, SupportsIndex...) are one kind:
pybind11 spells them differently across versions and accepts either.
"""

from __future__ import annotations

import ast
import pathlib
import re

import pytest

native = pytest.importorskip(
    "aladyn_engine_native", reason="native module not built in this environment"
)

CONTRACTS = pathlib.Path(__file__).resolve().parents[1] / "bridge" / "boundary" / "contracts"
PRIMITIVES = {"number", "bool", "str", "bytes", "sequence"}


def _kind(annotation: str) -> str:
    text = annotation.replace('"', "").replace("'", "").strip()
    if text.startswith("Optional[") and text.endswith("]"):
        return _kind(text[len("Optional["):-1])
    if "|" in text:
        kinds = {_kind(part) for part in text.split("|")}
        return kinds.pop() if len(kinds) == 1 else "any"
    base = text.split("[", 1)[0].split(".")[-1]
    if base in {"int", "float"} or base.startswith("Supports"):
        return "number"
    if base in {"bool", "str"}:
        return base
    if base in {"bytes", "bytearray", "Buffer"}:
        return "bytes"
    if base in {"List", "list", "Sequence", "Tuple", "tuple"}:
        return "sequence"
    return base or "any"


def _compatible(declared: str, actual: str) -> bool:
    if declared == actual or "any" in (declared, actual):
        return True
    if {declared, actual} <= {"number", "bool"}:
        return True  # pybind11 takes a bool where an int is asked, and the stubs vary
    if {declared, actual} <= {"sequence", "bytes"}:
        return True
    return False


def _declared_signatures() -> dict[tuple[str, str], list[tuple[int, int, list[str]]]]:
    """{(class, method): [(required, total, kinds)]} from every .pyi (overloads add entries)."""
    found: dict[tuple[str, str], list[tuple[int, int, list[str]]]] = {}
    for stub in sorted(CONTRACTS.glob("*.pyi")):
        for node in ast.parse(stub.read_text(encoding="utf-8")).body:
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if not isinstance(item, ast.FunctionDef) or item.name.startswith("__"):
                    continue
                static = any(isinstance(d, ast.Name) and d.id == "staticmethod" for d in item.decorator_list)
                names = [a.arg for a in item.args.args]
                params = item.args.args[1:] if names and names[0] == "self" and not static else item.args.args
                kinds = [_kind(ast.unparse(a.annotation)) if a.annotation else "any" for a in params]
                found.setdefault((node.name, item.name), []).append(
                    (len(params) - len(item.args.defaults), len(params), kinds)
                )
    return found


def _split_top_level(text: str) -> list[str]:
    parts, depth, current = [], 0, ""
    for char in text:
        depth += char in "([{"
        depth -= char in ")]}"
        if char == "," and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        parts.append(current.strip())
    return parts


def _binary_signatures(docstring: str) -> list[tuple[int, int, list[str]]]:
    signatures = []
    for line in docstring.splitlines():
        match = re.match(r"\s*(?:\d+\.\s*)?\w+\((.*)\)\s*->", line)
        if not match:
            continue
        params = [p for p in _split_top_level(match.group(1)) if not p.startswith("self") and p not in ("*", "/")]
        kinds = [_kind(re.sub(r"^\w+:\s*", "", p).split(" = ")[0]) for p in params]
        signatures.append((sum(" = " not in p for p in params), len(params), kinds))
    return signatures


def _mismatches() -> list[str]:
    problems = []
    for (class_name, method), declared in sorted(_declared_signatures().items()):
        member = getattr(getattr(native, class_name, None), method, None)
        actual = _binary_signatures(getattr(member, "__doc__", "") or "")
        if not actual:
            continue  # absent from the binary: the name test reports it
        if not any(
            d[:2] == a[:2] and all(_compatible(x, y) for x, y in zip(d[2], a[2]))
            for d in declared
            for a in actual
        ):
            problems.append(f"{class_name}.{method}: stub {declared}, binary {actual}")
    return problems


def test_every_stub_signature_matches_the_binary():
    problems = _mismatches()
    assert not problems, (
        "the .pyi describes these methods differently from the binary "
        "(bump the contract version if you fix them: tests/test_bridge_contract_version.py):\n  "
        + "\n  ".join(problems)
    )


def test_the_comparison_sees_what_it_is_for():
    """Guard against a comparison that finds nothing: it must read many signatures,
    and it must tell four floats from four Point2D."""
    assert len(_declared_signatures()) > 150
    assert _compatible("number", "number") and not _compatible("number", "Point2D")
    four_floats = _kind("float"), _kind("float"), _kind("float"), _kind("float")
    four_points = _binary_signatures(
        "set_control_points(self: X, arg0: aladyn_engine_native.Point2D, arg1: aladyn_engine_native.Point2D) -> None"
    )[0][2]
    assert not all(_compatible(a, b) for a, b in zip(four_floats, four_points))
