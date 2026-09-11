"""Persistência e abertura de documentos para a janela principal."""

from __future__ import annotations

import os

from PySide6 import QtGui, QtWidgets

from ui.core.document.serializer import DocumentFormatError, DocumentSerializer
from ui.core.engine.registry import EngineRegistry
from ui.core.document.restore import restore_document


class MainWindowDocumentActionsMixin:
    """Ações de arquivo editável, isoladas do mixin de menus."""

    def open_image_file(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Abrir Imagem ou Documento",
            "",
            "Arquivos Lumenia (*.lmn);;Imagens (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if not filename:
            return
        if filename.lower().endswith(".lmn"):
            self.open_native_document(filename)
            return
        qimg = QtGui.QImage(filename)
        if qimg.isNull():
            return
        name = os.path.splitext(os.path.basename(filename))[0]
        width, height = qimg.width(), qimg.height()
        doc = self.dm.new_document(width=width, height=height, name=name)
        qimg_rgba = qimg.convertToFormat(QtGui.QImage.Format_RGBA8888)
        raw_bytes = bytes(qimg_rgba.constBits()[: width * height * 4])
        backend = EngineRegistry.instance().get_backend()
        if backend and getattr(backend, "available", False):
            backend.paste_rgba_buffer_on_active_layer(0, 0, width, height, raw_bytes)
        doc.mark_dirty("import_image")
        if self.workspace:
            self.workspace.canvas_widget.update()
        self.reset_view()
        self.status_bar.showMessage(f"Imagem '{name}' ({width}x{height}) aberta com sucesso!", 3000)

    def open_native_document(self, filename: str | None = None) -> bool:
        if not filename:
            filename, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "Abrir Documento Lumenia", "", "Documento Lumenia (*.lmn)"
            )
        if not filename:
            return False
        try:
            manifest, payloads = DocumentSerializer.read(filename)
        except (OSError, DocumentFormatError, ValueError) as exc:
            self.status_bar.showMessage(f"Falha ao abrir documento: {exc}", 5000)
            return False

        previous = self.dm.active_document()
        paper = manifest.get("paper", {})
        color = paper.get("color", [255, 255, 255, 255])
        doc = self.dm.new_document(
            width=int(manifest.get("width", 1)),
            height=int(manifest.get("height", 1)),
            name=str(manifest.get("name", os.path.basename(filename))),
            bg_color=tuple(int(x) for x in color[:4]),
            paper_texture_id=int(paper.get("texture_id", 0)),
        )
        doc.paper_visible = bool(paper.get("visible", True))
        doc.paper_texture_enabled = bool(paper.get("texture_enabled", False))
        backend = EngineRegistry.instance().get_backend()
        try:
            restore_document(doc, backend, manifest, payloads)
        except Exception as exc:
            self.dm.close_document(doc.uid)
            if backend:
                backend.close_document_context(doc.uid)
            if previous:
                self.dm.set_active_document(previous.uid)
            self.status_bar.showMessage(f"Falha ao restaurar documento: {exc}", 5000)
            return False

        doc.zoom = float(manifest.get("zoom", 1.0))
        doc.pan_x = float(manifest.get("pan_x", 0.0))
        doc.pan_y = float(manifest.get("pan_y", 0.0))
        doc.rotation = float(manifest.get("rotation", 0.0))
        if self.workspace and hasattr(self.workspace, "refresh_document_state"):
            self.workspace.refresh_document_state(doc)
        doc.mark_saved(filename)
        if self.workspace:
            self.workspace.canvas_widget.update()
        self.status_bar.showMessage(f"Documento '{doc.name}' aberto com sucesso.", 3000)
        return True

    def save_active_document(self) -> bool:
        doc = self.dm.active_document()
        if not doc:
            self.status_bar.showMessage("Nenhum documento ativo para salvar.", 2000)
            return False
        path = getattr(doc, "file_path", None)
        return self.save_active_document_as() if not path else self._save_document_to_path(doc, path)

    def save_active_document_as(self) -> bool:
        doc = self.dm.active_document()
        if not doc:
            self.status_bar.showMessage("Nenhum documento ativo para salvar.", 2000)
            return False
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Salvar Documento Lumenia", f"{doc.name}.lmn", "Documento Lumenia (*.lmn)"
        )
        return bool(filename) and self._save_document_to_path(doc, filename)

    def _save_document_to_path(self, doc, path: str) -> bool:
        backend = EngineRegistry.instance().get_backend()
        try:
            saved_path = DocumentSerializer.save(doc, backend, path)
        except Exception as exc:
            self.status_bar.showMessage(f"Falha ao salvar '{doc.name}': {exc}", 5000)
            return False
        doc.mark_saved(saved_path)
        if hasattr(self, "recovery"):
            self._discard_recovery(doc.uid)
        self.status_bar.showMessage(f"Documento '{doc.name}' salvo.", 2500)
        return True
