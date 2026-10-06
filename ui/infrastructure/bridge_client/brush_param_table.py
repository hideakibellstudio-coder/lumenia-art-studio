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

def to_float(value: Any, _native: Any) -> float:
    return float(value)


def to_int(value: Any, _native: Any) -> int:
    return int(value)


def to_bool(value: Any, _native: Any) -> bool:
    return bool(value)


def _enum_by_index(value: Any, enum_cls: Any, label: str) -> Any:
    """A interface guarda o índice da combo; o motor exige o enum.

    A faixa é validada aqui, contra `__members__`, ANTES de construir o enum.
    `Enum(9)` não levanta nada no PyBind11 — devolve um enum com valor 9, que o
    motor recebe e usa. Delegar a validação ao construtor deixaria passar
    exatamente o tipo de lixo que esta tabela existe para barrar.
    """
    if isinstance(value, enum_cls):
        return value
    index = int(value)
    members = list(enum_cls.__members__.values())
    if not 0 <= index < len(members):
        raise ValueError(
            f"{label} fora da faixa: {index} "
            f"(o motor declara {len(members)} modos: "
            f"{', '.join(enum_cls.__members__)})"
        )
    return members[index]


def to_blend_mode(value: Any, native: Any) -> Any:
    return _enum_by_index(value, native.DabBlendMode, "blend_mode")


def to_grain_mode(value: Any, native: Any) -> Any:
    return _enum_by_index(value, native.GrainMode, "grain_mode")


def from_enum(value: Any) -> int:
    return int(value)


def identity(value: Any) -> Any:
    return value


# ── Onde cada grupo mora dentro do BrushProfile nativo ───────────────────────
# "" é a raiz do perfil. "root" é aceito como sinônimo por compatibilidade com
# as chamadas existentes da interface.

GROUP_ATTRIBUTES: dict[str, str | None] = {
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
class BrushParamSpec:
    """Uma propriedade do pincel, declarada uma única vez."""

    key: str                                   # chave de preset / interface
    group: str                                   # "" para a raiz do perfil
    attribute: str                                # nome do campo no módulo nativo
    to_engine: Callable[[Any, Any], Any] = to_float
    to_preset: Callable[[Any], Any] = identity
    default: Any = 0.0
    readable: bool = True                         # entra em get_brush_profile_dict


# ── A tabela ────────────────────────────────────────────────────────────────
# Toda linha aqui foi verificada contra as bindings PyBind11. Campos que a
# interface pedia e o motor não tem (`scatter_radius`, `jitter_opacity`) foram
# REMOVIDOS em vez de mantidos mortos — o motor define, a interface exibe.

BRUSH_PARAMS: tuple[BrushParamSpec, ...] = (
    # ── Raiz do perfil ──────────────────────────────────────────────────────
    BrushParamSpec("brush_size", "", "brush_size", default=20.0),
    BrushParamSpec("opacity", "", "opacity", default=1.0),
    BrushParamSpec("flow", "", "flow", default=1.0),
    BrushParamSpec("hardness", "", "hardness", default=0.85),
    BrushParamSpec("spacing_factor", "", "spacing_factor", default=0.08),
    BrushParamSpec("min_size_percent", "", "min_size_percent", default=0.0),
    BrushParamSpec("min_opacity_percent", "", "min_opacity_percent", default=0.0),
    BrushParamSpec("pressure_size_enabled", "", "pressure_size_enabled",
                  to_engine=to_bool, default=True),
    BrushParamSpec("pressure_flow_enabled", "", "pressure_flow_enabled",
                  to_engine=to_bool, default=True),
    BrushParamSpec("velocity_size_enabled", "", "velocity_size_enabled",
                  to_engine=to_bool, default=False),
    BrushParamSpec("stroke_taper_enabled", "", "stroke_taper_enabled",
                  to_engine=to_bool, default=True),
    BrushParamSpec("stroke_taper_length", "", "stroke_taper_length", default=20.0),
    BrushParamSpec("time_spacing_enabled", "", "time_spacing_enabled",
                  to_engine=to_bool, default=False),
    BrushParamSpec("dabs_per_second", "", "dabs_per_second", default=60.0),
    BrushParamSpec("blend_mode", "", "blend_mode",
                  to_engine=to_blend_mode, to_preset=from_enum, default=0),
    BrushParamSpec("pressure_to_angle", "", "pressure_to_angle", default=0.0),
    BrushParamSpec("pressure_to_aspect", "", "pressure_to_aspect", default=0.0),
    BrushParamSpec("velocity_to_flow", "", "velocity_to_flow", default=0.0),
    BrushParamSpec("scatter_count", "", "scatter_count",
                  to_engine=to_int, default=1),
    BrushParamSpec("brush_grain_enabled", "", "brush_grain_enabled",
                  to_engine=to_bool, default=False),
    BrushParamSpec("brush_grain_mode", "", "brush_grain_mode",
                  to_engine=to_grain_mode, to_preset=from_enum, default=0),
    BrushParamSpec("brush_grain_scale", "", "brush_grain_scale", default=1.0),
    BrushParamSpec("brush_grain_contrast", "", "brush_grain_contrast", default=1.0),
    BrushParamSpec("brush_grain_invert", "", "brush_grain_invert",
                  to_engine=to_bool, default=False),

    # ── Geometria da ponta ──────────────────────────────────────────────────
    # Os jitters moram em BrushTip, não num grupo "dynamics". A interface
    # escrevia em "dynamics", que nunca existiu no módulo nativo.
    BrushParamSpec("tip_angle", "tip", "angle", default=0.0),
    BrushParamSpec("tip_aspect", "tip", "aspect_ratio", default=1.0),
    BrushParamSpec("follow_stroke", "tip", "follow_stroke",
                  to_engine=to_bool, default=False),
    BrushParamSpec("tilt_to_angle", "tip", "tilt_to_angle", default=0.0),
    BrushParamSpec("tilt_to_aspect", "tip", "tilt_to_aspect", default=0.0),
    BrushParamSpec("tilt_to_size", "tip", "tilt_to_size", default=0.0),
    BrushParamSpec("tilt_to_flow", "tip", "tilt_to_flow", default=0.0),
    BrushParamSpec("use_twist_for_angle", "tip", "use_twist_for_angle",
                  to_engine=to_bool, default=False),
    BrushParamSpec("jitter_size", "tip", "jitter_size", default=0.0),
    BrushParamSpec("jitter_angle", "tip", "jitter_angle", default=0.0),
    BrushParamSpec("jitter_position", "tip", "jitter_position", default=0.0),

    # ── Parâmetros por mini-motor ───────────────────────────────────────────
    BrushParamSpec("pencil_graphite_hardness", "pencil", "graphite_hardness", default=0.5),
    BrushParamSpec("pencil_tilt_shading", "pencil", "tilt_shading_enabled",
                  to_engine=to_bool, default=False),
    BrushParamSpec("inker_flow_rate", "inker", "ink_flow_rate", default=0.8),
    BrushParamSpec("inker_taper_smoothing", "inker", "taper_smoothing", default=0.3),
    BrushParamSpec("marker_solvent_wetness", "marker", "solvent_wetness", default=0.5),
    BrushParamSpec("marker_edge_darkening", "marker", "edge_darkening", default=0.4),
    BrushParamSpec("blur_radius", "blur", "blur_radius", to_engine=to_int, default=5),
    BrushParamSpec("blur_strength", "blur", "blur_strength", default=0.5),
    BrushParamSpec("smudge_color_pickup", "smudge", "color_pickup", default=0.7),
    BrushParamSpec("smudge_mix_ratio", "smudge", "mix_ratio", default=0.5),
    BrushParamSpec("smudge_stretch", "smudge", "smudge_stretch", default=0.8),
    BrushParamSpec("watercolor_water_level", "watercolor", "water_level", default=0.5),
    BrushParamSpec("watercolor_pigment_bleed", "watercolor", "pigment_bleed", default=0.5),
    BrushParamSpec("watercolor_fringe_intensity", "watercolor", "fringe_intensity", default=0.4),
    BrushParamSpec("watercolor_granulation", "watercolor", "granulation", default=0.3),
    BrushParamSpec("oil_impasto_depth", "oil", "impasto_depth", default=0.7),
    BrushParamSpec("oil_bristle_grooves", "oil", "bristle_grooves", default=0.5),
    BrushParamSpec("oil_viscosity", "oil", "viscosity", default=0.6),
    BrushParamSpec("oil_specular_brilliance", "oil", "specular_brilliance", default=0.5),
    BrushParamSpec("oil_wet_mix_factor", "oil", "wet_mix_factor", default=0.35),
    BrushParamSpec("oil_paint_depletion", "oil", "paint_depletion", default=0.0),
)


# ── Parâmetros que NÃO moram no BrushProfile ────────────────────────────────
# Estes passam por um método do backend, não por um campo da struct. Ficam
# aqui para que a lista de chaves de preset continue tendo uma origem única,
# mas o caminho de escrita é outro.
#
# `stabilizer_weight` é o único com leitura própria (vem do DynamicStabilizer,
# não do perfil) — `get_brush_profile_dict` a trata explicitamente.

@dataclass(frozen=True)
class MethodParamSpec:
    key: str
    method: str
    converter: Callable[[Any], Any]


METHOD_PARAMS: tuple[MethodParamSpec, ...] = (
    MethodParamSpec("engine_type", "set_engine_type", int),
    MethodParamSpec("shape_preset", "set_shape_preset", int),
    MethodParamSpec("brush_height_preset", "set_brush_height_preset", int),
    MethodParamSpec("stabilizer_weight", "set_stabilizer_weight", float),
)


# ── Índices derivados ───────────────────────────────────────────────────────

BY_KEY: dict[str, BrushParamSpec] = {p.key: p for p in BRUSH_PARAMS}

BY_GROUP_AND_ATTRIBUTE: dict[tuple[str, str], BrushParamSpec] = {}
for _p in BRUSH_PARAMS:
    BY_GROUP_AND_ATTRIBUTE[(_p.group, _p.attribute)] = _p
    if _p.group == "":                       # "root" é sinônimo da raiz
        BY_GROUP_AND_ATTRIBUTE[("root", _p.attribute)] = _p

PRESET_KEYS: frozenset[str] = frozenset(
    [p.key for p in BRUSH_PARAMS] + [p.key for p in METHOD_PARAMS]
)


def native_target(profile: Any, group: str) -> Any:
    """Objeto nativo onde o grupo mora. Lança se o grupo não for declarado."""
    if group not in GROUP_ATTRIBUTES:
        raise KeyError(
            f"grupo de pincel desconhecido: {group!r}. "
            f"Grupos declarados: {sorted(g for g in GROUP_ATTRIBUTES if g)}"
        )
    attribute = GROUP_ATTRIBUTES[group]
    if attribute is None:
        return profile
    return getattr(profile, attribute)


def resolve_param(group: str, param: str) -> BrushParamSpec:
    """Encontra a linha da tabela para um par (grupo, parâmetro) da interface.

    Lança KeyError quando o par não existe — de propósito. O silêncio anterior
    (`hasattr` sem `else`) transformava "esqueci de ligar isso" em "parece que
    está ligado", e o custo aparecia meses depois, sem rastro.
    """
    spec = BY_GROUP_AND_ATTRIBUTE.get((group, param))
    if spec is None:
        raise KeyError(
            f"parâmetro de pincel não declarado: grupo={group!r} "
            f"parâmetro={param!r}. O motor não expõe esse campo, ou a "
            f"tabela em brush_param_table.py precisa declará-lo."
        )
    return spec
