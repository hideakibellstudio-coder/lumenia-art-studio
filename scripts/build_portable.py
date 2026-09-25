"""Build and verify the portable Lumenia distribution with Nuitka."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib


ROOT = Path(__file__).resolve().parents[1]
PARENT_BUILD = ROOT.parent / "build"
PARENT_DIST = ROOT.parent / "dist"
# Out-of-tree build default: se existir pasta build/dist externa, usa ROOT.parent
DEFAULT_OUTPUT = (PARENT_BUILD / "portable") if (PARENT_BUILD.exists() or ROOT.parent.name.endswith("CLEAN")) else (ROOT / "build" / "portable")
NOTICES = ROOT / "assets" / "legal" / "THIRD_PARTY_NOTICES.txt"
# Pacotes distribuídos que trazem o texto da licença (e o das bibliotecas que
# embutem) nos metadados instalados. O PySide6 não traz: a LGPLv3 e a GPLv3
# estão em assets/legal/. Pacote novo na distribuição entra aqui e em NOTICES.
LICENSED_PACKAGES = ("Pillow", "numpy", "scipy", "pybind11")
LICENSE_NAME = re.compile(r"LICEN[CS]E|COPYING|NOTICE", re.IGNORECASE)


def project_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as project_file:
        return str(tomllib.load(project_file)["project"]["version"])


def _native_extension() -> Path:
    extensions = sorted(ROOT.glob("aladyn_engine_native*.pyd"))
    if len(extensions) != 1:
        raise RuntimeError("compile o motor nativo antes de empacotar: esperado um aladyn_engine_native*.pyd")
    return extensions[0]


def _runtime_package_data(package_name: str) -> list[str]:
    """Return data inclusions for binary scientific packages kept as runtime code."""
    spec = importlib.util.find_spec(package_name)
    if spec is None or not spec.submodule_search_locations:
        raise RuntimeError(f"pacote de runtime ausente: {package_name}")
    package_dir = Path(next(iter(spec.submodule_search_locations)))
    if not any(path.is_file() for path in package_dir.iterdir()):
        raise RuntimeError(f"pacote de runtime vazio: {package_name}")
    includes = [f"--include-data-files={package_dir}={package_name}/=**/*.*"]
    libraries = package_dir.with_name(package_name + ".libs")
    if libraries.is_dir():
        includes.append(f"--include-data-files={libraries}={libraries.name}/=**/*.*")
    return includes


def nuitka_command(output_dir: Path | None = None) -> list[str]:
    """Return the exact build command without modifying the workspace."""
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT
    _native_extension()  # falha cedo se o motor nativo não foi compilado
    theme_dir = ROOT / "ui" / "infrastructure" / "theme" / "themes"
    required = (ROOT / "assets", ROOT / "ui" / "plugins", theme_dir, ROOT / "main.py", NOTICES)
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"recursos de distribuição ausentes: {', '.join(missing)}")
    command = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--enable-plugin=pyside6",
        "--windows-console-mode=disable",
        "--windows-company-name=Lumenia Team",
        "--windows-product-name=Lumenia",
        f"--windows-product-version={project_version()}.0",
        f"--windows-file-version={project_version()}.0",
        "--output-filename=Lumenia.exe",
        f"--output-dir={output_dir}",
        "--include-package=ui",
        "--include-package=ui.plugins",  # pastas de agrupamento sem __init__ (namespace)
        "--include-module=aladyn_engine_native",
        "--nofollow-import-to=numpy",
        "--nofollow-import-to=scipy",
        f"--include-data-dir={ROOT / 'assets'}=assets",
        f"--include-data-dir={theme_dir}=ui/infrastructure/theme/themes",
        f"--include-data-files={ROOT / 'Send_Feedback.html'}=Send_Feedback.html",
        f"--include-data-files={ROOT / 'TERMS_AND_LICENSE.txt'}=TERMS_AND_LICENSE.txt",
        f"--include-data-files={NOTICES}=THIRD_PARTY_NOTICES.txt",
        str(ROOT / "main.py"),
    ]
    return command[:-1] + _runtime_package_data("numpy") + _runtime_package_data("scipy") + command[-1:]


def write_release_manifest(distribution_dir: Path) -> Path:
    files = []
    for item in sorted(distribution_dir.rglob("*")):
        if item.is_file() and item.name != "release-manifest.json":
            files.append({
                "path": item.relative_to(distribution_dir).as_posix(),
                "bytes": item.stat().st_size,
                "sha256": hashlib.sha256(item.read_bytes()).hexdigest(),
            })
    manifest = {
        "schema_version": 1,
        "product": "Lumenia",
        "version": project_version(),
        "files": files,
    }
    output = distribution_dir / "release-manifest.json"
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return output


def copy_third_party_licenses(distribution_dir: Path, packages: tuple[str, ...] | None = None) -> list[Path]:
    """Copy each bundled package's license texts to licenses/<package>/ (plus Python's)."""
    copied = []
    for name in LICENSED_PACKAGES if packages is None else packages:
        try:
            package = importlib.metadata.distribution(name)
        except importlib.metadata.PackageNotFoundError as exc:
            raise RuntimeError(f"pacote distribuído sem metadados de licença: {name}") from exc
        texts = [f for f in package.files or () if ".dist-info/" in f.as_posix() and LICENSE_NAME.search(f.name)]
        if not texts:
            raise RuntimeError(f"{name} {package.version} não traz o texto da licença nos metadados")
        for text in texts:
            relative = text.as_posix().split(".dist-info/", 1)[1].removeprefix("licenses/")
            target = distribution_dir / "licenses" / name / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(package.locate_file(text), target)
            copied.append(target)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.is_file():
        target = distribution_dir / "licenses" / "Python" / "LICENSE.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(python_license, target)
        copied.append(target)
    return copied


def _canonical_distribution(output_dir: Path) -> Path:
    distributions = sorted(path for path in output_dir.glob("*.dist") if path.is_dir())
    if len(distributions) != 1:
        raise RuntimeError("o Nuitka deve produzir exatamente uma pasta *.dist")
    distribution = distributions[0]
    expected = output_dir / "Lumenia.dist"
    if distribution != expected:
        if expected.exists():
            raise RuntimeError("já existe uma distribuição Lumenia.dist no diretório de saída")
        distribution.replace(expected)
        distribution = expected
    return distribution


def verify_distribution(output_dir: Path = DEFAULT_OUTPUT) -> Path:
    distribution = _canonical_distribution(output_dir)
    executable = distribution / "Lumenia.exe"
    if not executable.is_file():
        raise RuntimeError(f"executável ausente na distribuição: {executable}")
    bundled_native = distribution / "aladyn_engine_native.pyd"
    if not bundled_native.is_file():
        source_native = _native_extension()
        shutil.copy2(source_native, bundled_native)
    copy_third_party_licenses(distribution)
    write_release_manifest(distribution)
    return distribution


def build_portable(output_dir: Path = DEFAULT_OUTPUT) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    command = nuitka_command(output_dir)
    subprocess.run(command, cwd=ROOT, check=True)
    distribution = verify_distribution(output_dir)
    return distribution


def main() -> int:
    parser = argparse.ArgumentParser(description="Compila a distribuição portátil do Lumenia via Nuitka.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="diretório de saída da distribuição")
    args = parser.parse_args()
    build_portable(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
