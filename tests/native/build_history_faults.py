"""Build the native fault harness with the same compiler family as the extension."""
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

OUT = DEFAULT_BUILD_DIR / "history-faults"
BINARY = OUT / ("history_faults.exe" if os.name == "nt" else "history_faults")
SOURCES = [
    "tests/native/history_faults.cpp",
    "engine/core/canvas/Tile.cpp", "engine/core/canvas/TileGrid.cpp",
    "engine/core/canvas/SpatialCuller.cpp", "engine/core/history/TileUndoManager.cpp",
    "engine/core/history/TileHistoryRestore.cpp", "engine/infrastructure/storage/ScratchDiskManager.cpp",
    "engine/infrastructure/compression/Lz4Codec.cpp", "engine/core/document/LayerStack.cpp",
    "engine/core/document/LayerMerger.cpp", "engine/core/document/FilterLayer.cpp",
    "engine/core/document/Compositor.cpp",
    "engine/core/document/CompositeRegionSupport.cpp",
    "engine/core/document/filters/FilterApplier.cpp",
    "engine/core/document/filters/PointFilters.cpp",
    "engine/core/document/filters/AreaFilters.cpp",
]


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    inputs = [Path(__file__)] + [ROOT / name for name in SOURCES] + sorted((ROOT / "engine").rglob("*.hpp"))
    digest = hashlib.sha256(b"".join(path.read_bytes() for path in inputs)).hexdigest()
    stamp = OUT / "source.sha256"
    binary = BINARY
    if binary.exists() and stamp.exists() and stamp.read_text() == digest:
        return
    if os.name == "nt" and not shutil.which("cl.exe"):
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
    compiler = new_compiler()
    customize_compiler(compiler)
    if os.name == "nt":
        compiler.initialize()
    flags = ["/std:c++20", "/EHsc", "/O2"] if os.name == "nt" else ["-std=c++20", "-O2"]
    if os.environ.get("LUMENIA_SIMD", "scalar").strip().lower() == "avx2" and os.name == "nt":
        flags.append("/arch:AVX2")
    objects = compiler.compile(SOURCES, output_dir=str(OUT), include_dirs=[str(ROOT)], extra_postargs=flags)
    # target_lang="c++": no Linux/macOS o linker padrão do distutils é o de C,
    # que não traz a libstdc++ (falhava com dezenas de símbolos indefinidos).
    compiler.link_executable(objects, str(OUT / "history_faults"), target_lang="c++")
    stamp.write_text(digest)


if __name__ == "__main__":
    os.chdir(ROOT)
    build()
