"""
AladynBrushProfiles — Serialização e Mapeamento de Parâmetros de Pincel
========================================================================
Converte entre estruturas nativas BrushProfile e dicionários de preset da UI.

Ambos os sentidos derivam de `brush_param_table.TABELA`. Este módulo não
mantém nenhuma lista própria de chaves: antes eram duas (uma na leitura, outra
na escrita) e elas divergiram — `scatter_radius` e `jitter_opacity` eram
escritas num destino que o motor não tem, e `blend_mode` era lido de um dicionário
que nunca o produzia.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .brush_param_table import (
    PARAMS_POR_METODO,
    TABELA,
    alvo_nativo,
)

if TYPE_CHECKING:  # apenas para tipagem: evita ciclo de import em runtime
    from ui.core.engine.backend import EngineBackend

logger = logging.getLogger(__name__)

STABILIZER_PADRAO_PCT = 40.0


def get_brush_profile_dict(facade: Any) -> dict:
    """Lê o estado vivo do motor como dicionário de preset."""
    if not facade:
        return {}
    perfil = facade.get_brush_profile()
    if not perfil:
        return {}

    dados: dict[str, Any] = {}
    for linha in TABELA:
        if not linha.legivel:
            continue
        try:
            destino = alvo_nativo(perfil, linha.grupo)
        except KeyError:
            # Um grupo declarado na tabela mas ausente do módulo nativo é um
            # erro de contrato, não uma condição normal. test_brush_param_contract
            # falha antes de isto chegar ao usuário; aqui só registramos.
            logger.warning(
                "[AladynBrush] Grupo '%s' ausente do módulo nativo; "
                "'%s' não foi lido.", linha.grupo, linha.chave
            )
            continue
        bruto = getattr(destino, linha.atributo, linha.padrao)
        dados[linha.chave] = linha.para_preset(bruto)

    # O estabilizador não mora no BrushProfile: vem do DynamicStabilizer, em
    # porcentagem. O preset guarda peso normalizado (0..1).
    percentual = STABILIZER_PADRAO_PCT
    if facade:
        try:
            percentual = float(facade.get_stabilizer().get_stabilization_percentage())
        except Exception:
            logger.debug("[AladynBrush] Estabilizador ilegível; usando padrão.", exc_info=True)
    dados["stabilizer_weight"] = percentual / 100.0

    return dados


def apply_brush_preset_dict(backend: EngineBackend, facade: Any, native: Any, data: dict) -> None:
    """Aplica um dicionário de preset ao motor, campo a campo, pela tabela.

    Só usa a API pública do backend (métodos de PARAMS_POR_METODO) e a facade
    e o módulo nativo recebidos; não lê nem escreve estado do backend.
    """
    if not data:
        return

    # 1. Parâmetros que passam por um método do backend (não vivem no perfil).
    for entrada in PARAMS_POR_METODO:
        if entrada.chave not in data:
            continue
        metodo = getattr(backend, entrada.metodo, None)
        if metodo is None:
            logger.warning(
                "[AladynBrush] Backend sem método '%s'; '%s' ignorado.",
                entrada.metodo, entrada.chave,
            )
            continue
        metodo(entrada.conversor(data[entrada.chave]))

    # Compatibilidade: presets antigos gravavam "stabilizer" em vez de
    # "stabilizer_weight".
    if "stabilizer_weight" not in data and "stabilizer" in data:
        backend.set_stabilizer_weight(float(data["stabilizer"]))

    # 2. Campos do BrushProfile.
    if not facade:
        return
    perfil = facade.get_brush_profile()
    if not perfil:
        return

    for linha in TABELA:
        if linha.chave not in data:
            continue
        destino = alvo_nativo(perfil, linha.grupo)
        setattr(destino, linha.atributo, linha.para_motor(data[linha.chave], native))
