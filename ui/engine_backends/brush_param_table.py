"""
Tabela Única de Parâmetros de Pincel — o motor define, a interface exibe.
=========================================================================
Cada parâmetro é declarado UMA vez: a chave usada por presets e pela interface,
onde o valor mora no módulo nativo, e como convertê-lo nos dois sentidos.

`get_brush_profile_dict`, `apply_brush_preset_dict` e `set_brush_param` derivam
desta tabela. Nenhum deles mantém lista própria — era a existência de quatro
listas paralelas, mantidas à mão, que permitia um controle da interface apontar
para um campo que o motor não tem.

Nada aqui pode ser escrito no escuro: `tests/test_brush_param_contract.py`
percorre a tabela contra o módulo COMPILADO e falha se alguma linha apontar
para um campo inexistente, ou se alguma chamada da interface usar um par
(grupo, parâmetro) que não esteja aqui. Declarar um controle sem o campo
correspondente no motor quebra o teste, não o usuário.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


# ── Conversores ─────────────────────────────────────────────────────────────
# Todos recebem (valor, modulo_nativo) para que os que dependem de um tipo do
# módulo — enums, structs — tenham acesso a ele sem import circular.

def para_float(valor: Any, _native: Any) -> float:
    return float(valor)


def para_int(valor: Any, _native: Any) -> int:
    return int(valor)


def para_bool(valor: Any, _native: Any) -> bool:
    return bool(valor)


def para_blend_mode(valor: Any, native: Any) -> Any:
    """A interface guarda o índice da combo; o motor exige o enum DabBlendMode.

    A faixa é validada aqui, contra `__members__`, ANTES de construir o enum.
    `DabBlendMode(9)` não levanta nada no PyBind11 — devolve um enum com valor
    9, que o motor recebe e usa. Delegar a validação ao construtor deixaria
    passar exatamente o tipo de lixo que esta tabela existe para barrar.
    """
    enum_cls = native.DabBlendMode
    if isinstance(valor, enum_cls):
        return valor
    indice = int(valor)
    membros = list(enum_cls.__members__.values())
    if not 0 <= indice < len(membros):
        raise ValueError(
            f"blend_mode fora da faixa: {indice} "
            f"(o motor declara {len(membros)} modos: "
            f"{', '.join(enum_cls.__members__)})"
        )
    return membros[indice]


def de_enum(valor: Any) -> int:
    return int(valor)


def identidade(valor: Any) -> Any:
    return valor


# ── Onde cada grupo mora dentro do BrushProfile nativo ───────────────────────
# "" é a raiz do perfil. "root" é aceito como sinônimo por compatibilidade com
# as chamadas existentes da interface.

ATRIBUTO_DO_GRUPO: dict[str, str | None] = {
    "": None,
    "root": None,
    "tip": "tip",
    "pencil": "pencil_params",
    "inker": "inker_params",
    "marker": "marker_params",
    "blur": "blur_params",
    "smudge": "smudge_params",
    "watercolor": "watercolor_params",
    "oil": "oil_params",
}


@dataclass(frozen=True)
class ParamDePincel:
    """Uma propriedade do pincel, declarada uma única vez."""

    chave: str                                   # chave de preset / interface
    grupo: str                                   # "" para a raiz do perfil
    atributo: str                                # nome do campo no módulo nativo
    para_motor: Callable[[Any, Any], Any] = para_float
    para_preset: Callable[[Any], Any] = identidade
    padrao: Any = 0.0
    legivel: bool = True                         # entra em get_brush_profile_dict


# ── A tabela ────────────────────────────────────────────────────────────────
# Toda linha aqui foi verificada contra as bindings PyBind11. Campos que a
# interface pedia e o motor não tem (`scatter_radius`, `jitter_opacity`) foram
# REMOVIDOS em vez de mantidos mortos — o motor define, a interface exibe.

TABELA: tuple[ParamDePincel, ...] = (
    # ── Raiz do perfil ──────────────────────────────────────────────────────
    ParamDePincel("brush_size", "", "brush_size", padrao=20.0),
    ParamDePincel("opacity", "", "opacity", padrao=1.0),
    ParamDePincel("hardness", "", "hardness", padrao=0.85),
    ParamDePincel("spacing_factor", "", "spacing_factor", padrao=0.08),
    ParamDePincel("min_size_percent", "", "min_size_percent", padrao=0.0),
    ParamDePincel("min_opacity_percent", "", "min_opacity_percent", padrao=0.0),
    ParamDePincel("pressure_size_enabled", "", "pressure_size_enabled",
                  para_motor=para_bool, padrao=True),
    ParamDePincel("pressure_flow_enabled", "", "pressure_flow_enabled",
                  para_motor=para_bool, padrao=True),
    ParamDePincel("velocity_size_enabled", "", "velocity_size_enabled",
                  para_motor=para_bool, padrao=False),
    ParamDePincel("stroke_taper_enabled", "", "stroke_taper_enabled",
                  para_motor=para_bool, padrao=True),
    ParamDePincel("blend_mode", "", "blend_mode",
                  para_motor=para_blend_mode, para_preset=de_enum, padrao=0),
    ParamDePincel("pressure_to_angle", "", "pressure_to_angle", padrao=0.0),
    ParamDePincel("pressure_to_aspect", "", "pressure_to_aspect", padrao=0.0),
    ParamDePincel("scatter_count", "", "scatter_count",
                  para_motor=para_int, padrao=1),
    ParamDePincel("brush_grain_enabled", "", "brush_grain_enabled",
                  para_motor=para_bool, padrao=False),
    ParamDePincel("brush_grain_scale", "", "brush_grain_scale", padrao=1.0),
    ParamDePincel("brush_grain_contrast", "", "brush_grain_contrast", padrao=1.0),
    ParamDePincel("brush_grain_invert", "", "brush_grain_invert",
                  para_motor=para_bool, padrao=False),

    # ── Geometria da ponta ──────────────────────────────────────────────────
    # Os jitters moram em BrushTip, não num grupo "dynamics". A interface
    # escrevia em "dynamics", que nunca existiu no módulo nativo.
    ParamDePincel("tip_angle", "tip", "angle", padrao=0.0),
    ParamDePincel("tip_aspect", "tip", "aspect_ratio", padrao=1.0),
    ParamDePincel("follow_stroke", "tip", "follow_stroke",
                  para_motor=para_bool, padrao=False),
    ParamDePincel("jitter_size", "tip", "jitter_size", padrao=0.0),
    ParamDePincel("jitter_angle", "tip", "jitter_angle", padrao=0.0),
    ParamDePincel("jitter_position", "tip", "jitter_position", padrao=0.0),

    # ── Parâmetros por mini-motor ───────────────────────────────────────────
    ParamDePincel("pencil_graphite_hardness", "pencil", "graphite_hardness", padrao=0.5),
    ParamDePincel("pencil_tilt_shading", "pencil", "tilt_shading_enabled",
                  para_motor=para_bool, padrao=False),
    ParamDePincel("inker_flow_rate", "inker", "ink_flow_rate", padrao=0.8),
    ParamDePincel("inker_taper_smoothing", "inker", "taper_smoothing", padrao=0.3),
    ParamDePincel("marker_solvent_wetness", "marker", "solvent_wetness", padrao=0.5),
    ParamDePincel("marker_edge_darkening", "marker", "edge_darkening", padrao=0.4),
    ParamDePincel("blur_radius", "blur", "blur_radius", para_motor=para_int, padrao=5),
    ParamDePincel("blur_strength", "blur", "blur_strength", padrao=0.5),
    ParamDePincel("smudge_color_pickup", "smudge", "color_pickup", padrao=0.7),
    ParamDePincel("smudge_mix_ratio", "smudge", "mix_ratio", padrao=0.5),
    ParamDePincel("smudge_stretch", "smudge", "smudge_stretch", padrao=0.8),
    ParamDePincel("watercolor_water_level", "watercolor", "water_level", padrao=0.5),
    ParamDePincel("watercolor_pigment_bleed", "watercolor", "pigment_bleed", padrao=0.5),
    ParamDePincel("watercolor_fringe_intensity", "watercolor", "fringe_intensity", padrao=0.4),
    ParamDePincel("watercolor_granulation", "watercolor", "granulation", padrao=0.3),
    ParamDePincel("oil_impasto_depth", "oil", "impasto_depth", padrao=0.7),
    ParamDePincel("oil_bristle_grooves", "oil", "bristle_grooves", padrao=0.5),
    ParamDePincel("oil_viscosity", "oil", "viscosity", padrao=0.6),
    ParamDePincel("oil_specular_brilliance", "oil", "specular_brilliance", padrao=0.5),
)


# ── Parâmetros que NÃO moram no BrushProfile ────────────────────────────────
# Estes passam por um método do backend, não por um campo da struct. Ficam
# aqui para que a lista de chaves de preset continue tendo uma origem única,
# mas o caminho de escrita é outro.
#
# `stabilizer_weight` é o único com leitura própria (vem do DynamicStabilizer,
# não do perfil) — `get_brush_profile_dict` a trata explicitamente.

@dataclass(frozen=True)
class ParamPorMetodo:
    chave: str
    metodo: str
    conversor: Callable[[Any], Any]


PARAMS_POR_METODO: tuple[ParamPorMetodo, ...] = (
    ParamPorMetodo("engine_type", "set_engine_type", int),
    ParamPorMetodo("shape_preset", "set_shape_preset", int),
    ParamPorMetodo("brush_height_preset", "set_brush_height_preset", int),
    ParamPorMetodo("stabilizer_weight", "set_stabilizer_weight", float),
)


# ── Índices derivados ───────────────────────────────────────────────────────

POR_CHAVE: dict[str, ParamDePincel] = {p.chave: p for p in TABELA}

POR_GRUPO_E_ATRIBUTO: dict[tuple[str, str], ParamDePincel] = {}
for _p in TABELA:
    POR_GRUPO_E_ATRIBUTO[(_p.grupo, _p.atributo)] = _p
    if _p.grupo == "":                       # "root" é sinônimo da raiz
        POR_GRUPO_E_ATRIBUTO[("root", _p.atributo)] = _p

CHAVES_DE_PRESET: frozenset[str] = frozenset(
    [p.chave for p in TABELA] + [p.chave for p in PARAMS_POR_METODO]
)


def alvo_nativo(perfil: Any, grupo: str) -> Any:
    """Objeto nativo onde o grupo mora. Lança se o grupo não for declarado."""
    if grupo not in ATRIBUTO_DO_GRUPO:
        raise KeyError(
            f"grupo de pincel desconhecido: {grupo!r}. "
            f"Grupos declarados: {sorted(g for g in ATRIBUTO_DO_GRUPO if g)}"
        )
    atributo = ATRIBUTO_DO_GRUPO[grupo]
    if atributo is None:
        return perfil
    return getattr(perfil, atributo)


def resolver(grupo: str, parametro: str) -> ParamDePincel:
    """Encontra a linha da tabela para um par (grupo, parâmetro) da interface.

    Lança KeyError quando o par não existe — de propósito. O silêncio anterior
    (`hasattr` sem `else`) transformava "esqueci de ligar isso" em "parece que
    está ligado", e o custo aparecia meses depois, sem rastro.
    """
    linha = POR_GRUPO_E_ATRIBUTO.get((grupo, parametro))
    if linha is None:
        raise KeyError(
            f"parâmetro de pincel não declarado: grupo={grupo!r} "
            f"parâmetro={parametro!r}. O motor não expõe esse campo, ou a "
            f"tabela em brush_param_table.py precisa declará-lo."
        )
    return linha
