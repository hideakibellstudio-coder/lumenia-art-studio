"""
test_engine_backend_protocols.py
=================================
Prova, em runtime, que os Protocols de ui.core.engine.backend_protocols sao
cortes fieis de EngineBackend: cada backend concreto (AladynBackend,
WgpuRustBackend) precisa satisfazer TODOS os protocolos, exatamente como ja
satisfaz o EngineBackend inteiro hoje.

Contexto: docs/01-correcao-da-base/02-simplificacao-da-ponte.md, item 3.6.
Isto nao substitui EngineBackend nem muda nenhum consumidor existente -- prova
que a decomposicao em papeis e estruturalmente correta, para que codigo novo
(sobretudo testes) possa depender so do papel que usa.
"""

from __future__ import annotations

import unittest

from PySide6.QtWidgets import QApplication

from ui.core.engine.backend_protocols import (
    BrushProtocol,
    CanvasResourceProtocol,
    ColorProtocol,
    CoreLifecycleProtocol,
    GeometryProtocol,
    HistoryProtocol,
    LayerProtocol,
    RenderPipelineProtocol,
    SelectionTransformProtocol,
    StrokeProtocol,
    TelemetryProtocol,
)
from ui.engine_backends.aladyn import AladynBackend
from ui.engine_backends.wgpu_rust import WgpuRustBackend

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
)


class TestEngineBackendProtocolsCoverAladyn(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.backend = AladynBackend()

    def test_satisfaz_todos_os_protocolos_por_papel(self):
        for protocol in ALL_PROTOCOLS:
            with self.subTest(protocol=protocol.__name__):
                self.assertIsInstance(
                    self.backend,
                    protocol,
                    f"AladynBackend nao satisfaz {protocol.__name__} -- "
                    "backend_protocols.py esta desatualizado em relacao a "
                    "EngineBackend (regenere a partir da fonte).",
                )


class TestEngineBackendProtocolsCoverWgpuRust(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.backend = WgpuRustBackend()

    def test_satisfaz_todos_os_protocolos_por_papel(self):
        for protocol in ALL_PROTOCOLS:
            with self.subTest(protocol=protocol.__name__):
                self.assertIsInstance(
                    self.backend,
                    protocol,
                    f"WgpuRustBackend nao satisfaz {protocol.__name__} -- "
                    "backend_protocols.py esta desatualizado em relacao a "
                    "EngineBackend (regenere a partir da fonte).",
                )


if __name__ == "__main__":
    unittest.main()
