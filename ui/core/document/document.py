from PySide6 import QtCore

from plugins.ui.layers_plugin.manager import LocalLayerManager



class Document(QtCore.QObject):
    def __init__(self, uid: str, name: str, width: int = 1920, height: int = 1080):
        super().__init__()
        self.uid = uid
        self.name = name
        self.width = width
        self.height = height
        
        # Cada documento possui seu próprio gerenciador de camadas local
        self.layer_manager = LocalLayerManager()
        
        # Posição da câmera local
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.rotation = 0.0
        
        # Cor ativa salva
        self.saved_color = None

        # Papel de Fundo (Layer 0)
        from PySide6.QtGui import QColor
        self.paper_color = QColor(255, 255, 255, 255)
        self.paper_visible = True
        self.paper_texture_id = 0
        self.paper_texture_enabled = False
