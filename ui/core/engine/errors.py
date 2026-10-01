"""
ui.core.engine.errors — Exceções padronizadas da camada de motor.
"""


class EngineUnavailableError(RuntimeError):
    """Lançada quando nenhum EngineBackend está disponível/registrado."""


class EngineNotInitializedError(RuntimeError):
    """Lançada quando o backend está registrado mas ainda não foi inicializado
    (ex.: init_renderer ainda não foi chamado com o HWND)."""


class EngineContextError(RuntimeError):
    """O motor não conseguiu criar o contexto de um documento (em geral, falta
    de memória num canvas grande). O contexto que estava ativo continua ativo e
    intacto: quem pediu o novo não pode seguir como se ele existisse.

    `out_of_memory` distingue falta de memória (o que o usuário pode resolver
    fechando documentos) de qualquer outra causa, para a mensagem não mentir."""

    def __init__(self, message: str, *, out_of_memory: bool = False) -> None:
        super().__init__(message)
        self.out_of_memory = out_of_memory
