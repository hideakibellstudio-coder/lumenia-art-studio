"""Contrato do enum canonico de modo de mesclagem de camadas -- o motor
define, a interface consome.

Ver `ui/core/document/layer_blend_mode.py` para o historico completo: antes
desta classe, cinco lugares diferentes traduziam blend_mode cada um a sua
maneira (rotulo em portugues cru guardado como valor, tres formas de string
comparadas por igualdade, duas tabelas indice->rotulo divergentes -- uma
delas com a ordem errada). Isto e' o teste de contrato que faltava, no
mesmo racional de `test_brush_param_contract.py`.

O binding pybind11 (`bridge/core/bindings/bind_math_brush.cpp`) expunha
originalmente so 7 dos 13 valores de `document::LayerBlendMode`
(Normal..Erase) -- estendido na Fase C5 para os 13, ja que o motor
(`engine/core/document/blending/BlendEquations.hpp`) sempre implementou os
13 por completo e a UI (`layers_plugin/header.py`) ja os ofereceria todos.
`ui/infrastructure/bridge_client/aladyn_layer_mixin.py` nao depende deste binding pra
converter (passa o indice inteiro puro direto pra
`PaintEngineFacade::setLayerBlendMode(int)`), mas o binding documentando o
contrato completo evita a mesma lacuna se algum codigo futuro voltar a
construir `native.LayerBlendMode(...)` diretamente.
"""

from __future__ import annotations

import pytest

from ui.core.document.layer_blend_mode import LayerBlendMode, DISPLAY_ORDER, _LABEL_TO_MODE

native = pytest.importorskip(
    "aladyn_engine_native", reason="módulo nativo não compilado neste ambiente"
)


@pytest.mark.parametrize("member", list(LayerBlendMode))
def test_all_13_modes_match_native(member):
    native_member = getattr(native.LayerBlendMode, member.name.title().replace("_", ""), None)
    assert native_member is not None, (
        f"native.LayerBlendMode não tem {member.name} -- binding incompleto "
        f"(ver bridge/core/bindings/bind_math_brush.cpp)"
    )
    assert int(native_member) == int(member)


def test_native_binding_covers_every_canonical_member_exactly_once():
    native_names = set(native.LayerBlendMode.__members__)
    python_names = {m.name.title().replace("_", "") for m in LayerBlendMode}
    assert native_names == python_names, (
        f"native.LayerBlendMode tem {len(native_names)} membros, "
        f"LayerBlendMode (Python) tem {len(python_names)} -- fora de sincronia"
    )


def test_display_order_covers_every_canonical_member_exactly_once():
    assert set(DISPLAY_ORDER) == set(LayerBlendMode)
    assert len(DISPLAY_ORDER) == len(LayerBlendMode)


@pytest.mark.parametrize("label,expected", sorted(_LABEL_TO_MODE.items()))
def test_from_label_resolves_every_known_alias(label, expected):
    assert LayerBlendMode.from_label(label) == expected


@pytest.mark.parametrize("label", ["Multiplicar", "Sobrepor"])
def test_from_label_fixes_the_confirmed_typo_bug(label):
    """Regressão direta do bug: header.py emitia esses dois rótulos, mas a
    tabela de conversão antiga (aladyn_layer_mixin.py) só conhecia
    "Multiplicação"/"Sobreposição" -- então selecionar "Multiplicar" ou
    "Sobrepor" no painel de camadas aplicava Normal silenciosamente."""
    assert LayerBlendMode.from_label(label) != LayerBlendMode.NORMAL


def test_from_label_unknown_falls_back_to_normal():
    assert LayerBlendMode.from_label("nao-existe") == LayerBlendMode.NORMAL


@pytest.mark.parametrize("value,expected", [
    (7, LayerBlendMode.PASS_THROUGH),
    ("Atravessar", LayerBlendMode.PASS_THROUGH),
    ("PassThrough", LayerBlendMode.PASS_THROUGH),
    ("Pass-Through", LayerBlendMode.PASS_THROUGH),
    (LayerBlendMode.ADD, LayerBlendMode.ADD),
    (99, LayerBlendMode.NORMAL),
])
def test_coerce_handles_every_historical_form(value, expected):
    assert LayerBlendMode.coerce(value) == expected


@pytest.mark.parametrize("member", list(LayerBlendMode))
def test_set_layer_blend_mode_accepts_every_mode_as_plain_int(member):
    """Confirma que o motor aceita os 13 indices via
    PaintEngineFacade::setLayerBlendMode(int) -- o caminho real que
    aladyn_layer_mixin.py usa, sem depender do enum nativo."""
    facade = native.PaintEngineFacade(8, 8)
    idx = facade.add_layer("Camada de teste", -1)
    assert idx >= 0
    facade.set_layer_blend_mode(idx, int(member))
