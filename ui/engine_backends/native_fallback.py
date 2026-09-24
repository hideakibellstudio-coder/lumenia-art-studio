"""Plano B para binário nativo desatualizado -- nunca em silêncio.

Contexto (2026-09-23): as guardas ``hasattr(self._facade, "x")`` existiam para o
caso "atualizei o Python mas ainda não recompilei o motor". O problema é que o
plano B entrava calado: a prévia nativa do pincel sumiu do binário em 25/08 e a
UI passou 4 semanas mostrando uma aproximação sem ninguém notar.

``nativo_tem`` mantém o plano B, mas registra UM aviso por método (por processo)
dizendo o que o usuário perde e como resolver. Toda chamada nova precisa entrar
em ``GUARDAS_COM_AVISO`` (tests/test_river_ratchets.py).
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("ui.engine_backends.native")

DICA_RECOMPILAR = "Recompile o motor: python scripts/build_native.py --simd scalar"

_avisados: set[str] = set()


def nativo_tem(alvo: Any, metodo: str, consequencia: str) -> bool:
    """True se o objeto nativo expõe ``metodo``.

    Se não expõe, devolve False (o chamador segue o plano B) e registra um
    WARNING na primeira vez que o método falta, com ``consequencia`` explicando
    o que deixa de funcionar.
    """
    if hasattr(alvo, metodo):
        return True
    if metodo not in _avisados:
        _avisados.add(metodo)
        logger.warning(
            "Motor nativo desatualizado: o .pyd carregado não tem '%s' -- %s. %s",
            metodo, consequencia, DICA_RECOMPILAR,
        )
    return False


def _esquecer_avisos() -> None:
    """Só para testes: permite verificar o aviso de novo."""
    _avisados.clear()
