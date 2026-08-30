#!/usr/bin/env python3
"""
Runner de Testes Padrão Ouro — Project Lumenia Suite
Executa todas as suítes de teste de integração do motor C++ e da interface Python com suporte a UTF-8 no Windows.
"""

import os
import sys
import unittest

# Reconfigura stdout/stderr para UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Força execução em modo headless / offscreen
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Adiciona a raiz do projeto Lumenia ao PATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def main():
    print("=" * 75)
    print(" 🏛️  LUMENIA ART STUDIO & ALADYN ENGINE -- SUÍTE DE TESTES EXECUTIVA")
    print("=" * 75)

    loader = unittest.TestLoader()
    start_dir = os.path.dirname(__file__)
    suite = loader.discover(start_dir, pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 75)
    if result.wasSuccessful():
        print(f" 🟢 [OK] TODOS OS TESTES PASSARAM COM SUCESSO! ({result.testsRun} testes executados)")
        print("=" * 75)
        sys.exit(0)
    else:
        print(f" 🔴 [FALHA] ENCONTRADOS ERROS NOS TESTES! ({len(result.failures)} falhas, {len(result.errors)} erros)")
        print("=" * 75)
        sys.exit(1)


if __name__ == "__main__":
    main()
