"""Build the Aladyn extension from a clean Windows developer environment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def _load_msvc_environment() -> None:
    """Load vcvarsall only when the caller did not already configure MSVC."""
    if os.name != "nt" or shutil.which("cl.exe"):
        return
    program_files_x86 = os.environ.get("ProgramFiles(x86)")
    if not program_files_x86:
        raise RuntimeError("Visual Studio não foi configurado e ProgramFiles(x86) não está disponível")
    vswhere = Path(program_files_x86) / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
    if not vswhere.is_file():
        raise RuntimeError("vswhere.exe não encontrado; instale o workload Desktop development with C++")
    install = subprocess.check_output(
        [str(vswhere), "-latest", "-products", "*", "-requires",
         "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"],
        text=True,
    ).strip()
    vcvarsall = Path(install) / "VC" / "Auxiliary" / "Build" / "vcvarsall.bat"
    if not vcvarsall.is_file():
        raise RuntimeError("vcvarsall.bat não encontrado na instalação MSVC selecionada")

    output = subprocess.check_output(
        f'cmd /d /u /c ""{vcvarsall}" x64 >nul && set"'
    ).decode("utf-16le")
    for line in output.splitlines():
        name, separator, value = line.partition("=")
        if name and separator:
            os.environ[name] = value
    os.environ["DISTUTILS_USE_SDK"] = "1"


def artifact_metadata(simd: str) -> dict[str, str]:
    """Describe the binary just produced so a build can be audited later."""
    artifacts = sorted(ROOT.glob("aladyn_engine_native*.pyd"))
    if len(artifacts) != 1:
        raise RuntimeError("O build deve produzir exatamente um artefato aladyn_engine_native*.pyd na raiz")
    artifact = artifacts[0]
    return {
        "schema_version": "1",
        "simd": simd,
        "python_version": sys.version.split()[0],
        "python_abi": sys.implementation.cache_tag,
        "platform": sys.platform,
        "msvc_tools_version": os.environ.get("VCToolsVersion", "unknown"),
        "extension_file": artifact.name,
        "extension_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
    }


def write_build_metadata(simd: str) -> Path:
    output = ROOT / "build" / "native-build.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact_metadata(simd), indent=2) + "\n", encoding="utf-8")
    return output


def build(simd: str, force: bool) -> None:
    _load_msvc_environment()
    environment = os.environ.copy()
    environment["LUMENIA_SIMD"] = simd
    command = [sys.executable, "setup.py", "build_ext", "--inplace"]
    if force:
        command.append("--force")
    subprocess.run(command, cwd=ROOT, env=environment, check=True)
    metadata_path = write_build_metadata(simd)
    print(f"Metadados do artefato: {metadata_path.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compila aladyn_engine_native para Windows x64.")
    parser.add_argument("--simd", choices=("scalar", "avx2"), default="scalar")
    parser.add_argument("--force", action="store_true", help="recompila todos os objetos")
    args = parser.parse_args()
    build(args.simd, args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
