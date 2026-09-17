"""
ui.infrastructure.bridge_client — Cliente Canônico de Comunicação com a Bridge (ARCcC).
========================================================================================
Ponto oficial de saída do Pilar 1 (UI) em direção à Bridge / Motor Nativo C++.
"""

from .client import BridgeClient, BridgePointerEvent
from ui.engine_backends.aladyn import AladynBackend

__all__ = ["BridgeClient", "BridgePointerEvent", "AladynBackend"]
