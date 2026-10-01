"""DocumentActions — novo, abrir, salvar e fechar documentos.

Colaborador da `MainWindow` (ver `shell_actions.py`). Recebe pelo construtor
a janela (pai dos diálogos), o `DocumentManager`, o provedor do motor, o
`BrushEngineSync` (reenvia o pincel à facade nova) e o workspace (câmera e
estado do documento aberto; pode ser None sem plugins).
"""
from __future__ import annotations

import os
from typing import Callable, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from ui.infrastructure.i18n import tr
from ui.core.engine.limits import max_canvas_dimension
from ui.core.document.document import Document
from ui.core.document.document_loader import DocumentLoader, LoadedDocument
from ui.core.document.document_saver import DocumentSaver
from ui.core.document.save_capture import SaveCapture, capture_document
from ui.core.document.manager import DocumentManager
from ui.core.document.restore import restore_document
from ui.core.state import BrushEngineSync

from .shell_actions import BackendProvider, ShellActions, backend_ready
from .workspace_port import ShellWorkspace


class DocumentActions(ShellActions):
    # Documento gravado em disco: a cópia de recuperação dele pode sair.
    documentSaved = QtCore.Signal(str)

    def __init__(
        self,
        window: QtWidgets.QWidget,
        dm: DocumentManager,
        backend: BackendProvider,
        brush_sync: BrushEngineSync,
        workspace: Optional[ShellWorkspace],
        saver: DocumentSaver,
        loader: DocumentLoader,
    ) -> None:
        super().__init__(window)
        self._window = window
        self._dm = dm
        self._backend = backend
        self._brush_sync = brush_sync
        self._workspace = workspace
        self._saver = saver
        self._loader = loader
        # Onde cada documento está sendo salvo pela primeira vez: `file_path` só vale depois da
        # gravação terminar, e um segundo Ctrl+S nesse meio tempo não deve reabrir o diálogo.
        self._saving_to: dict[str, str] = {}

    # ── Novo ──────────────────────────────────────────────────────────────

    def new_document(self) -> None:
        from ui.core.screens.new_document_dialog import NewDocumentDialog
        dialog = NewDocumentDialog(self._window)
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return
        params = dialog.get_document_params()
        name, w, h = params["name"], params["width"], params["height"]
        dpi = params.get("dpi", 300)
        color_prof = params.get("color_profile_id", 0)
        bg_color = params.get("bg_color", (255, 255, 255, 255))
        paper_tex = params.get("paper_texture_id", 0)

        # Ativar o documento abre o contexto dele no motor e leva o papel
        # (DocumentViewSync). Até 2026-09-24 esta ação também escrevia o papel
        # direto no motor e limpava a tela nova, e o documento nascia sujo.
        doc = self._dm.new_document(width=w, height=h, name=name, bg_color=bg_color, dpi=dpi)
        if not self._hosted(doc):
            return
        if paper_tex > 0:
            doc.set_paper(texture_id=paper_tex, texture_enabled=True)  # carrega o relevo do preset
        backend = self._backend()
        if backend_ready(backend):
            backend.set_color_profile(color_prof)
            # A facade nova começa com o pincel padrão do motor: reenvia o
            # pincel do usuário (preset, parâmetros e cor).
            self._brush_sync.resync()
        # Papel e perfil escolhidos no diálogo são o estado inicial, não edição.
        doc.mark_saved()
        self._reset_view()
        prof_name = backend.get_color_profile_name(color_prof) if backend else "sRGB"
        self._say(tr("status.doc_created", "Novo documento '{name}' ({w}×{h} px, {dpi} DPI, {profile}) criado.",
                     name=doc.name, w=w, h=h, dpi=dpi, profile=prof_name), 3000)

    # ── Abrir ─────────────────────────────────────────────────────────────

    def _hosted(self, doc: Document) -> bool:
        """True quando o contexto ativo do motor é o do documento novo.

        Falso se o motor não pôde criá-lo: a vista vai fechar o documento e dizer o
        motivo, mas seguir daqui escreveria no documento que estava aberto (a
        colagem da imagem e a restauração de arquivo agem no contexto ativo).
        Sem motor (modo casca) não há contexto a conferir."""
        backend = self._backend()
        if not backend_ready(backend):
            return True
        return backend.get_active_document_context() == doc.uid

    def open_file(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self._window,
            tr("file_dialogs.open_image_or_document", "Abrir Imagem ou Documento"),
            "",
            f"{tr('file_dialogs.lumenia_files', 'Arquivos Lumenia')} (*.lmn);;"
            f"{tr('file_dialogs.images', 'Imagens')} (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if not filename:
            return
        if filename.lower().endswith(".lmn"):
            self.open_native_document(filename)
            return
        self.open_image(filename)

    def open_image(self, filename: str) -> None:
        name = os.path.splitext(os.path.basename(filename))[0]
        limit = max_canvas_dimension()
        reader = QtGui.QImageReader(filename)
        size = reader.size()  # lê só o cabeçalho; inválido em formato que não o declara
        if size.isValid() and (size.width() > limit or size.height() > limit):
            self._say(tr("status.image_too_large",
                         "A imagem '{name}' ({w}×{h} px) passa do tamanho máximo do canvas ({max}×{max} px).",
                         name=name, w=size.width(), h=size.height(), max=limit), 6000)
            return
        # O Qt recusa por padrão qualquer imagem acima de 256 MB e a recusa parece
        # defeito do arquivo. O teto de verdade é o do motor (um lado de `limit`, 4 bytes por pixel).
        reader.setAllocationLimit(limit * limit * 4 // (1024 * 1024) + 64)
        qimg = reader.read()
        if qimg.isNull():
            self._say(tr("status.image_read_failed", "Não foi possível ler a imagem '{name}'.", name=filename), 4000)
            return
        width, height = qimg.width(), qimg.height()
        dpi = max(1, round(qimg.dotsPerMeterX() * 0.0254))  # a resolução gravada na imagem
        doc = self._dm.new_document(width=width, height=height, name=name, dpi=dpi)
        if not self._hosted(doc):
            return
        rgba = qimg.convertToFormat(QtGui.QImage.Format_RGBA8888)
        raw_bytes = bytes(rgba.constBits()[: width * height * 4])
        backend = self._backend()
        if backend_ready(backend):
            backend.paste_rgba_buffer_on_active_layer(0, 0, width, height, raw_bytes)
        doc.mark_dirty("import_image")
        self._reset_view()
        self._say(tr("status.image_opened", "Imagem '{name}' ({w}×{h}) aberta.", name=name, w=width, h=height), 3000)

    def open_native_document(self, filename: str | None = None, then: Optional[Callable[[Document], None]] = None) -> bool:
        """Começa a abrir um `.lmn`. True se a leitura foi iniciada; `then(doc)` roda com o documento aberto.

        Ler e decodificar o arquivo (quase todo o tempo) roda numa thread de fundo; aqui, na thread
        da interface, só se cria o documento e se adotam os pixels já decodificados. Falhas chegam
        pela barra de status, como antes, e deixam aberto o que estava aberto."""
        if not filename:
            filename, _ = QtWidgets.QFileDialog.getOpenFileName(
                self._window, tr("file_dialogs.open_document", "Abrir Documento Lumenia"), "",
                f"{tr('file_dialogs.lumenia_document', 'Documento Lumenia')} (*.lmn)",
            )
        if not filename:
            return False
        backend = self._backend()
        if not backend_ready(backend):
            self._say(tr("status.doc_open_failed", "Falha ao abrir documento: {error}", error="motor indisponível"), 5000)
            return False
        self._say(tr("status.doc_opening", "Abrindo '{name}'...", name=os.path.basename(filename)), 0)
        self._loader.submit(
            filename, backend,
            on_done=lambda loaded: self._finish_open(loaded, then),
            on_error=self._on_open_failed,
        )
        return True

    def _on_open_failed(self, _filename: str, error: Exception) -> None:
        self._say(tr("status.doc_open_failed", "Falha ao abrir documento: {error}", error=error), 5000)

    def _finish_open(self, loaded: LoadedDocument, then: Optional[Callable[[Document], None]]) -> None:
        """A metade que precisa da thread do documento: cria o documento e adota os pixels."""
        manifest, filename = loaded.manifest, loaded.path
        previous = self._dm.active_document()
        paper = manifest.get("paper", {})
        color = paper.get("color", [255, 255, 255, 255])
        doc: Document = self._dm.new_document(
            width=int(manifest.get("width", 1)),
            height=int(manifest.get("height", 1)),
            name=str(manifest.get("name", os.path.basename(filename))),
            bg_color=tuple(int(x) for x in color[:4]),
        )  # a textura do papel vem do arquivo, em restore_document
        if not self._hosted(doc):
            return
        doc.paper_visible = bool(paper.get("visible", True))
        doc.paper_texture_enabled = bool(paper.get("texture_enabled", False))
        backend = self._backend()
        try:
            restore_document(doc, backend, manifest, loaded.payloads, loaded.prepared)
        except Exception as exc:
            self._dm.close_document(doc.uid)
            if backend:
                backend.close_document_context(doc.uid)
            if previous:
                self._dm.set_active_document(previous.uid)
            self._say(tr("status.doc_restore_failed", "Falha ao restaurar documento: {error}", error=exc), 5000)
            return

        doc.zoom = float(manifest.get("zoom", 1.0))
        doc.pan_x = float(manifest.get("pan_x", 0.0))
        doc.pan_y = float(manifest.get("pan_y", 0.0))
        doc.rotation = float(manifest.get("rotation", 0.0))
        if self._workspace is not None:
            self._workspace.refresh_document_state(doc)
        doc.mark_saved(filename)
        self._say(tr("status.doc_opened", "Documento '{name}' aberto.", name=doc.name), 3000)
        if then is not None:
            then(doc)

    def wait_for_opens(self, timeout_ms: int = 120_000) -> bool:
        """Espera as aberturas em andamento (ao sair, e nos testes)."""
        return self._loader.wait_idle(timeout_ms)

    # ── Salvar ────────────────────────────────────────────────────────────

    def save_active(self, then: Optional[Callable[[Document], None]] = None) -> bool:
        """Começa a salvar o documento ativo. True se a gravação foi iniciada.

        `then(doc)` roda quando o arquivo está gravado e conferido (e não roda se falhar):
        é como "salvar e fechar" sabe quando fechar sem arriscar o documento."""
        doc = self._dm.active_document()
        if not doc:
            self._say(tr("status.no_doc_to_save", "Nenhum documento ativo para salvar."), 2000)
            return False
        path = doc.file_path or self._saving_to.get(doc.uid)
        return self._save_to_path(doc, path, then) if path else self.save_active_as(then)

    def save_active_as(self, then: Optional[Callable[[Document], None]] = None) -> bool:
        doc = self._dm.active_document()
        if not doc:
            self._say(tr("status.no_doc_to_save", "Nenhum documento ativo para salvar."), 2000)
            return False
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self._window, tr("file_dialogs.save_document", "Salvar Documento Lumenia"), f"{doc.name}.lmn",
            f"{tr('file_dialogs.lumenia_document', 'Documento Lumenia')} (*.lmn)",
        )
        return bool(filename) and self._save_to_path(doc, filename, then)

    def _save_to_path(self, doc: Document, path: str, then: Optional[Callable[[Document], None]] = None) -> bool:
        """A metade que precisa da thread do documento; a gravação segue no `DocumentSaver`."""
        try:
            capture = capture_document(doc, self._backend(), path)
        except Exception as exc:
            self._say(tr("status.doc_save_failed", "Falha ao salvar '{name}': {error}", name=doc.name, error=exc), 5000)
            return False
        self._saving_to[doc.uid] = str(capture.target)
        self._say(tr("status.doc_saving", "Salvando '{name}'...", name=doc.name), 0)
        self._saver.submit(
            capture,
            on_done=lambda done: self._on_saved(done, then),
            on_error=self._on_save_failed,
        )
        return True

    def _on_saved(self, capture: SaveCapture, then: Optional[Callable[[Document], None]]) -> None:
        self._saving_to.pop(capture.uid, None)
        doc = self._dm.get_document(capture.uid)
        if doc is None:  # fechado enquanto gravava: o arquivo está salvo e não há mais o que atualizar
            return
        doc.mark_saved(str(capture.target), revision=capture.revision)
        self.documentSaved.emit(doc.uid)
        self._say(tr("status.doc_saved", "Documento '{name}' salvo com sucesso.", name=doc.name), 2500)
        if then is not None:
            then(doc)

    def _on_save_failed(self, capture: SaveCapture, error: Exception) -> None:
        self._saving_to.pop(capture.uid, None)
        self._say(tr("status.doc_save_failed", "Falha ao salvar '{name}': {error}", name=capture.manifest.get("name", ""), error=error), 8000)

    def wait_for_saves(self, timeout_ms: int = 300_000) -> bool:
        """Espera as gravações em andamento (ao sair). False se passou do prazo."""
        return self._saver.wait_idle(timeout_ms)

    # ── Fechar ────────────────────────────────────────────────────────────

    def close_active(self) -> None:
        doc = self._dm.active_document()
        if doc:
            self.close_with_confirmation(doc.uid)

    def close_with_confirmation(self, uid: str) -> None:
        doc = self._dm.get_document(uid)
        if not doc:
            return
        from ui.core.screens.close_document_dialog import CloseDocumentDialog
        dialog = CloseDocumentDialog(doc.name, self._window)
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return
        if dialog.result_code == CloseDocumentDialog.SAVE:
            current = self._dm.active_document()
            if current is not doc:
                self._dm.set_active_document(uid)
            # O documento só fecha depois do arquivo gravado e conferido: uma falha na gravação
            # o deixa aberto, com tudo o que foi pintado.
            self.save_active(then=lambda saved: self._dm.close_document(saved.uid))
            if current is not None and current is not doc:
                self._dm.set_active_document(current.uid)
        elif dialog.result_code == CloseDocumentDialog.DISCARD:
            self._dm.close_document(uid)

    def close_all_for_exit(self) -> bool:
        """Fecha tudo ao sair; False se o usuário manteve algum documento sujo aberto.

        Nunca encerra enquanto houver documento sujo sem decisão explícita.
        """
        for doc in list(self._dm.documents()):
            if doc.is_dirty:
                self.close_with_confirmation(doc.uid)
                self.wait_for_saves()  # "salvar e fechar" fecha quando a gravação termina
                if self._dm.get_document(doc.uid) is not None:
                    return False
        self.wait_for_saves()
        for doc in list(self._dm.documents()):
            if self._dm.get_document(doc.uid) is not None:
                self._dm.close_document(doc.uid)
        return True

    def _reset_view(self) -> None:
        if self._workspace is not None:
            self._workspace.reset_view()
