"""DocumentViewSync — o canvas mostra o documento ativo; câmera ↔ navegador.

Ao trocar de documento: guarda a câmera, a cor e as guias do anterior,
aponta o motor para o contexto do novo, restaura câmera, guias, papel e cor
dele e avisa os painéis. Também converte a câmera do canvas em coordenadas
normalizadas do navegador e vice-versa.

Fala com os painéis só por sinais (o `WorkspaceContainer` liga cada painel
em `add_panel`, pelo `PanelConnections`). Antes era o mixin
`WorkspaceDocSyncMixin`, que guardava referências aos painéis de outros
plugins, perguntava `hasattr(self, "_layers_panel")` e escrevia no widget de
papel do painel de camadas por dentro.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from PySide6 import QtCore

from ui.core.document.document import Document
from ui.core.document.manager import DocumentManager
from ui.core.document.paper_backend_sync import sync_paper_to_backend
from ui.core.engine.errors import EngineContextError
from ui.infrastructure.i18n import tr
from ui.core.state import BrushEngineSync, BrushState

from .canvas.render_widget import RenderWidget

logger = logging.getLogger(__name__)


class DocumentViewSync(QtCore.QObject):
    # Painel de camadas: gerenciador do documento ativo (None = sem documento).
    layerManagerChanged = QtCore.Signal(object)
    # Navegador.
    hasDocumentChanged = QtCore.Signal(bool)
    canvasSizeChanged = QtCore.Signal(int, int)
    # zoom, x e y normalizados, rotação, espelho h/v, fração visível w/h
    viewportChanged = QtCore.Signal(float, float, float, float, bool, bool, float, float)
    # O motor não conseguiu criar o contexto do documento: texto para o usuário.
    contextFailed = QtCore.Signal(str)

    def __init__(
        self,
        canvas: RenderWidget,
        show_tab: Callable[[str], None],
        dm: DocumentManager,
        brush: BrushState,
        brush_sync: BrushEngineSync,
        backend: Callable[[], Any],
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._canvas = canvas
        self._show_tab = show_tab
        self._dm = dm
        self._brush = brush
        self._brush_sync = brush_sync
        self._backend = backend
        self._last_uid: Optional[str] = None
        self._geometry_document: Optional[Document] = None
        dm.activeDocumentChanged.connect(self.show_document)
        dm.documentClosed.connect(self._on_document_closed)
        canvas.cameraChanged.connect(self._on_canvas_camera_changed)

    # ── Troca de documento ────────────────────────────────────────────────

    def show_document(self, doc: Optional[Document], *, capture_previous: bool = True) -> None:
        """Mostra `doc` no canvas (ligado a `DocumentManager.activeDocumentChanged`)."""
        self._watch_geometry(doc)
        if self._canvas.transform_ctrl.active:
            self._canvas.transform_ctrl.cancel()
        if capture_previous and self._last_uid:
            self._capture_view(self._dm.get_document(self._last_uid))
        self._last_uid = doc.uid if doc else None

        if doc is None:
            self._canvas.setEnabled(False)
            self.layerManagerChanged.emit(None)
            self.hasDocumentChanged.emit(False)
            self._canvas.update()  # sem documento o renderer desenha a tela vazia
            return

        backend = self._backend()
        if backend is not None:
            try:
                backend.set_active_document_context(doc.uid, doc.width, doc.height)
            except EngineContextError as exc:
                self._reject_document(doc, exc)
                return
        sync_paper_to_backend(doc)
        canvas = self._canvas
        canvas.setEnabled(True)
        canvas.canvas_w, canvas.canvas_h = doc.width, doc.height
        canvas.geometry_ctrl.load_document_state(doc)
        self._show_tab(doc.uid)
        if doc.zoom == 1.0 and doc.pan_x == 0.0 and doc.pan_y == 0.0:
            canvas.center_canvas()
        else:
            canvas.zoom, canvas.pan_x, canvas.pan_y, canvas.rotation = doc.zoom, doc.pan_x, doc.pan_y, doc.rotation
            canvas.publish_view(zoom_changed=True)

        # Cada documento lembra a última cor usada nele; os painéis de cor se
        # atualizam sozinhos pelo sinal do BrushState.
        if doc.saved_color:
            self._brush.set_color(doc.saved_color)

        self.layerManagerChanged.emit(doc.layer_manager)
        self.canvasSizeChanged.emit(doc.width, doc.height)
        self.hasDocumentChanged.emit(True)
        self.sync_navigator()

        manager = doc.layer_manager
        if backend is not None and manager.get_active_layer() is not None:
            backend.select_layer(manager.active_index)

        # A facade nativa deste documento recebeu do adaptador o perfil da aba
        # anterior; reenvia os valores do BrushState por cima.
        self._brush_sync.resync()

    def _reject_document(self, doc: Document, error: EngineContextError) -> None:
        """O motor não pode hospedar `doc`: ele não fica aberto nem ativo.

        Um documento sem contexto próprio faria traços, colagens e a restauração
        de arquivo caírem no contexto que estava ativo, o documento do usuário.
        Quem cria o documento confere `get_active_document_context() == doc.uid`
        antes de seguir; o fechamento fica para depois desta emissão do sinal,
        porque os outros ouvintes de `activeDocumentChanged` ainda vão receber
        `doc` e fechá-lo aqui os faria observar um documento já removido.
        """
        logger.error("[DocumentViewSync] Documento '%s' recusado: %s", doc.uid, error)
        reason = tr("status.engine_out_of_memory", "memória insuficiente") if error.out_of_memory else str(error)
        message = tr(
            "status.doc_context_failed",
            "O motor não conseguiu criar o documento '{name}' ({w}×{h} px): {reason}. "
            "O documento atual foi mantido.",
            name=doc.name, w=doc.width, h=doc.height, reason=reason)
        QtCore.QTimer.singleShot(0, self, lambda: self._finish_rejection(doc.uid, message))

    def _finish_rejection(self, uid: str, message: str) -> None:
        self._dm.close_document(uid)
        self.contextFailed.emit(message)

    def _capture_view(self, doc: Optional[Document]) -> None:
        if doc is None:
            return
        canvas = self._canvas
        doc.zoom, doc.pan_x, doc.pan_y, doc.rotation = canvas.zoom, canvas.pan_x, canvas.pan_y, canvas.rotation
        doc.saved_color = self._brush.color
        doc.guide_state = dict(canvas.geometry_ctrl.guide_state)
        doc.sym_state = dict(canvas.geometry_ctrl.sym_state)

    def _watch_geometry(self, doc: Optional[Document]) -> None:
        if self._geometry_document is not None:
            self._geometry_document.geometry_changed.disconnect(self._on_geometry_changed)
        self._geometry_document = doc
        if doc is not None:
            doc.geometry_changed.connect(self._on_geometry_changed)

    def _on_geometry_changed(self, width: int, height: int) -> None:
        self._canvas.canvas_w, self._canvas.canvas_h = width, height
        self.canvasSizeChanged.emit(width, height)
        self.sync_navigator()
        self._canvas.update()

    def _on_document_closed(self, uid: str) -> None:
        """Libera a memória C++ do documento fechado imediatamente."""
        backend = self._backend()
        if backend is not None:
            backend.close_document_context(uid)

    # ── Câmera ↔ navegador ────────────────────────────────────────────────

    def sync_navigator(self) -> None:
        """Empurra a câmera atual do canvas para o navegador."""
        c = self._canvas
        self._on_canvas_camera_changed(
            c.zoom, c.pan_x, c.pan_y, c.rotation, float(max(1, c.width())), float(max(1, c.height()))
        )

    def _on_canvas_camera_changed(self, zoom, pan_x, pan_y, rotation, view_w, view_h) -> None:
        doc = self._dm.active_document()
        if doc is not None:
            doc.zoom, doc.pan_x, doc.pan_y, doc.rotation = zoom, pan_x, pan_y, rotation
        doc_w, doc_h = float(self._canvas.canvas_w), float(self._canvas.canvas_h)
        self.viewportChanged.emit(
            zoom,
            0.5 - pan_x / (zoom * doc_w),
            0.5 - pan_y / (zoom * doc_h),
            rotation,
            bool(self._canvas.flip_x),
            bool(self._canvas.flip_y),
            view_w / (zoom * doc_w),
            view_h / (zoom * doc_h),
        )

    def set_camera_from_navigator(self, zoom: float, norm_x: float, norm_y: float, rotation: float) -> None:
        """Coordenadas normalizadas do navegador → câmera do canvas."""
        c = self._canvas
        c.zoom = zoom
        c.pan_x = (0.5 - norm_x) * zoom * float(c.canvas_w)
        c.pan_y = (0.5 - norm_y) * zoom * float(c.canvas_h)
        c.rotation = rotation
        # A mudança veio do navegador: não devolve cameraChanged para ele.
        c.publish_view(zoom_changed=True, notify_camera=False)

    def set_flip_from_navigator(self, flip_x: bool, flip_y: bool) -> None:
        self._canvas.flip_x = bool(flip_x)
        self._canvas.flip_y = bool(flip_y)
        self._canvas.update()
