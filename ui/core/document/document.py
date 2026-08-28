"""Document — Representação de um documento aberto no Lumenia."""

from __future__ import annotations
from PySide6 import QtCore, QtGui
from plugins.ui.layers_plugin.manager import LocalLayerManager


class Document(QtCore.QObject):
    """Modelo de dados isolado de um documento MDI aberto."""

    def __init__(self, uid: str, name: str, width: int = 1920, height: int = 1080):
        super().__init__()
        self.uid = uid
        self.name = name
        self.width = max(1, width)
        self.height = max(1, height)

        # Gerenciador de camadas local do documento
        self.layer_manager = LocalLayerManager()

        # Posição da câmera no viewport
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.rotation = 0.0

        # Cor ativa e histórico
        self.saved_color: QtGui.QColor | None = None
        self.is_dirty: bool = False

        # Papel de Fundo (Layer 0)
        self.paper_color = QtGui.QColor(255, 255, 255, 255)
        self.paper_visible = True
        self.paper_texture_id = 0
        self.paper_texture_enabled = False

        # Estados de Guias e Simetria específicos do documento
        self.guide_state: dict = {}
        self.sym_state: dict = {}

        # Camadas e histórico de preenchimento (Flood Fill) isolados
        self.flood_layers: list = []
        self.flood_redo_stack: list = []
