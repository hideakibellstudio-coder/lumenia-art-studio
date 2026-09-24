"""
ui.engine_backends — Factories de Backends de Motor
====================================================
A casca nunca importa um motor concreto. Apenas este pacote conhece backends
específicos e os expõe para o EngineRegistry durante o boot.

Para plugar um motor novo no futuro:
    1. Implemente `BaseEngineBackend` de ui.core.engine.backend;
    2. Adicione a classe aqui (import lazy) e a inclua na lista abaixo;
    3. Registre o backend no EngineRegistry (ex.: via um plugin de sistema).
"""

from typing import List

from ui.core.engine.backend import EngineBackend


def create_backends() -> List[EngineBackend]:
    """Instancia todos os backends de motor disponíveis neste ambiente.

    Backends cujo binário/dependência não existir simplesmente reportam
    `available == False` e são ignorados pelo EngineRegistry.
    """
    backends: List[EngineBackend] = []

    try:
        from ui.engine_backends.aladyn import AladynBackend
        backends.append(AladynBackend())
    except Exception as e:  # pragma: no cover
        import logging
        logging.getLogger(__name__).warning(
            f"[engine_backends] Falha ao preparar AladynBackend: {e}"
        )

    return backends


__all__ = ["create_backends"]