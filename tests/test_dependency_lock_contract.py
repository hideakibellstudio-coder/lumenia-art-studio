from pathlib import Path
import re


def test_windows_dependency_lock_pins_every_resolved_package_with_hashes():
    lock = Path(__file__).parents[1] / "requirements-dev.lock"
    logical_lines = []
    current = ""
    for line in lock.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        current += stripped.removesuffix("\\").rstrip()
        if stripped.endswith("\\"):
            current += " "
            continue
        logical_lines.append(current)
        current = ""
    assert logical_lines.pop(0) == "--require-hashes"
    names = set()
    for requirement in logical_lines:
        name, _, rest = requirement.partition("==")
        names.add(name)
        assert rest
        hashes = re.findall(r"--hash=sha256:([0-9a-f]{64})", requirement)
        assert hashes, requirement
    # numpy e scipy: scripts/build_portable.py empacota os dois como dados de
    # runtime e falha se não estiverem instalados (CI quebrou assim em 2026-09-24).
    assert {"pyside6", "pybind11", "numpy", "scipy", "pillow", "pytest", "coverage"} <= names
