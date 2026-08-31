from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QToolButton
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QCursor
from ui.core.icons import get_icon
from ui.core.i18n import tr, I18nManager


class IconButton(QToolButton):
    def __init__(self, icon, tooltip="", parent=None, size=28, icon_size=18, checkable=False):
        super().__init__(parent)
        if icon: 
            self.setIcon(icon)
        self.setToolTip(tooltip)
        self.setFixedSize(size, size)
        self.setIconSize(QSize(icon_size, icon_size))
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setAutoRaise(True)
        if checkable: 
            self.setCheckable(True)


class GridActionButton(IconButton):
    def __init__(self, icon, tooltip="", parent=None):
        super().__init__(icon, tooltip, parent, size=32, icon_size=20)
        self.setProperty("class", "GridButton")


class LayersPrimaryBox(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(4)
        
        self.buttons = []
        self.btn_map = {}
        
        def add_separator():
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setFrameShadow(QFrame.Plain)
            line.setProperty("class", "GridSeparator")
            layout.addWidget(line)
        
        # --- Grupo 1: Criação e Exclusão ---
        self._add_btn(layout, "duplicate", tr("layers.duplicate", "Duplicar Camada"), self.controller.duplicate_selection)
        self._add_btn(layout, "clean-layer", tr("layers.clear_layer", "Limpar Camada"), self.controller.grid_clear)
        layout.addSpacing(2)
        add_separator()
        layout.addSpacing(2)
        
        # --- Grupo 2: Estrutura ---
        self._add_btn(layout, "folder", tr("layers.new_group", "Novo Grupo (G)"), lambda: self.controller.add_group(None))
        layout.addSpacing(2)
        add_separator()
        layout.addSpacing(2)
        
        # --- Grupo 3: Clipping e Bloqueios ---
        self._add_btn(layout, "clip-mask", tr("layers.clipping_mask", "Clipping Mask"), self.controller.grid_toggle_clip)
        self._add_btn(layout, "alpha-lock", tr("layers.alpha_lock", "Alpha Lock"), self.controller.grid_toggle_alpha)
        self._add_btn(layout, "lock", tr("layers.lock", "Bloquear Camada"), self.controller.grid_toggle_lock)

        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

    def _add_btn(self, layout, icon_name, tooltip, callback):
        icon = get_icon(icon_name)
        btn = GridActionButton(icon, tooltip)
        btn.setProperty("icon_name", icon_name)
        btn.setProperty("class", "PrimaryBoxButton")
        btn.setFixedSize(28, 28)
        btn.setIconSize(QSize(16, 16))
        btn.clicked.connect(callback)
        layout.addWidget(btn)
        self.buttons.append(btn)
        self.btn_map[icon_name] = btn

    def retranslate_ui(self):
        if "duplicate" in self.btn_map:
            self.btn_map["duplicate"].setToolTip(tr("layers.duplicate", "Duplicar Camada"))
        if "clean-layer" in self.btn_map:
            self.btn_map["clean-layer"].setToolTip(tr("layers.clear_layer", "Limpar Camada"))
        if "folder" in self.btn_map:
            self.btn_map["folder"].setToolTip(tr("layers.new_group", "Novo Grupo (G)"))
        if "clip-mask" in self.btn_map:
            self.btn_map["clip-mask"].setToolTip(tr("layers.clipping_mask", "Clipping Mask"))
        if "alpha-lock" in self.btn_map:
            self.btn_map["alpha-lock"].setToolTip(tr("layers.alpha_lock", "Alpha Lock"))
        if "lock" in self.btn_map:
            self.btn_map["lock"].setToolTip(tr("layers.lock", "Bloquear Camada"))


class LayersSecondaryBar(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        
        self.buttons = []
        self.btn_map = {}

        actions = [
            ("plus", tr("layers.new_layer", "Nova Camada"), lambda: self.controller.add_layer(None)),
            ("trash", tr("layers.delete", "Deletar Camada"), self.controller.delete_selection),
            ("chevron-up", tr("layers.move_up", "Mover Cima"), self.controller.move_up),
            ("chevron-down", tr("layers.move_down", "Mover Baixo"), self.controller.move_down),
            ("merge", tr("layers.merge_down", "Mesclar para Baixo"), self.controller.merge_down),
            ("sliders", tr("layers.add_filter", "Adicionar Filtro"), self.controller.add_filter_layer)
        ]
        
        for icon_name, tooltip, callback in actions:
            icon = get_icon(icon_name)
            btn = GridActionButton(icon, tooltip)
            btn.setProperty("icon_name", icon_name)
            btn.setProperty("class", "SecondaryBarButton")
            btn.setFixedSize(24, 24)
            btn.setIconSize(QSize(14, 14))
            btn.clicked.connect(callback)
            layout.addWidget(btn)
            self.buttons.append(btn)
            self.btn_map[icon_name] = btn
            
        layout.addStretch()
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

    def retranslate_ui(self):
        if "plus" in self.btn_map:
            self.btn_map["plus"].setToolTip(tr("layers.new_layer", "Nova Camada"))
        if "trash" in self.btn_map:
            self.btn_map["trash"].setToolTip(tr("layers.delete", "Deletar Camada"))
        if "chevron-up" in self.btn_map:
            self.btn_map["chevron-up"].setToolTip(tr("layers.move_up", "Mover Cima"))
        if "chevron-down" in self.btn_map:
            self.btn_map["chevron-down"].setToolTip(tr("layers.move_down", "Mover Baixo"))
        if "merge" in self.btn_map:
            self.btn_map["merge"].setToolTip(tr("layers.merge_down", "Mesclar para Baixo"))
        if "sliders" in self.btn_map:
            self.btn_map["sliders"].setToolTip(tr("layers.add_filter", "Adicionar Filtro"))
