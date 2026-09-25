"""
test_arccc_cpp_and_docs_governance.py
======================================
Extensao do Guardrail de Governanca ARCcC para a camada nativa (C++).

O teste original `test_arccc_architecture_invariants.py` audita SOMENTE
os modulos Python de `ui/` (com `ui/plugins/`) e `tests/` (ver seu `test_05_...`,
teto de linhas). O nucleo nativo do ALADYN ENGINE (`engine/` e `bridge/`)
fica fora de qualquer guardrail automatizado de LOC ou consistencia
documental -- o que permitiu que:

  - engine/boundary/public-api/PaintEngineFacade.cpp        (652 LOC)
  - engine/boundary/orchestrator/StrokeOrchestrator.cpp (460 LOC; então em public-api/internal/)

ultrapassassem o teto sem que nenhum teste os acusasse, mesmo com a
suite 100% GREEN.

Este modulo fecha essa lacuna:
  1. Teto estrito de LOC (mesmo limite numerico do teste Python) aplicado
     a todos os arquivos .cpp/.hpp/.h/.cc/.cxx de engine/ e bridge/.
  2. Consistencia documental: a versao do padrao C++ declarada em
     AGENTS.md e docs/05-visao-e-futuro/01-visao-estrategica.md deve bater.
     (ARCHITECTURE.md foi removido em 2026-09-20; a checagem ignora
     arquivos ausentes, entao so restam esses dois hoje.)
"""

import os
import re
import sys
import unittest
from typing import List, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Mantenha sincronizado com
# test_arccc_architecture_invariants.TestARCcCArchitectureInvariants.test_05_strict_loc_ceiling_compliance
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arccc_governance_rules import (  # noqa: E402
    MAX_LINES_ERROR,
    MAX_LINES_WALL,
    exception_reason,
    is_declared_exception,
)


class TestARCcCNativeGovernance(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.root = PROJECT_ROOT
        cls.engine_dir = os.path.join(cls.root, 'engine')
        cls.bridge_dir = os.path.join(cls.root, 'bridge')

    def _get_native_files(self, base_dir: str) -> List[str]:
        native_files = []
        if not os.path.isdir(base_dir):
            return native_files
        for dirpath, _, filenames in os.walk(base_dir):
            if any(x in dirpath for x in ('.git', 'build', '__pycache__', 'scratch')):
                continue
            for f in filenames:
                if f.endswith(('.cpp', '.hpp', '.h', '.cc', '.cxx')):
                    native_files.append(os.path.join(dirpath, f))
        return native_files

    def test_01_strict_loc_ceiling_native_engine(self):
        """[ARCcC Nativo] Teto estrito de LOC tambem vale para engine/ e bridge/ (C++)."""
        violations: List[Tuple[str, int]] = []
        exempted: List[Tuple[str, int, str]] = []
        for tdir in (self.engine_dir, self.bridge_dir):
            for fpath in self._get_native_files(tdir):
                rel = os.path.relpath(fpath, self.root)
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as fl:
                    loc = sum(1 for _ in fl)
                # Excecoes formais vivem em arccc_governance_rules.py, espelhando
                # o perfil `lumenia` do Navigator. Sem esse mecanismo este teste
                # reprovava PaintEngineFacade.cpp (652 linhas), que tem excecao
                # declarada — o teste estava vermelho por construcao.
                if loc >= MAX_LINES_ERROR and not is_declared_exception(rel):
                    violations.append((rel, loc))
                elif loc >= MAX_LINES_ERROR:
                    exempted.append((rel, loc, exception_reason(rel)))

        msg = (
            f"Encontrados {len(violations)} arquivo(s) nativo(s) violando o teto "
            f"da Zona Vermelha ARCcC ({MAX_LINES_ERROR} LOC):\n" +
            "\n".join(f"  - {v[0]}: {v[1]} LOC" for v in sorted(violations, key=lambda x: x[1], reverse=True))
        )
        self.assertEqual(len(violations), 0, msg)

    def test_01b_no_native_file_on_the_wall(self):
        """[ARCcC Nativo] Parede dos 450: nenhum .cpp/.hpp entre 430 e 449 linhas."""
        on_the_wall = []
        for tdir in (self.engine_dir, self.bridge_dir):
            for fpath in self._get_native_files(tdir):
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as fl:
                    loc = sum(1 for _ in fl)
                if MAX_LINES_WALL <= loc < MAX_LINES_ERROR:
                    on_the_wall.append(f"{os.path.relpath(fpath, self.root)}: {loc}")
        self.assertEqual(on_the_wall, [], "divida por responsabilidade antes de crescer: " + ", ".join(on_the_wall))

    def test_02_cpp_standard_version_consistency(self):
        """[ARCcC Documental] A versao do padrao C++ deve ser identica em toda a documentacao canonica."""
        docs_to_check = ['AGENTS.md', os.path.join('docs', '05-visao-e-futuro', '01-visao-estrategica.md')]
        pattern = re.compile(r'C\+\+\s*(1[4-9]|2[0-9])')

        found_versions = {}
        for doc in docs_to_check:
            path = os.path.join(self.root, doc)
            if not os.path.isfile(path):
                continue
            with open(path, 'r', encoding='utf-8', errors='ignore') as fl:
                content = fl.read()
            versions = sorted(set(pattern.findall(content)))
            if versions:
                found_versions[doc] = versions

        all_versions = set()
        for versions in found_versions.values():
            all_versions.update(versions)

        msg = (
            f"Inconsistencia na versao do padrao C++ declarada entre documentos: {found_versions}. "
            "Escolha uma unica versao de referencia (ex: a que scripts/build_native.py realmente "
            "usa via /std:c++NN ou -std=c++NN) e alinhe todos os documentos canonicos."
        )
        self.assertLessEqual(len(all_versions), 1, msg)


if __name__ == '__main__':
    unittest.main()
