"""
test_arccc_architecture_invariants.py
======================================
Guardrail de Governança Arquitetural ARCcC (Atomic Recursive Componentization by Contract).
Testa e bloqueia de forma estática (via AST e inspeção estrutural) qualquer violação de:
1. Cross-plugin imports (um plugin importando de outro plugin irmão).
2. Imports diretos de C++ (aladyn_engine_native) fora de ui/engine_backends/.
3. Acessos a atributos privados de ponteiros/facades nativas (_facade, _native) fora de ui/engine_backends/.
4. Cobertura de métodos canônicos do contrato universal EngineBackend no AladynBackend.
5. Teto estrito de 500 LOC em todos os módulos Python de plugins/, ui/ e tests/.
"""

import ast
import os
import unittest
from typing import List, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestARCcCArchitectureInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = PROJECT_ROOT
        cls.plugins_dir = os.path.join(cls.root, 'plugins')
        cls.ui_dir = os.path.join(cls.root, 'ui')
        cls.tests_dir = os.path.join(cls.root, 'tests')

    def _get_py_files(self, base_dir: str) -> List[str]:
        py_files = []
        for dirpath, _, filenames in os.walk(base_dir):
            if any(x in dirpath for x in ['.git', 'build', '__pycache__', 'scratch']):
                continue
            for f in filenames:
                if f.endswith('.py'):
                    py_files.append(os.path.join(dirpath, f))
        return py_files

    def test_01_no_cross_plugin_imports(self):
        """[ARCcC Regra 1] Plugins devem ser caixas-pretas isoladas; proibido importar de outro plugin."""
        violations: List[Tuple[str, int, str]] = []
        
        for ptype in os.listdir(self.plugins_dir):
            ptype_path = os.path.join(self.plugins_dir, ptype)
            if not os.path.isdir(ptype_path) or ptype in ['__pycache__']:
                continue
            for p_name in os.listdir(ptype_path):
                p_path = os.path.join(ptype_path, p_name)
                if not os.path.isdir(p_path):
                    continue
                
                for fpath in self._get_py_files(p_path):
                    rel = os.path.relpath(fpath, self.root)
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as fl:
                        tree = ast.parse(fl.read(), filename=fpath)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ImportFrom) and node.module:
                            parts = node.module.split('.')
                            if len(parts) >= 3 and parts[0] == 'plugins':
                                imp_plugin = parts[2]
                                if imp_plugin != p_name:
                                    violations.append((rel, node.lineno, node.module))
                        elif isinstance(node, ast.Import):
                            for alias in node.names:
                                parts = alias.name.split('.')
                                if len(parts) >= 3 and parts[0] == 'plugins':
                                    imp_plugin = parts[2]
                                    if imp_plugin != p_name:
                                        violations.append((rel, node.lineno, alias.name))

        msg = f"Encontradas {len(violations)} violacoes de Cross-Plugin Import:\n" + "\n".join(
            f"  - {v[0]}:{v[1]} importa de plugin '{v[2]}'" for v in violations
        )
        self.assertEqual(len(violations), 0, msg)

    def test_02_no_direct_native_cpp_in_ui_or_plugins(self):
        """[ARCcC Regra 2] Nenhum arquivo em plugins/ ou ui/ (exceto ui/engine_backends/) pode importar aladyn_engine_native."""
        violations: List[Tuple[str, int]] = []
        
        target_dirs = [self.plugins_dir, self.ui_dir]
        for tdir in target_dirs:
            for fpath in self._get_py_files(tdir):
                rel = os.path.relpath(fpath, self.root)
                # Permitido unicamente na camada de ponte (ui/engine_backends ou ui/infrastructure/bridge_client)
                if rel.startswith(os.path.join('ui', 'engine_backends')) or rel.startswith(os.path.join('ui', 'infrastructure', 'bridge_client')):
                    continue
                
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as fl:
                    tree = ast.parse(fl.read(), filename=fpath)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module:
                        if 'aladyn_engine_native' in node.module:
                            violations.append((rel, node.lineno))
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            if 'aladyn_engine_native' in alias.name:
                                violations.append((rel, node.lineno))

        msg = f"Encontrados {len(violations)} imports proibidos de aladyn_engine_native em UI/Plugins:\n" + "\n".join(
            f"  - {v[0]}:{v[1]}" for v in violations
        )
        self.assertEqual(len(violations), 0, msg)

    def test_03_no_private_facade_leaks_in_ui_or_plugins(self):
        """[ARCcC Regra 3] UI e Plugins nunca devem acessar atributos privados _facade ou _native."""
        violations: List[Tuple[str, int, str]] = []
        
        target_dirs = [self.plugins_dir, self.ui_dir]
        for tdir in target_dirs:
            for fpath in self._get_py_files(tdir):
                rel = os.path.relpath(fpath, self.root)
                if rel.startswith(os.path.join('ui', 'engine_backends')) or rel.startswith(os.path.join('ui', 'infrastructure', 'bridge_client')):
                    continue
                
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as fl:
                    tree = ast.parse(fl.read(), filename=fpath)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Attribute):
                        if node.attr in ('_facade', '_native'):
                            # Permite se for self._facade ou self._native dentro de uma classe que define
                            is_self = isinstance(node.value, ast.Name) and node.value.id == 'self'
                            if not is_self:
                                violations.append((rel, node.lineno, node.attr))

        msg = f"Encontrados {len(violations)} vazamentos de encapsulamento (_facade / _native):\n" + "\n".join(
            f"  - {v[0]}:{v[1]} acesso a '{v[2]}'" for v in violations
        )
        self.assertEqual(len(violations), 0, msg)

    def test_04_canonical_engine_backend_coverage(self):
        """[ARCcC Regra 4] AladynBackend deve implementar 100% dos métodos canônicos do EngineBackend sem herdar no-ops."""
        import inspect
        from ui.core.engine.backend import EngineBackend
        from ui.engine_backends.aladyn import AladynBackend

        backend = AladynBackend()
        self.assertIsInstance(backend, EngineBackend)

        backend_methods = [
            m for m, _ in inspect.getmembers(EngineBackend, predicate=inspect.isfunction)
            if not m.startswith('_')
        ]

        missing = []
        for m in backend_methods:
            func_backend = getattr(EngineBackend, m)
            func_aladyn = getattr(AladynBackend, m)
            if func_backend is func_aladyn:
                missing.append(m)

        msg = (
            f"AladynBackend falha em implementar {len(missing)} método(s) canônico(s) de EngineBackend:\n"
            + "\n".join(f"  - {m}" for m in missing)
        )
        self.assertEqual(len(missing), 0, msg)

    def test_05_strict_loc_ceiling_compliance(self):
        """[ARCcC Regra 5] Teto estrito de 500 LOC em todos os módulos Python de plugins/, ui/ e tests/."""
        violations: List[Tuple[str, int]] = []
        target_dirs = [self.plugins_dir, self.ui_dir, self.tests_dir]
        for tdir in target_dirs:
            for fpath in self._get_py_files(tdir):
                rel = os.path.relpath(fpath, self.root)
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as fl:
                    loc = sum(1 for _ in fl)
                if loc >= 500:
                    violations.append((rel, loc))

        msg = f"Encontrados {len(violations)} arquivo(s) violando o teto estrito de 500 LOC:\n" + "\n".join(
            f"  - {v[0]}: {v[1]} LOC (limite maximo estrito: 499 LOC)" for v in sorted(violations, key=lambda x: x[1], reverse=True)
        )
        self.assertEqual(len(violations), 0, msg)


if __name__ == '__main__':
    unittest.main()
