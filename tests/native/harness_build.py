"""Build a native C++ test harness with the same compiler family as the extension.

Shared by every executable in tests/native/: each one lists its sources and calls
`build_harness`. The Visual Studio environment lookup lives here once.
"""
from pathlib import Path
import hashlib
import os
import shutil
import subprocess
import sys

from setuptools._distutils.ccompiler import new_compiler
from setuptools._distutils.sysconfig import customize_compiler

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Mesma regra de pasta do build nativo (AGENTS.md: compilação out-of-tree).
from scripts.build_native import DEFAULT_BUILD_DIR  # noqa: E402


def binary_path(name: str) -> Path:
    return DEFAULT_BUILD_DIR / name.replace("_", "-") / (f"{name}.exe" if os.name == "nt" else name)


def _load_visual_studio_environment() -> None:
    if os.name != "nt" or shutil.which("cl.exe"):
        return
    vswhere = Path(os.environ["ProgramFiles(x86)"]) / "Microsoft Visual Studio/Installer/vswhere.exe"
    install = subprocess.check_output([str(vswhere), "-latest", "-products", "*", "-requires",
                                       "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                                       "-property", "installationPath"], text=True).strip()
    vcvars = Path(install) / "VC/Auxiliary/Build/vcvarsall.bat"
    command = f'cmd /d /u /c ""{vcvars}" x64 >nul && set"'
    output = subprocess.check_output(command).decode("utf-16le")
    seen = set()
    for line in output.splitlines():
        name, separator, value = line.partition("=")
        # Some launchers supply both Path and PATH; keep vcvars' first value.
        if name and separator and name.upper() not in seen:
            os.environ[name] = value
            seen.add(name.upper())
    os.environ["DISTUTILS_USE_SDK"] = "1"


def build_harness(name: str, sources: list[str]) -> Path:
    """Compile `sources` (paths from the repository root) into the harness `name`; returns the binary."""
    binary = binary_path(name)
    out = binary.parent
    out.mkdir(parents=True, exist_ok=True)
    inputs = [Path(__file__)] + [ROOT / source for source in sources] + sorted((ROOT / "engine").rglob("*.hpp"))
    digest = hashlib.sha256(b"".join(path.read_bytes() for path in inputs)).hexdigest()
    stamp = out / "source.sha256"
    if binary.exists() and stamp.exists() and stamp.read_text(encoding="utf-8") == digest:
        return binary
    _load_visual_studio_environment()
    compiler = new_compiler()
    customize_compiler(compiler)
    if os.name == "nt":
        compiler.initialize()
    flags = ["/std:c++20", "/EHsc", "/O2"] if os.name == "nt" else ["-std=c++20", "-O2"]
    if os.environ.get("LUMENIA_SIMD", "scalar").strip().lower() == "avx2" and os.name == "nt":
        flags.append("/arch:AVX2")
    objects = compiler.compile(sources, output_dir=str(out), include_dirs=[str(ROOT)], extra_postargs=flags)
    # target_lang="c++": no Linux/macOS o linker padrão do distutils é o de C,
    # que não traz a libstdc++ (falhava com dezenas de símbolos indefinidos).
    compiler.link_executable(objects, str(out / name), target_lang="c++")
    stamp.write_text(digest, encoding="utf-8")
    return binary
