"""Document — Representação de um documento aberto no Lumenia."""

from __future__ import annotations
from PySide6 import QtCore, QtGui
from .layer_manager import LocalLayerManager


class Document(QtCore.QObject):
    """Modelo de dados isolado de um documento MDI aberto."""

    geometry_changed = QtCore.Signal(int, int)

    def set_geometry(self, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("Dimensões inválidas.")
        if (self.width, self.height) != (width, height):
            self.width, self.height = width, height
            self.geometry_changed.emit(width, height)

    def __init__(self, uid: str, name: str, width: int = 1920, height: int = 1080):
        super().__init__()
        self.uid = uid
        self.name = name
        self.file_path: str | None = None
        self.format_id: str = "lmn"
        from .schema import CURRENT_VERSION
        self.format_version: int = CURRENT_VERSION
        self.width = max(1, width)
        self.height = max(1, height)

        # Gerenciador de camadas local do documento
        self.layer_manager = LocalLayerManager()
        self.layer_manager.document = self
        from .history import DocumentHistory
        self.history = DocumentHistory(self)

        # Posição da câmera no viewport
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.rotation = 0.0

        # Cor ativa e histórico
        self.saved_color: QtGui.QColor | None = None
        self.is_dirty: bool = False
        self.revision: int = 0
        self.dirty_reason: str | None = None

        # Papel de Fundo (Layer 0)
        self.paper_color = QtGui.QColor(255, 255, 255, 255)
        self.paper_visible = True
        self.paper_texture_id = 0
        self.paper_texture_enabled = False
        self.paper_scale = 1.0
        self.paper_contrast = 1.0
        self.paper_invert = False

        # Estados de Guias e Simetria específicos do documento
        self.guide_state: dict = {}
        self.sym_state: dict = {}

        # Camadas e histórico de preenchimento (Flood Fill) isolados
        self.flood_layers: list = []
        self.flood_redo_stack: list = []

        # Perfil de cor e Prova de Impressão (F-006)
        self.color_profile_id: int = 0
        self.color_profile_icc_bytes: bytes | None = None
        self.color_profile_name: str | None = None
        self.soft_proof_state: dict = {}

        # Qualquer mutação de camada invalida o estado salvo do documento.
        self.layer_manager.content_changed.connect(self._on_content_changed)
        self.layer_manager.layer_property_changed.connect(lambda _uid: self.mark_dirty("layer_property"))
        self.layer_manager.order_changed.connect(lambda: self.mark_dirty("layer_order"))

    def _on_content_changed(self, reason: str) -> None:
        self.mark_dirty(reason)

    def mark_dirty(self, reason: str = "content") -> None:
        self.revision += 1
        self.is_dirty = True
        self.dirty_reason = str(reason)

    def mark_saved(self, file_path: str | None = None) -> None:
        if file_path is not None:
            self.file_path = str(file_path)
        self.is_dirty = False
        self.dirty_reason = None
