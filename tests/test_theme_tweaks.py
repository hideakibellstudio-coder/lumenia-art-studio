"""Ajustes finos do tema: raio dos cantos e fonte de verdade; filtro em qualquer idioma.

Até 2026-09-24 os combos "Raio dos Cantos" e "Família da Fonte" do diálogo
de temas não estavam ligados a nada, e o filtro Escuros/Claros comparava o
texto traduzido com o português (fora do pt-BR não filtrava).
"""
import pytest

from ui.core.config import ConfigManager
from ui.core.i18n import I18nManager
from ui.core.screens.settings.components.theme_card import ThemeCard
from ui.core.screens.settings.theme_dialog import ThemeDialog
from ui.core.theme.interface_tweaks import FONT_STACKS, radius_metrics, tweak_metrics, valid_font, valid_radius
from ui.core.theme.manager import ThemeManager


@pytest.fixture
def theme(qapp):
    manager = ThemeManager.instance()
    before = (manager.corner_radius, manager.font_key)
    yield manager
    manager.set_interface_tweaks(*before)


def test_raio_base_gera_os_quatro_raios():
    assert radius_metrics(8) == {"RADIUS_SMALL": "4px", "RADIUS_MEDIUM": "6px",
                                 "RADIUS_LARGE": "8px", "RADIUS_XLARGE": "12px"}  # padrão dos temas
    assert set(radius_metrics(0).values()) == {"0px"}
    assert tweak_metrics(None, None) == {}
    assert tweak_metrics(None, "roboto") == {"FONT_FAMILY": FONT_STACKS["roboto"]}


def test_valores_salvos_invalidos_viram_o_do_tema():
    assert valid_radius("8") is None and valid_radius(7) is None and valid_radius(True) is None
    assert valid_radius(16) == 16
    assert valid_font("comic") is None and valid_font("inter") == "inter"


def test_ajuste_entra_na_folha_de_estilo_e_nas_preferencias(theme):
    qss_before = theme.compile_qss("a { border-radius: @RADIUS_LARGE; font-family: @FONT_FAMILY; }")
    theme.set_interface_tweaks(16, "helvetica")
    qss = theme.compile_qss("a { border-radius: @RADIUS_LARGE; font-family: @FONT_FAMILY; }")
    assert qss != qss_before
    assert f"{round(16 * theme.ui_scale)}px" in qss and "Helvetica" in qss
    config = ConfigManager.instance()
    assert config.get("interface", "corner_radius") == 16
    assert config.get("interface", "font_family") == "helvetica"
    theme.set_interface_tweaks(None, None)
    assert theme.compile_qss("a { font-family: @FONT_FAMILY; }") == theme.compile_qss(
        "a { font-family: @FONT_FAMILY; }")  # volta ao do tema sem erro
    assert "Helvetica" not in theme.compile_qss("a { font-family: @FONT_FAMILY; }")


def test_combos_do_dialogo_aplicam_o_ajuste(theme):
    dialog = ThemeDialog()
    try:
        tweaks = dialog.tweaks_group
        tweaks.combo_radius.setCurrentIndex(1)  # Quadrado (0px)
        assert theme.corner_radius == 0
        tweaks.combo_font.setCurrentIndex(2)  # Inter
        assert theme.font_key == "inter"
        tweaks.combo_radius.setCurrentIndex(0)  # Padrão do tema
        assert theme.corner_radius is None
    finally:
        dialog.deleteLater()


def test_filtro_escuros_claros_funciona_em_ingles(qapp):
    i18n = I18nManager.instance()
    previous = i18n.get_current_locale()
    dialog = ThemeDialog()
    try:
        i18n.set_locale("en_US", is_auto=False)
        dialog.combo_filter.setCurrentIndex(1)  # "Dark Themes"
        visible = [card for card in dialog.findChildren(ThemeCard) if not card.isHidden()]
        assert visible, "algum tema escuro deve aparecer"
        assert all(card.theme_data["metadata"].get("type", "dark") == "dark" for card in visible)
        dialog.combo_filter.setCurrentIndex(2)  # "Light Themes"
        visible = [card for card in dialog.findChildren(ThemeCard) if not card.isHidden()]
        assert visible and all(card.theme_data["metadata"].get("type") == "light" for card in visible)
    finally:
        i18n.set_locale(previous, is_auto=False)
        dialog.deleteLater()
