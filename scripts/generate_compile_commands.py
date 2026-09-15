"""
generate_compile_commands.py
=============================
Gera compile_commands.json capturando as invocacoes reais do MSVC (cl.exe)
durante 'python setup.py build_ext --inplace', sem migrar o projeto para
CMake nem tocar em build_native.py.

Fecha F-022 de docs/audit/PRE_FEATURE_FREEZE_AUDIT.md: sem esse arquivo, o
ARCcC Navigator resolve simbolos C++ por heuristica e qualquer chamada que
nao consiga casar com certeza vira 'dynamic_dispatch_risk' (causa provavel
da maioria dos achados 'suspicious' no `verify`).

v2: a v1 interceptava distutils.ccompiler.CCompiler.spawn, que em versoes
recentes do setuptools (vendorizacao reorganizada em compilers/C/*, usada
por padrao em Python 3.12+/3.14 sem distutils na stdlib) pode nao ser mais
o metodo realmente chamado — resultado: compile_commands.json vazio ("[]").
Esta versao intercepta em subprocess.Popen.__init__, a camada mais baixa por
onde qualquer invocacao de processo passa, independente de como o setuptools
organiza o compilador por cima. Mantem o patch de CCompiler.spawn tambem,
sem custo, como rede de seguranca adicional.

v3: v2 tambem deu 0 entradas, o que descarta "API errada" como explicacao —
algo mais fundamental esta acontecendo. Adicionado --debug-log para registrar
CADA subprocess.Popen chamado durante o build, nao so os que parecem cl.exe.

v4: o --debug-log revelou a causa real — as chamadas de cl.exe SEMPRE foram
capturadas certinho (por CCompiler.spawn e por subprocess.Popen), o problema
era so a extracao do nome do arquivo-fonte: o MSVC passa o arquivo como
'/Tpbridge/core/bindings/bind_canvas.cpp' (prefixo /Tp colado, sem espaco,
para forcar compilacao C++), e o filtro antigo descartava qualquer argumento
comecando com '/' — exatamente o caso do /Tp. Corrigido em _find_source_arg.

Uso (equivalente a scripts/build_native.py, mas gerando o compile database):
    python scripts/generate_compile_commands.py --simd scalar --force --debug-log debug.txt

O arquivo e escrito FORA da arvore de codigo, em ../build/compile_commands.json
(mesma pasta out-of-tree que build_native.py ja usa para objetos .obj),
respeitando a Zero-Dirt Policy do AGENTS.md.
"""
from __future__ import annotations

import argparse
import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent

sys.path.insert(0, str(SCRIPTS_DIR))
import build_native  # noqa: E402  (scripts/build_native.py — reaproveita ambiente MSVC e pasta out-of-tree)

_captured: list[dict] = []
_seen_keys: set[tuple] = set()
_debug_log_path: Path | None = None
_debug_count = 0

_SOURCE_EXTS = (".cpp", ".cc", ".cxx", ".c")


def _debug(line: str) -> None:
    global _debug_count
    if _debug_log_path is None:
        return
    _debug_count += 1
    with open(_debug_log_path, "a", encoding="utf-8") as fl:
        fl.write(line.rstrip("\n") + "\n")


def _find_source_arg(args: list[str]) -> str | None:
    for a in args:
        if not isinstance(a, str):
            continue
        low = a.lower()
        # MSVC: /Tp<path> forca compilacao como C++, /Tc<path> como C — prefixo colado, sem espaco.
        if low.startswith("/tp") or low.startswith("/tc"):
            candidate = a[3:]
            if candidate.lower().endswith(_SOURCE_EXTS):
                return candidate
        if low.endswith(_SOURCE_EXTS) and not a.startswith(("/", "-")):
            return a
    return None


def _looks_like_cl_invocation(cmd_list: list[str]) -> bool:
    if not cmd_list:
        return False
    first = str(cmd_list[0]).lower()
    if first.endswith("cl.exe") or first == "cl":
        return True
    return any(str(c).lower().endswith("cl.exe") for c in cmd_list)


def _record(cwd: str, cmd_list: list[str]) -> None:
    src = _find_source_arg([str(c) for c in cmd_list])
    if not src:
        return
    src_path = Path(src)
    if not src_path.is_absolute():
        src_path = (Path(cwd) / src_path).resolve()
    key = (str(src_path), tuple(str(c) for c in cmd_list))
    if key in _seen_keys:
        return
    _seen_keys.add(key)
    _captured.append({
        "directory": str(cwd),
        "arguments": [str(c) for c in cmd_list],
        "file": str(src_path),
    })


# --- Camada 1: intercepta subprocess.Popen diretamente (robusto contra
#     qualquer reorganizacao interna do distutils/setuptools) ---------------
_original_popen_init = subprocess.Popen.__init__


def _patched_popen_init(self, args, *a, **kw):
    try:
        cmd_list = list(args) if isinstance(args, (list, tuple)) else [args]
        cwd = kw.get("cwd") or os.getcwd()
        _debug(f"POPEN cwd={cwd} cmd={cmd_list}")
        if _looks_like_cl_invocation(cmd_list):
            _record(str(cwd), cmd_list)
    except Exception as exc:
        _debug(f"POPEN-HOOK-ERROR {exc!r}")
    return _original_popen_init(self, args, *a, **kw)


def _patch_subprocess() -> None:
    subprocess.Popen.__init__ = _patched_popen_init


# --- Camada 2: intercepta CCompiler.spawn tambem, caso exista e seja usado
#     (nao custa nada manter como rede de seguranca adicional) -------------
def _patch_ccompiler_spawn() -> None:
    for modname in (
        "distutils.ccompiler",
        "setuptools._distutils.ccompiler",
        "setuptools._distutils.compilers.C.base",
    ):
        try:
            mod = __import__(modname, fromlist=["*"])
        except ImportError:
            continue
        CCompiler = getattr(mod, "CCompiler", None) or getattr(mod, "Compiler", None)
        if CCompiler is None or getattr(CCompiler, "_arccc_patched", False):
            continue
        original_spawn = getattr(CCompiler, "spawn", None)
        if original_spawn is None:
            continue

        def make_patched(orig, modname=modname):
            def patched_spawn(self, cmd, *a, **kw):
                try:
                    _debug(f"CCOMPILER.SPAWN[{modname}] cmd={list(cmd)}")
                    _record(os.getcwd(), list(cmd))
                except Exception as exc:
                    _debug(f"CCOMPILER-HOOK-ERROR {exc!r}")
                return orig(self, cmd, *a, **kw)
            return patched_spawn

        CCompiler.spawn = make_patched(original_spawn)
        CCompiler._arccc_patched = True
        _debug(f"Patched CCompiler.spawn on {modname}")


def _patch_os_system() -> None:
    original_system = os.system

    def patched_system(command):
        try:
            _debug(f"OS.SYSTEM cwd={os.getcwd()} cmd={command!r}")
            if "cl.exe" in command.lower() or " cl " in command.lower():
                import shlex
                _record(os.getcwd(), shlex.split(command, posix=False))
        except Exception as exc:
            _debug(f"OS-SYSTEM-HOOK-ERROR {exc!r}")
        return original_system(command)

    os.system = patched_system


def build(simd: str, force: bool) -> None:
    build_native._load_msvc_environment()
    os.environ["LUMENIA_SIMD"] = simd

    temp_dir = build_native.DEFAULT_BUILD_DIR / "temp_native"
    temp_dir.mkdir(parents=True, exist_ok=True)

    argv_backup = sys.argv[:]
    cwd_backup = Path.cwd()
    sys.argv = [
        "setup.py", "build_ext", "--inplace",
        f"--build-temp={temp_dir}",
    ]
    if force:
        sys.argv.append("--force")
    try:
        os.chdir(ROOT)
        runpy.run_path(str(ROOT / "setup.py"), run_name="__main__")
    finally:
        sys.argv = argv_backup
        os.chdir(cwd_backup)


def write_compile_commands(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(_captured, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"compile_commands.json escrito em {output} ({len(_captured)} entradas capturadas)")
    if _debug_log_path is not None:
        print(f"Log de diagnostico: {_debug_log_path} ({_debug_count} linhas)")
    if not _captured:
        print(
            "AVISO: 0 entradas capturadas. Se rodou com --debug-log, me mande o "
            "conteudo desse arquivo (ou as primeiras ~40 linhas) para eu ver "
            "exatamente quais processos o build disparou."
        )


def main() -> int:
    global _debug_log_path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simd", choices=("scalar", "avx2"), default="scalar")
    parser.add_argument("--force", action="store_true", help="recompila todos os objetos (recomendado na primeira geracao)")
    parser.add_argument(
        "--output", type=Path,
        default=build_native.DEFAULT_BUILD_DIR / "compile_commands.json",
        help="onde escrever o compile_commands.json (default: pasta out-of-tree ../build)"
    )
    parser.add_argument(
        "--debug-log", type=Path, default=None,
        help="registra TODA invocacao de subprocess/CCompiler.spawn/os.system nesse arquivo, para diagnostico"
    )
    args = parser.parse_args()

    if args.debug_log is not None:
        _debug_log_path = args.debug_log.resolve()
        _debug_log_path.write_text("", encoding="utf-8")  # zera o arquivo
        print(f"Diagnostico ligado, escrevendo em {_debug_log_path}")

    _patch_subprocess()
    _patch_ccompiler_spawn()
    _patch_os_system()
    build(args.simd, args.force)
    write_compile_commands(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
