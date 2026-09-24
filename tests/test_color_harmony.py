"""Harmonias no painel "Cores & Harmonias" -- 2026-09-23.

O nome prometia harmonias que não existiam. Agora a regra escolhida marca as
cores parceiras no anel da roda e mostra amostras clicáveis.
"""

from __future__ import annotations

import pytest
from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.widgets.color_picker.harmony import HarmonyRule, harmony_colors, harmony_hues


@pytest.fixture(scope="module", autouse=True)
def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication(["--platform", "offscreen"])


def _graus(hues):
    return [round(h * 360) % 360 for h in hues]


@pytest.mark.parametrize("regra, esperado", [
    (HarmonyRule.NONE, []),
    (HarmonyRule.COMPLEMENTARY, [210]),
    (HarmonyRule.ANALOGOUS, [0, 60]),
    (HarmonyRule.TRIADIC, [150, 270]),
    (HarmonyRule.SPLIT_COMPLEMENTARY, [180, 240]),
    (HarmonyRule.SQUARE, [120, 210, 300]),
])
def test_deslocamentos_de_matiz(regra, esperado):
    assert _graus(harmony_hues(regra, 30 / 360)) == esperado


def test_parceiras_mantem_saturacao_e_valor():
    for cor in harmony_colors(HarmonyRule.TRIADIC, 0.0, 0.6, 0.8):
        _h, s, v, _a = cor.getHsvF()
        assert abs(s - 0.6) < 0.01 and abs(v - 0.8) < 0.01


def test_valor_desconhecido_vira_nenhuma():
    assert HarmonyRule.coerce("arco-iris") is HarmonyRule.NONE


def test_roda_mostra_marca_e_amostras_e_lembra_a_regra():
    from ui.core.config.manager import ConfigManager
    from ui.core.widgets.color_picker.color_wheel import ColorWheelWidget
    from ui.core.widgets.color_picker.harmony_widgets import HarmonyStrip

    roda: ColorWheelWidget = ColorWheelWidget(initial_color=QtGui.QColor.fromHsvF(0.0, 1.0, 1.0))
    faixa: HarmonyStrip = roda.harmony
    faixa.set_rule(HarmonyRule.TRIADIC)
    assert ConfigManager.instance().get("color", "harmony") == "triadic"
    assert _graus(roda.wheel.harmony_hues()) == [120, 240]
    visiveis = [b for b in faixa.amostras if not b.isHidden()]
    assert len(visiveis) == 2

    recebidas = []
    roda.colorChanged.connect(recebidas.append)
    visiveis[0].click()
    assert recebidas and round(recebidas[-1].hsvHueF() * 360) == 120
    # A nova cor vira a base: as parceiras giram junto.
    assert _graus(roda.wheel.harmony_hues()) == [240, 0]

    faixa.set_rule(HarmonyRule.NONE)
    assert roda.wheel.harmony_hues() == []
    assert all(b.isHidden() for b in faixa.amostras)
