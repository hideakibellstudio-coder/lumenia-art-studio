"""Tests for Phase 4: Layers Plugin (paper & panel) ARCcC v2 decomposition."""

import pytest
from PySide6 import QtWidgets, QtGui

from plugins.ui.layers_plugin.paper_texture_dialog import TexturePopup
from plugins.ui.layers_plugin.paper import TexturePopup as PaperTexturePopup, PaperLayerWidget
from plugins.ui.layers_plugin.panel import LayersPanel
from ui.core.document.local_layer import LocalLayer



def test_texture_popup_standalone_and_export(qapp):
    # Test identical class export
    assert TexturePopup is PaperTexturePopup

    popup = TexturePopup(preset_id=1, depth=0.75, scale=2.0, invert=True, enabled=True)
    assert popup.preset_id == 1
    assert popup.chk_c_invert.isChecked()
    assert popup.chk_c_grain.isChecked()
    assert popup.scale_slider.value() == 200
    assert popup.depth_slider.value() == 75

    emitted_presets = []
    emitted_depth = []
    popup.presetChanged.connect(emitted_presets.append)
    popup.depthChanged.connect(emitted_depth.append)

    popup._on_preset_changed(2)
    assert 2 in emitted_presets

    popup.depth_slider.setValue(150)
    assert 1.5 in emitted_depth


def test_paper_layer_widget_integration(qapp):
    """O widget mostra o papel do documento e não guarda cópia dele."""
    from ui.core.document.document import Document
    paper = PaperLayerWidget()
    doc = Document("paper-structure", "Papel", 8, 8)
    doc.set_paper(color=QtGui.QColor(200, 100, 50), visible=False, texture_id=2, texture_enabled=True)
    paper.show_document(doc)
    assert paper.color_btn.color.red() == 200
    assert paper.tex_btn.has_texture is True
    for attribute in ("visible", "color", "preset_id", "enabled"):
        assert not hasattr(paper, attribute), f"cópia de estado '{attribute}' voltou ao widget"


def test_layers_panel_delegate_actions(qapp):
    # O painel aqui tem gerenciador próprio; um documento ativo deixado por outro
    # módulo faria layer_transaction recusar a ação (painel != documento ativo).
    from ui.core.document.manager import DocumentManager
    dm = DocumentManager.instance()
    for doc in list(dm.documents()):
        dm.close_document(doc.uid)
    from ui.core.document.layer_manager import LocalLayerManager
    panel = LayersPanel()
    assert panel.layer_manager is None  # sem documento o painel não inventa um gerenciador
    panel.set_layer_manager(LocalLayerManager())

    # Duas camadas: a de baixo nunca pode ser máscara de recorte (regra do
    # LocalLayerManager). O setData antigo escrevia direto na camada e este
    # teste passava violando a regra.
    panel.add_layer("Base")
    panel.add_layer("Test Layer")
    active: LocalLayer = panel.layer_manager.get_active_layer()
    assert active is not None
    uid = active.uid

    # Test toggle visibility via handle_delegate_action
    orig_vis = active.visible
    panel.delegate.actionRequested.emit("toggle_visibility", uid)
    assert active.visible != orig_vis

    # Test toggle lock
    orig_lock = active.locked
    panel.delegate.actionRequested.emit("toggle_lock", uid)
    assert active.locked != orig_lock

    # Test toggle alpha lock
    orig_alpha = active.alpha_locked
    panel.delegate.actionRequested.emit("toggle_alpha", uid)
    assert active.alpha_locked != orig_alpha

    # Test toggle clipping mask
    orig_clip = active.clipping_mask
    panel.delegate.actionRequested.emit("toggle_clipping_mask", uid)
    assert active.clipping_mask != orig_clip

    base = panel.layer_manager.layers[0]
    panel.delegate.actionRequested.emit("toggle_clipping_mask", base.uid)
    assert base.clipping_mask is False
