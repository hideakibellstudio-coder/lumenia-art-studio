"""
ui.infrastructure.bridge_client — Cliente Canônico de Comunicação com a Bridge (ARCcC).
========================================================================================
Ponto oficial de saída do Pilar 1 (UI) em direção à Bridge / Motor Nativo C++.
"""

from .client import BridgeClient, BridgePointerEvent

# Até 2026-09-24 este pacote reexportava `AladynBackend` (o motor concreto).
# Ninguém importava daqui, e a casca não deve conhecer motor concreto:
# só `ui/engine_backends` conhece (ver ui/core/engine/README).
__all__ = ["BridgeClient", "BridgePointerEvent"]
