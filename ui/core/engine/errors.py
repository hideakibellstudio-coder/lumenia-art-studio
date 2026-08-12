"""
ui.core.engine.errors — Exceções padronizadas da camada de motor.
"""


class EngineUnavailableError(RuntimeError):
    """Lançada quando nenhum EngineBackend está disponível/registrado."""


class EngineNotInitializedError(RuntimeError):
    """Lançada quando o backend está registrado mas ainda não foi inicializado
    (ex.: init_renderer ainda não foi chamado com o HWND)."""