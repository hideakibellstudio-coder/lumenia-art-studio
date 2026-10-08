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
PARENT_BUILD = ROOT.parent / "build"
# Se existir uma pasta 'build' externa ou se estivermos na raiz do repositório limpo, usa out-of-tree
DEFAULT_BUILD_DIR = PARENT_BUILD if (PARENT_BUILD.exists() or ROOT.parent.name.endswith("CLEAN")) else (ROOT / "build")


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


def write_build_metadata(simd: str, build_dir: Path = DEFAULT_BUILD_DIR, pdb_dir: Path | None = None) -> Path:
    output = build_dir / "native-build.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata = artifact_metadata(simd)
    if pdb_dir is not None:
        metadata["pdb_file"] = str(keep_pdb(pdb_dir, metadata["extension_sha256"]))
    output.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return output


def keep_pdb(pdb_dir: Path, extension_sha256: str) -> Path:
    """Names the PDB after the binary it describes: a crash dump is matched to it by that hash."""
    produced = pdb_dir / "aladyn_engine_native.pdb"
    if not produced.is_file():
        raise RuntimeError(f"o link não gravou o PDB em {produced}")
    kept = pdb_dir / f"aladyn_engine_native-{extension_sha256[:16]}.pdb"
    produced.replace(kept)
    return kept


def build(simd: str, force: bool, build_dir: Path = DEFAULT_BUILD_DIR, pdb: bool = False) -> None:
    _load_msvc_environment()
    environment = os.environ.copy()
    environment["LUMENIA_SIMD"] = simd
    pdb_dir = build_dir / "pdb" if pdb else None
    if pdb_dir is not None:
        pdb_dir.mkdir(parents=True, exist_ok=True)
        environment["LUMENIA_PDB_DIR"] = str(pdb_dir)
        force = True  # objects compiled without /Zi carry no symbols

    # Redireciona a compilação de temporários para a pasta build externa
    temp_dir = build_dir / "temp_native"
    temp_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "setup.py",
        "build_ext",
        "--inplace",
        f"--build-temp={temp_dir}",
    ]
    if force:
        command.append("--force")
    subprocess.run(command, cwd=ROOT, env=environment, check=True)
    metadata_path = write_build_metadata(simd, build_dir, pdb_dir)
    print(f"Metadados do artefato: {metadata_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compila aladyn_engine_native para Windows x64.")
    parser.add_argument("--simd", choices=("scalar", "avx2"), default="scalar")
    parser.add_argument("--force", action="store_true", help="recompila todos os objetos")
    parser.add_argument("--build-dir", type=Path, default=DEFAULT_BUILD_DIR, help="diretório para artefatos e metadados de build")
    parser.add_argument("--pdb", action="store_true",
                        help="grava o PDB (símbolos) em <build-dir>/pdb para ler minidumps de queda (build de release)")
    args = parser.parse_args()
    build(args.simd, args.force, args.build_dir, args.pdb)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
