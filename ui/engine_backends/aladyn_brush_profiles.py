"""
AladynBrushProfiles — Serialização e Mapeamento de Parâmetros de Pincel
========================================================================
Converte entre estruturas nativas BrushProfile e dicionários de preset da UI.

Ambos os sentidos derivam de `brush_param_table.BRUSH_PARAMS`. Este módulo não
mantém nenhuma lista própria de chaves: antes eram duas (uma na leitura, outra
na escrita) e elas divergiram — `scatter_radius` e `jitter_opacity` eram
escritas num destino que o motor não tem, e `blend_mode` era lido de um dicionário
que nunca o produzia.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .brush_param_table import (
    METHOD_PARAMS,
    BRUSH_PARAMS,
    native_target,
)

if TYPE_CHECKING:  # apenas para tipagem: evita ciclo de import em runtime
    from ui.core.engine.backend import EngineBackend

logger = logging.getLogger(__name__)

STABILIZER_DEFAULT_PCT = 40.0


def get_brush_profile_dict(facade: Any) -> dict:
    """Lê o estado vivo do motor como dicionário de preset."""
    if not facade:
        return {}
    profile = facade.get_brush_profile()
    if not profile:
        return {}

    values: dict[str, Any] = {}
    for spec in BRUSH_PARAMS:
        if not spec.readable:
            continue
        try:
            target = native_target(profile, spec.group)
        except KeyError:
            # Um grupo declarado na tabela mas ausente do módulo nativo é um
            # erro de contrato, não uma condição normal. test_brush_param_contract
            # falha antes de isto chegar ao usuário; aqui só registramos.
            logger.warning(
                "[AladynBrush] Grupo '%s' ausente do módulo nativo; "
                "'%s' não foi lido.", spec.group, spec.key
            )
            continue
        raw = getattr(target, spec.attribute, spec.default)
        values[spec.key] = spec.to_preset(raw)

    # O estabilizador não mora no BrushProfile: vem do DynamicStabilizer, em
    # porcentagem. O preset guarda peso normalizado (0..1).
    percent = STABILIZER_DEFAULT_PCT
    if facade:
        try:
            percent = float(facade.get_stabilizer().get_stabilization_percentage())
        except Exception:
            logger.debug("[AladynBrush] Estabilizador ilegível; usando padrão.", exc_info=True)
    values["stabilizer_weight"] = percent / 100.0

    return values


def apply_brush_preset_dict(backend: EngineBackend, facade: Any, native: Any, data: dict) -> None:
    """Aplica um dicionário de preset ao motor, campo a campo, pela tabela.

    Só usa a API pública do backend (métodos de METHOD_PARAMS) e a facade
    e o módulo nativo recebidos; não lê nem escreve estado do backend.
    """
    if not data:
        return

    # 1. Parâmetros que passam por um método do backend (não vivem no perfil).
    for method_spec in METHOD_PARAMS:
        if method_spec.key not in data:
            continue
        method = getattr(backend, method_spec.method, None)
        if method is None:
            logger.warning(
                "[AladynBrush] Backend sem método '%s'; '%s' ignorado.",
                method_spec.method, method_spec.key,
            )
            continue
        method(method_spec.converter(data[method_spec.key]))

    # Compatibilidade: presets antigos gravavam "stabilizer" em vez de
    # "stabilizer_weight".
    if "stabilizer_weight" not in data and "stabilizer" in data:
        backend.set_stabilizer_weight(float(data["stabilizer"]))

    # 2. Campos do BrushProfile.
    if not facade:
        return
    profile = facade.get_brush_profile()
    if not profile:
        return

    for spec in BRUSH_PARAMS:
        if spec.key not in data:
            continue
        target = native_target(profile, spec.group)
        setattr(target, spec.attribute, spec.to_engine(data[spec.key], native))
