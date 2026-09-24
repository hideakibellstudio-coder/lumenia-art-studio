"""Plano B para binário nativo desatualizado -- nunca em silêncio.

Contexto (2026-09-23): as guardas ``hasattr(self._facade, "x")`` existiam para o
caso "atualizei o Python mas ainda não recompilei o motor". O problema é que o
plano B entrava calado: a prévia nativa do pincel sumiu do binário em 25/08 e a
UI passou 4 semanas mostrando uma aproximação sem ninguém notar.

``native_has`` mantém o plano B, mas registra UM aviso por método (por processo)
dizendo o que o usuário perde e como resolver. Toda chamada nova precisa entrar
em ``WARNED_GUARDS`` (tests/test_river_ratchets.py).
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("ui.engine_backends.native")

REBUILD_HINT = "Recompile o motor: python scripts/build_native.py --simd scalar"

_warned: set[str] = set()


def native_has(target: Any, method: str, consequence: str) -> bool:
    """True se o objeto nativo expõe ``method``.

    Se não expõe, devolve False (o chamador segue o plano B) e registra um
    WARNING na primeira vez que o método falta, com ``consequence`` explicando
    o que deixa de funcionar.
    """
    if hasattr(target, method):
        return True
    if method not in _warned:
        _warned.add(method)
        logger.warning(
            "Motor nativo desatualizado: o .pyd carregado não tem '%s' -- %s. %s",
            method, consequence, REBUILD_HINT,
        )
    return False


def _forget_warnings() -> None:
    """Só para testes: permite verificar o aviso de novo."""
    _warned.clear()
