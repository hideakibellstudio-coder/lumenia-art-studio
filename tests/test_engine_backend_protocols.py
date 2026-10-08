"""
test_engine_backend_protocols.py
=================================
Prova, em runtime, que os Protocols de ui.core.engine.backend_protocols sao
cortes fieis de EngineBackend E que o backend concreto (AladynBackend)
implementa de fato cada papel.

Por que dois niveis de prova:
    `isinstance(obj, Protocol)` so verifica se o atributo EXISTE. Como
    EngineBackend declara os seus metodos com corpo padrao (retorna None/False),
    qualquer subclasse passaria nesse teste mesmo sem implementar nada -- a
    prova seria vazia. Por isso o segundo teste exige que cada membro de cada
    Protocol seja definido por uma classe DIFERENTE de EngineBackend na MRO do
    backend (o proprio AladynBackend ou um dos seus mixins).

Contexto: docs/01-correcao-da-base/02-simplificacao-da-ponte.md, item 3.6.
O antigo WgpuRustBackend (adaptador do motor Rust arquivado) foi removido em
2026-09-22: nao havia motor por tras dele, so os corpos padrao herdados.
"""

from __future__ import annotations

import unittest

from PySide6.QtWidgets import QApplication

from ui.core.engine.backend import EngineBackend
from ui.core.engine.backend_protocols import (
    BrushProtocol,
    CanvasResourceProtocol,
    ColorProtocol,
    CoreLifecycleProtocol,
    GeometryProtocol,
    HistoryProtocol,
    LayerProtocol,
    RenderPipelineProtocol,
    RuntimeServicesProtocol,
    SelectionTransformProtocol,
    StrokeProtocol,
    TelemetryProtocol,
)
from ui.infrastructure.bridge_client.aladyn import AladynBackend

app = QApplication.instance() or QApplication(["--platform", "offscreen"])

ALL_PROTOCOLS = (
    CoreLifecycleProtocol,
    StrokeProtocol,
    BrushProtocol,
    CanvasResourceProtocol,
    LayerProtocol,
    SelectionTransformProtocol,
    GeometryProtocol,
    TelemetryProtocol,
    ColorProtocol,
    RenderPipelineProtocol,
    HistoryProtocol,
    RuntimeServicesProtocol,
)


def _membros(protocol) -> list[str]:
    return [n for n in vars(protocol) if not n.startswith("_")]


class TestProtocolsSaoCortesDeEngineBackend(unittest.TestCase):
    def test_cada_membro_existe_no_contrato_universal(self):
        for protocol in ALL_PROTOCOLS:
            for nome in _membros(protocol):
                with self.subTest(protocol=protocol.__name__, membro=nome):
                    self.assertIn(nome, vars(EngineBackend))

    def test_os_protocolos_cobrem_o_contrato_inteiro_sem_sobreposicao(self):
        vistos: dict[str, str] = {}
        for protocol in ALL_PROTOCOLS:
            for nome in _membros(protocol):
                self.assertNotIn(nome, vistos, f"{nome} aparece em {vistos.get(nome)} e {protocol.__name__}")
                vistos[nome] = protocol.__name__
        publicos = {
            n for n, v in vars(EngineBackend).items()
            if not n.startswith("_") and (callable(v) or isinstance(v, property))
        }
        self.assertEqual(publicos - set(vistos), set(), "metodos de EngineBackend sem Protocol")


class TestAladynImplementaCadaPapel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.backend = AladynBackend()

    def test_satisfaz_todos_os_protocolos_por_papel(self):
        for protocol in ALL_PROTOCOLS:
            with self.subTest(protocol=protocol.__name__):
                self.assertIsInstance(self.backend, protocol)

    def test_nenhum_membro_depende_do_corpo_padrao_de_engine_backend(self):
        for protocol in ALL_PROTOCOLS:
            for nome in _membros(protocol):
                dono = next(c for c in type(self.backend).__mro__ if nome in vars(c))
                with self.subTest(protocol=protocol.__name__, membro=nome):
                    self.assertIsNot(
                        dono,
                        EngineBackend,
                        f"AladynBackend herda `{nome}` do corpo padrao de EngineBackend "
                        "-- o papel nao esta implementado de verdade.",
                    )


if __name__ == "__main__":
    unittest.main()
