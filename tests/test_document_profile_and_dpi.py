"""Perfil de cor por documento, DPI no Document e o fluxo "Novo documento".

Três defeitos medidos em 2026-09-24:
- o backend guardava UM perfil de cor para todos os documentos: voltar ao
  documento A depois de configurar o B mostrava e gravava o perfil do B;
- o DPI escolhido no diálogo de novo documento era descartado;
- o documento novo nascia sujo ("clear_canvas"), e fechá-lo sem mexer pedia
  para salvar.
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from PySide6 import QtWidgets

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(["--platform", "offscreen"])

from ui.core.config import ConfigManager
from ui.core.document.document import Document
from ui.core.document.restore import restore_document
from ui.core.document.schema import validate_auxiliary
from ui.core.document.serializer import DocumentFormatError, DocumentSerializer
from ui.engine_backends.aladyn import AladynBackend


def _document(uid: str) -> Document:
    doc = Document(uid, uid, 4, 4)
    doc.layer_manager.add_layer("Pintura")
    return doc


def test_color_profile_follows_the_active_document_context(tmp_path):
    backend = AladynBackend()
    a, b = _document("perfil-a"), _document("perfil-b")
    try:
        backend.set_active_document_context(a.uid, 4, 4)
        backend.set_color_profile(2)
        backend.set_active_document_context(b.uid, 4, 4)
        backend.set_color_profile(0)

        backend.set_active_document_context(a.uid, 4, 4)
        assert backend.get_color_profile() == 2
        manifest, _payloads = DocumentSerializer.read(DocumentSerializer.save(a, backend, tmp_path / "a.lmn"))
        assert manifest["color_profile_id"] == 2

        backend.set_active_document_context(b.uid, 4, 4)
        assert backend.get_color_profile() == 0

        # Fechar o ativo cai no outro documento, com o perfil dele.
        backend.close_document_context(b.uid)
        assert backend.get_active_document_context() == a.uid
        assert backend.get_color_profile() == 2
    finally:
        for uid in (a.uid, b.uid):
            backend.close_document_context(uid)


def test_dpi_round_trips_through_the_lmn_file(tmp_path):
    backend = AladynBackend()
    source, copy = _document("dpi-origem"), _document("dpi-copia")
    try:
        source.dpi = 600
        backend.set_active_document_context(source.uid, 4, 4)
        manifest, payloads = DocumentSerializer.read(DocumentSerializer.save(source, backend, tmp_path / "d.lmn"))
        assert manifest["dpi"] == 600
        backend.set_active_document_context(copy.uid, 4, 4)
        restore_document(copy, backend, manifest, payloads)
        assert copy.dpi == 600
    finally:
        for uid in (source.uid, copy.uid):
            backend.close_document_context(uid)


def test_files_without_dpi_open_at_300_and_invalid_dpi_is_rejected():
    validate_auxiliary({})  # arquivo anterior ao campo
    assert Document("x", "x").dpi == 300
    for bad in (0, -72, "300", 72.5, True):
        with pytest.raises(DocumentFormatError):
            validate_auxiliary({"dpi": bad})


@pytest.fixture
def main_window():
    from tests.main_window_fixture import main_window_com_workspace
    ConfigManager.instance().set_test_mode(True)
    yield main_window_com_workspace()
    ConfigManager.instance().set_test_mode(False)


def test_new_document_starts_clean_with_the_dialog_choices(main_window):
    from ui.core.screens import new_document_dialog as nd

    params = {"name": "Escolhas", "width": 64, "height": 48, "dpi": 600, "color_profile_id": 2,
              "bg_color": (10, 20, 30, 255), "paper_texture_id": 2}
    with patch.object(nd.NewDocumentDialog, "exec", return_value=QtWidgets.QDialog.Accepted), \
         patch.object(nd.NewDocumentDialog, "get_document_params", return_value=params):
        main_window.documents.new_document()

    doc = main_window.dm.active_document()
    backend = main_window.documents._backend()
    try:
        assert not doc.is_dirty, doc.dirty_reason
        assert doc.dpi == 600
        assert backend.get_active_document_context() == doc.uid
        assert backend.get_color_profile() == 2
        assert doc.paper_color.getRgb() == (10, 20, 30, 255)
        assert (doc.paper_texture_id, doc.paper_texture_enabled) == (2, True)
        assert backend.get_canvas_resource()["enabled"]
    finally:
        main_window.dm.close_document(doc.uid)


def test_opening_render_settings_does_not_change_the_document_profile(main_window):
    from ui.core.dialogs.render_settings_components import load_render_settings, save_render_settings
    from ui.core.dialogs.render_settings_dialog import RenderSettingsDialog

    saved = load_render_settings()
    save_render_settings({**saved, "profile_id": 2})
    doc = main_window.dm.new_document(32, 32, "Perfil intocado")
    backend = main_window.documents._backend()
    try:
        assert backend.get_color_profile() == 0
        dialog = RenderSettingsDialog()
        dialog.deleteLater()
        assert backend.get_color_profile() == 0
        assert not doc.is_dirty, doc.dirty_reason
    finally:
        save_render_settings(saved)
        main_window.dm.close_document(doc.uid)
