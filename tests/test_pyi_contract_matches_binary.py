"""
test_pyi_contract_matches_binary.py
====================================
Regressao para F-024/3.3: garante que bridge/boundary/contracts/aladyn_engine_native.pyi
descreve exatamente a superficie do modulo nativo compilado, nas duas direcoes.

Contexto (docs/historico/estado-da-base-2026-09-15.md, item 3.3): em 2026-09-15
havia 63 metodos expostos pelo binario e nao declarados no .pyi -- o contrato
que a UI e as ferramentas de tipo leem estava incompleto, e nada detectava
regressao. Verificacao manual em 2026-09-20 mostrou o problema corrigido na
pratica; este teste formaliza a checagem para que nunca mais precise ser
manual.

Duas direcoes verificadas:
  1. Metodo existe no binario mas nao esta declarado no .pyi -- superficie
     nao tipada, o risco original documentado.
  2. Metodo declarado no .pyi mas ausente do binario -- contrato morto,
     que engana quem le o stub (caso real corrigido nesta mesma sessao:
     get_pixel_data_size / get_display_pixel_data_size).

Dunder methods (__init__, __repr__, etc.) sao ignorados dos dois lados: sao
gerados implicitamente pelo pybind11 e nao fazem parte da superficie que
este teste audita.
"""

import ast
import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import aladyn_engine_native as native  # noqa: E402

PYI_PATH = os.path.join(
    PROJECT_ROOT, "bridge", "boundary", "contracts", "aladyn_engine_native.pyi"
)


def _parse_pyi_classes(pyi_path):
    """Extrai {nome_da_classe: {metodos declarados}} de um arquivo .pyi via AST.

    Usa o modulo ast em vez de regex: um stub .pyi e Python valido (corpo
    ``...``), entao o parser da linguagem e mais confiavel que casar texto
    por indentacao.
    """
    with open(pyi_path, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=pyi_path)

    classes = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        methods = set()
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not (item.name.startswith("__") and item.name.endswith("__")):
                    methods.add(item.name)
        classes[node.name] = methods
    return classes


class TestPyiContractMatchesBinary(unittest.TestCase):
    """O .pyi de aladyn_engine_native deve descrever exatamente o binario compilado."""

    @classmethod
    def setUpClass(cls):
        cls.pyi_classes = _parse_pyi_classes(PYI_PATH)

    def test_pyi_declara_pelo_menos_uma_classe(self):
        self.assertTrue(
            self.pyi_classes,
            f"Nenhuma classe encontrada em {PYI_PATH} -- parser ou arquivo quebrado.",
        )

    def test_nenhum_metodo_do_binario_falta_no_pyi(self):
        """A direcao original do F-024: superficie nao tipada / nao declarada."""
        problemas = []
        for cls_name, pyi_methods in self.pyi_classes.items():
            native_cls = getattr(native, cls_name, None)
            if native_cls is None:
                problemas.append(f"{cls_name}: declarada no .pyi mas ausente do binario")
                continue
            native_methods = {
                m
                for m in dir(native_cls)
                if not m.startswith("_")
            }
            faltando = sorted(native_methods - pyi_methods)
            if faltando:
                problemas.append(
                    f"{cls_name}: {len(faltando)} metodo(s) no binario sem declaracao no .pyi: {faltando}"
                )
        self.assertFalse(
            problemas,
            "Contrato .pyi incompleto -- rode scripts/build_native.py e "
            "atualize bridge/boundary/contracts/aladyn_engine_native.pyi:\n"
            + "\n".join(problemas),
        )

    def test_nenhum_metodo_do_pyi_esta_ausente_do_binario(self):
        """Contrato morto: .pyi promete algo que o binario atual nao tem."""
        problemas = []
        for cls_name, pyi_methods in self.pyi_classes.items():
            native_cls = getattr(native, cls_name, None)
            if native_cls is None:
                continue
            native_methods = {
                m
                for m in dir(native_cls)
                if not m.startswith("_")
            }
            sobrando = sorted(pyi_methods - native_methods)
            if sobrando:
                problemas.append(
                    f"{cls_name}: {len(sobrando)} metodo(s) declarado(s) no .pyi mas ausente(s) do binario: {sobrando}"
                )
        self.assertFalse(
            problemas,
            "Contrato .pyi com declaracoes mortas -- remova do .pyi o que nao "
            "existe mais no binario:\n" + "\n".join(problemas),
        )


if __name__ == "__main__":
    unittest.main()
