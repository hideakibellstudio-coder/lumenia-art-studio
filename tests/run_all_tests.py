#!/usr/bin/env python3
"""
Runner de Testes Padrão Ouro — Project Lumenia Suite
Executa todas as suítes de teste de integração do motor C++ e da interface Python com suporte a UTF-8 no Windows.
"""

import argparse
import json
import os
import sys

# Reconfigura stdout/stderr para UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Força execução em modo headless / offscreen
os.environ["QT_QPA_PLATFORM"] = "offscreen"
# Small contract fixtures do not benefit from spawning one OpenMP worker per
# logical CPU. Benchmarks can override this explicitly in their environment.
os.environ.setdefault("OMP_NUM_THREADS", "2")

# Adiciona a raiz do projeto Lumenia ao PATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


SUITE_TARGETS = {
    "smoke": (
        "test_arccc_architecture_invariants.py",
        "test_backend_capabilities.py",
        "test_config_schema.py",
        "test_engine_benchmark_runner.py",
        "test_lowlevel_render_options.py",
        "test_plugin_installation.py",
        "test_shortcut_registry.py",
        "test_tool_settings_contract.py",
    ),
    "contract": (
        "test_arccc_architecture_invariants.py",
        "test_backend_capabilities.py",
        "test_buffer_contract.py",
        "test_config_manager.py",
        "test_config_schema.py",
        "test_dependency_lock_contract.py",
        "test_layer_projection_divergence.py",
        "test_document_serializer_integrity.py",
        "test_document_v2.py",
        "test_lowlevel_blend_modes.py",
        "test_lowlevel_color_profiles.py",
        "test_lowlevel_render_options.py",
        "test_lowlevel_selection_transform.py",
        "test_plugin_installation.py",
        "test_shortcut_registry.py",
        "test_tool_settings_contract.py",
    ),
    "integration": (
        "test_document_history_integration.py",
        "test_geometry_history.py",
        "test_layer_manager_history.py",
        "test_main_window_actions.py",
        "test_mdi_multidoc_lifecycle.py",
        "test_persistence_failures.py",
        "test_plugin_lifecycle.py",
    ),
    "stress": (
        "test_document_format_fuzz.py",
        "test_history_io_failures.py",
        "test_lowlevel_giant_brushes_simd.py",
        "test_lowlevel_memory_scalability.py",
        "test_lowlevel_viewport_lod_antialiasing.py",
        "test_lowlevel_viewport_pipeline.py",
        "test_lowlevel_undo_tile_stress.py",
    ),
}


def build_pytest_args(start_dir: str, suite: str) -> list[str]:
    """Return an explicit, reviewable pytest selection for a quality suite."""
    if suite == "full":
        return [start_dir, "-q"]
    return [*(os.path.join(start_dir, test_file) for test_file in SUITE_TARGETS[suite]), "-q"]


def write_document_coverage() -> tuple[object, str]:
    """Write a portable coverage report for the document state boundary."""
    import coverage

    output = os.path.join(PROJECT_ROOT, "build", "coverage", "document.json")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    session = coverage.Coverage(
        source=[os.path.join(PROJECT_ROOT, "ui", "core", "document")],
        branch=True,
    )
    return session, output


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Executa a malha de qualidade do Lumenia.")
    parser.add_argument(
        "--suite",
        choices=("full", *SUITE_TARGETS),
        default="full",
        help="full coleta toda a suíte; as demais opções executam uma fatia nomeada.",
    )
    parser.add_argument("--coverage", action="store_true", help="grava cobertura do núcleo de documento em build/coverage.")
    parser.add_argument("--coverage-minimum", type=float, default=0.0,
                        help="falha se a cobertura do núcleo de documento ficar abaixo deste percentual.")
    args = parser.parse_args(argv)
    if not 0 <= args.coverage_minimum <= 100:
        parser.error("coverage-minimum deve estar entre 0 e 100")
    print("=" * 75)
    print(f" 🏛️  LUMENIA ART STUDIO & ALADYN ENGINE -- SUÍTE {args.suite.upper()}")
    print("=" * 75)

    start_dir = os.path.dirname(__file__)
    # Pytest collects both unittest.TestCase suites and standalone test
    # functions/classes.  The previous unittest-only runner silently skipped
    # those standalone tests, giving a false green signal.
    try:
        import pytest
    except ImportError:
        print("pytest é obrigatório para a suíte executiva.", file=sys.stderr)
        return 2
    coverage_session = None
    coverage_output = None
    if args.coverage:
        coverage_session, coverage_output = write_document_coverage()
        coverage_session.start()
    try:
        exit_code = pytest.main(build_pytest_args(start_dir, args.suite))
    finally:
        if coverage_session is not None:
            coverage_session.stop()
            coverage_session.save()

    coverage_percent = None
    if coverage_session is not None:
        coverage_session.json_report(outfile=coverage_output, pretty_print=True)
        with open(coverage_output, encoding="utf-8") as report_file:
            coverage_percent = float(json.load(report_file)["totals"]["percent_covered"])
        print(f"Cobertura ui/core/document: {coverage_percent:.2f}% ({coverage_output})")
        if exit_code == 0 and coverage_percent < args.coverage_minimum:
            print(f"Cobertura abaixo do mínimo de {args.coverage_minimum:.2f}%.", file=sys.stderr)
            exit_code = 1

    print("\n" + "=" * 75)
    if exit_code == 0:
        print(" 🟢 [OK] TODOS OS TESTES PASSARAM COM SUCESSO!")
        print("=" * 75)
        try:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.closeAllWindows()
                app.processEvents()
        except Exception:
            pass
        sys.stdout.flush()
        sys.stderr.flush()
        return 0
    else:
        print(f" 🔴 [FALHA] ENCONTRADOS ERROS NOS TESTES! (código {exit_code})")
        print("=" * 75)
        sys.stdout.flush()
        sys.stderr.flush()
        return int(exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
