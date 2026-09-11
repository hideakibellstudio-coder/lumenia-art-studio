"""Build and verify the portable Lumenia distribution with Nuitka."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tomllib


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "build" / "portable"


def project_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as project_file:
        return str(tomllib.load(project_file)["project"]["version"])


def _native_extension() -> Path:
    extensions = sorted(ROOT.glob("aladyn_engine_native*.pyd"))
    if len(extensions) != 1:
        raise RuntimeError("compile o motor nativo antes de empacotar: esperado um aladyn_engine_native*.pyd")
    return extensions[0]


def nuitka_command(output_dir: Path = DEFAULT_OUTPUT) -> list[str]:
    """Return the exact build command without modifying the workspace."""
    native_extension = _native_extension()
    theme_dir = ROOT / "ui" / "core" / "theme" / "themes"
    required = (ROOT / "assets", ROOT / "plugins", theme_dir, ROOT / "main.py")
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"recursos de distribuição ausentes: {', '.join(missing)}")
    return [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--enable-plugin=pyside6",
        "--windows-disable-console",
        "--windows-company-name=Lumenia Team",
        "--windows-product-name=Lumenia",
        f"--windows-product-version={project_version()}.0",
        f"--windows-file-version={project_version()}.0",
        "--output-filename=Lumenia.exe",
        f"--output-dir={output_dir}",
        "--include-package=ui",
        "--include-package=plugins",
        f"--include-data-dir={ROOT / 'assets'}=assets",
        f"--include-data-dir={ROOT / 'plugins'}=plugins",
        f"--include-data-dir={theme_dir}=ui/core/theme/themes",
        f"--include-data-files={native_extension}=.",
        f"--include-data-files={ROOT / 'Enviar_Feedback.html'}=Enviar_Feedback.html",
        f"--include-data-files={ROOT / 'TERMS_AND_LICENSE.txt'}=TERMS_AND_LICENSE.txt",
        str(ROOT / "main.py"),
    ]


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


def verify_distribution(output_dir: Path) -> Path:
    distributions = sorted(path for path in output_dir.glob("*.dist") if path.is_dir())
    if len(distributions) != 1:
        raise RuntimeError("o Nuitka deve produzir exatamente uma pasta *.dist")
    distribution = distributions[0]
    required = (
        distribution / "Lumenia.exe",
        distribution / _native_extension().name,
        distribution / "assets",
        distribution / "plugins",
        distribution / "ui" / "core" / "theme" / "themes",
    )
    missing = [str(path.relative_to(distribution)) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"pacote portátil incompleto: {', '.join(missing)}")
    write_release_manifest(distribution)
    return distribution


def build(output_dir: Path = DEFAULT_OUTPUT) -> Path:
    command = nuitka_command(output_dir)
    subprocess.run(command, cwd=ROOT, check=True)
    return verify_distribution(output_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gera a distribuição portátil Lumenia com Nuitka.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dry-run", action="store_true", help="mostra o comando sem compilar")
    args = parser.parse_args(argv)
    command = nuitka_command(args.output)
    if args.dry_run:
        print(subprocess.list2cmdline(command))
        return 0
    distribution = build(args.output)
    print(f"Pacote portátil validado: {distribution}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
