"""Build and verify the portable Lumenia distribution with Nuitka."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tomllib


ROOT = Path(__file__).resolve().parents[1]
PARENT_BUILD = ROOT.parent / "build"
PARENT_DIST = ROOT.parent / "dist"
# Out-of-tree build default: se existir pasta build/dist externa, usa ROOT.parent
DEFAULT_OUTPUT = (PARENT_BUILD / "portable") if (PARENT_BUILD.exists() or ROOT.parent.name.endswith("CLEAN")) else (ROOT / "build" / "portable")


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
    native_extension = _native_extension()
    theme_dir = ROOT / "ui" / "core" / "theme" / "themes"
    required = (ROOT / "assets", ROOT / "plugins", theme_dir, ROOT / "main.py")
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
        "--include-package=plugins",
        "--include-module=aladyn_engine_native",
        "--nofollow-import-to=numpy",
        "--nofollow-import-to=scipy",
        f"--include-data-dir={ROOT / 'assets'}=assets",
        f"--include-data-dir={theme_dir}=ui/core/theme/themes",
        f"--include-data-files={ROOT / 'Enviar_Feedback.html'}=Enviar_Feedback.html",
        f"--include-data-files={ROOT / 'TERMS_AND_LICENSE.txt'}=TERMS_AND_LICENSE.txt",
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
