"""
FilterAdjustmentDialog — Diálogo Principal de Criação de Camadas de Filtro & Ajuste
===================================================================================
Interface moderna de 2 colunas no padrão Lumenia V2 (inspirada no PluginsWindow):
  - Coluna da Esquerda: Lista/Galeria de Cards de Filtros (Cores, Iluminação, Efeitos).
  - Coluna da Direita: Inspector de Parâmetros com sliders e botões de controle (- / +).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.theme.manager import ThemeManager
from ui.core.widgets.slider.labeled_slider import LabeledSlider
from ui.core.icons import get_icon


FILTER_DEFINITIONS = [
    {
        "type_id": 0,
        "key": "huesat",
        "name": "Matiz / Saturação (HSV)",
        "category": "Cores",
        "icon": "cat_efeitos",
        "description": "Ajusta matiz, saturação e luminosidade das cores da imagem.",
        "params": [
            {"id": "hue", "label": "Matiz (Hue Shift)", "min": -180, "max": 180, "default": 0, "suffix": "°"},
            {"id": "sat", "label": "Saturação (Saturation)", "min": -100, "max": 100, "default": 0, "suffix": "%"},
            {"id": "light", "label": "Luminosidade (Lightness)", "min": -100, "max": 100, "default": 0, "suffix": "%"},
            {"id": "colorize", "label": "Modo Colorizar", "type": "bool", "default": False},
        ]
    },
    {
        "type_id": 1,
        "key": "brightness",
        "name": "Brilho, Contraste & Gama",
        "category": "Iluminação",
        "icon": "theme",
        "description": "Controle de exposição, nível de sombras, brilho e curva de gama.",
        "params": [
            {"id": "bright", "label": "Brilho (Brightness)", "min": -100, "max": 100, "default": 0, "suffix": "%"},
            {"id": "contrast", "label": "Contraste (Contrast)", "min": -100, "max": 100, "default": 0, "suffix": "%"},
            {"id": "gamma", "label": "Gama (Correction)", "min": 1, "max": 30, "default": 10, "factor": 10.0, "suffix": ""},
        ]
    },
    {
        "type_id": 3,
        "key": "colorbalance",
        "name": "Balanço de Cores / Níveis",
        "category": "Cores",
        "icon": "cat_efeitos",
        "description": "Ajuste independente dos canais Vermelho, Verde e Azul (RGB).",
        "params": [
            {"id": "red", "label": "Vermelho (Red)", "min": -100, "max": 100, "default": 0, "suffix": "%"},
            {"id": "green", "label": "Verde (Green)", "min": -100, "max": 100, "default": 0, "suffix": "%"},
            {"id": "blue", "label": "Azul (Blue)", "min": -100, "max": 100, "default": 0, "suffix": "%"},
        ]
    },
    {
        "type_id": 5,
        "key": "invert",
        "name": "Inversão & Limiar (Threshold)",
        "category": "Efeitos",
        "icon": "clean_layer",
        "description": "Inverte os canais de cor ou converte a imagem em alto contraste P&B.",
        "params": [
            {"id": "mode", "label": "Modo Inverter (vs Limiar)", "type": "bool", "default": True},
            {"id": "thresh", "label": "Corte de Limiar (Threshold)", "min": 0, "max": 255, "default": 128, "suffix": ""},
        ]
    },
    {
        "type_id": 6,
        "key": "pixelate",
        "name": "Pixelizar (Mosaico 8-Bits)",
        "category": "Efeitos",
        "icon": "cat_efeitos",
        "description": "Converte a imagem em blocos procedurais de pixels estilo retro 8-bits.",
        "params": [
            {"id": "block", "label": "Tamanho dos Blocos (Pixel Size)", "min": 2, "max": 64, "default": 8, "suffix": "px"},
        ]
    },
]


class FilterCard(QtWidgets.QFrame):
    """Cartão da lista esquerda representando um tipo de filtro."""

    selected = QtCore.Signal(dict)

    def __init__(self, filter_def: dict, is_selected: bool = False, parent=None):
        super().__init__(parent)
        self.filter_def = filter_def
        self.is_selected = is_selected
        self.setCursor(QtCore.Qt.PointingHandCursor)

        self._build_ui()
        ThemeManager.instance().themeChanged.connect(self.update_style)
        self.update_style()

    def _build_ui(self) -> None:
        self.setMinimumHeight(64)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        # Icon
        icon_lbl = QtWidgets.QLabel()
        icon_lbl.setFixedSize(32, 32)
        icon_lbl.setPixmap(get_icon(self.filter_def["icon"]).pixmap(32, 32))
        layout.addWidget(icon_lbl)

        # Info
        info_box = QtWidgets.QVBoxLayout()
        info_box.setSpacing(2)
        
        name_lbl = QtWidgets.QLabel(self.filter_def["name"])
        name_lbl.setStyleSheet("font-weight: bold; font-size: 12px;")
        
        desc_lbl = QtWidgets.QLabel(self.filter_def["description"])
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("font-size: 10px; color: #9ca3af;")

        info_box.addWidget(name_lbl)
        info_box.addWidget(desc_lbl)
        layout.addLayout(info_box, 1)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self.selected.emit(self.filter_def)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool) -> None:
        self.is_selected = selected
        self.update_style()

    def update_style(self, *args) -> None:
        theme = ThemeManager.instance()
        bg_panel = theme.get_color("bg_panel", "#1e1e24")
        border = theme.get_color("border", "#2e2e38")
        accent = theme.get_color("accent", "#6366f1")

        bg_color = theme.get_color("bg_hover", "#2a2a32") if self.is_selected else bg_panel
        border_color = accent if self.is_selected else border

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 6px;
            }}
            QFrame:hover {{
                border-color: {accent};
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)


class FilterAdjustmentDialog(QtWidgets.QDialog):
    """
    Diálogo principal de criação de Camadas de Ajuste e Filtros com visual de 2 colunas.
    """

    filter_created = QtCore.Signal(str, int, list)     # (name, type_id, params)
    preview_changed = QtCore.Signal(str, int, list)    # (name, type_id, params)
    preview_cancelled = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Filtros & Camadas de Ajuste (Não-Destrutivas)")
        self.resize(820, 500)
        self.setMinimumSize(740, 420)

        self._active_def: dict = FILTER_DEFINITIONS[0]
        self._param_widgets: Dict[str, Any] = {}

        self._build_ui()
        self._select_filter(FILTER_DEFINITIONS[0])

        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

    def _build_ui(self) -> None:
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # ── Coluna Esquerda: Galeria de Filtros ────────────────────────────
        left_box = QtWidgets.QWidget(self)
        left_layout = QtWidgets.QVBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # Header
        title_box = QtWidgets.QHBoxLayout()
        icon_gallery = QtWidgets.QLabel()
        icon_gallery.setFixedSize(16, 16)
        icon_gallery.setPixmap(get_icon("filter").pixmap(16, 16))
        title_lbl = QtWidgets.QLabel("GALERIA DE FILTROS")
        title_lbl.setStyleSheet("font-size: 13px; font-weight: bold; text-transform: uppercase;")
        title_box.addWidget(icon_gallery)
        title_box.addWidget(title_lbl)
        title_box.addStretch()
        left_layout.addLayout(title_box)

        # Search bar
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Pesquisar ajuste...")
        self.search_input.addAction(get_icon("search"), QtWidgets.QLineEdit.LeadingPosition)
        self.search_input.textChanged.connect(self._filter_cards)
        left_layout.addWidget(self.search_input)

        # Scroll area com cards
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        
        cards_widget = QtWidgets.QWidget()
        self.cards_layout = QtWidgets.QVBoxLayout(cards_widget)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(6)
        self.cards_layout.setAlignment(QtCore.Qt.AlignTop)

        self.cards: List[FilterCard] = []
        for fdef in FILTER_DEFINITIONS:
            card = FilterCard(fdef)
            card.selected.connect(self._select_filter)
            self.cards_layout.addWidget(card)
            self.cards.append(card)

        scroll.setWidget(cards_widget)
        left_layout.addWidget(scroll, 1)

        main_layout.addWidget(left_box, 4)

        # Divisor vertical
        v_line = QtWidgets.QFrame()
        v_line.setFrameShape(QtWidgets.QFrame.VLine)
        main_layout.addWidget(v_line)

        # ── Coluna Direita: Inspector de Parâmetros ────────────────────────
        right_box = QtWidgets.QWidget(self)
        right_layout = QtWidgets.QVBoxLayout(right_box)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        self.inspector_title = QtWidgets.QLabel("PARÂMETROS DO FILTRO")
        self.inspector_title.setStyleSheet("font-size: 13px; font-weight: bold;")
        right_layout.addWidget(self.inspector_title)

        self.inspector_desc = QtWidgets.QLabel("Ajuste os parâmetros abaixo para criar a camada.")
        self.inspector_desc.setWordWrap(True)
        self.inspector_desc.setStyleSheet("font-size: 11px; color: #9ca3af;")
        right_layout.addWidget(self.inspector_desc)

        # Container dos sliders dinâmicos
        self.params_container = QtWidgets.QScrollArea()
        self.params_container.setWidgetResizable(True)
        self.params_container.setFrameShape(QtWidgets.QFrame.NoFrame)
        
        self.params_inner = QtWidgets.QWidget()
        self.params_layout = QtWidgets.QVBoxLayout(self.params_inner)
        self.params_layout.setContentsMargins(0, 4, 0, 4)
        self.params_layout.setSpacing(12)
        self.params_layout.setAlignment(QtCore.Qt.AlignTop)

        self.params_container.setWidget(self.params_inner)
        right_layout.addWidget(self.params_container, 1)

        # Botões de Ação
        btn_box = QtWidgets.QHBoxLayout()
        btn_box.setSpacing(8)

        btn_cancel = QtWidgets.QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        
        self.btn_apply = QtWidgets.QPushButton("Criar Camada de Ajuste")
        self.btn_apply.setIcon(get_icon("plus"))
        self.btn_apply.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_apply.clicked.connect(self._create_layer)

        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(self.btn_apply)

        right_layout.addLayout(btn_box)
        main_layout.addWidget(right_box, 5)

    def _select_filter(self, fdef: dict) -> None:
        self._active_def = fdef
        for card in self.cards:
            card.set_selected(card.filter_def["key"] == fdef["key"])

        self.inspector_title.setText(fdef["name"].upper())
        self.inspector_desc.setText(fdef["description"])

        # Recontrói a lista de parâmetros na coluna da direita
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self._param_widgets.clear()

        for p in fdef["params"]:
            if p.get("type") == "bool":
                chk = QtWidgets.QCheckBox(p["label"])
                chk.setChecked(p["default"])
                chk.toggled.connect(self._emit_preview)
                self.params_layout.addWidget(chk)
                self._param_widgets[p["id"]] = chk
            else:
                slider = LabeledSlider(
                    p["label"],
                    p["min"],
                    p["max"],
                    p["default"],
                    value_suffix=p.get("suffix", "")
                )
                slider.valueChanged.connect(self._emit_preview)
                self.params_layout.addWidget(slider)
                self._param_widgets[p["id"]] = slider

        self._emit_preview()

    def _emit_preview(self, *args) -> None:
        name = self._active_def["name"]
        type_id = self._active_def["type_id"]
        params = self.get_current_params()
        self.preview_changed.emit(name, type_id, params)

    def reject(self) -> None:
        self.preview_cancelled.emit()
        super().reject()

    def _filter_cards(self, text: str) -> None:
        query = text.strip().lower()
        for card in self.cards:
            name = card.filter_def["name"].lower()
            desc = card.filter_def["description"].lower()
            card.setVisible(query in name or query in desc)

    def get_current_params(self) -> List[float]:
        result = []
        for p in self._active_def["params"]:
            w = self._param_widgets.get(p["id"])
            if w:
                if isinstance(w, QtWidgets.QCheckBox):
                    val = 1.0 if w.isChecked() else 0.0
                elif isinstance(w, LabeledSlider):
                    raw_val = float(w.value())
                    factor = p.get("factor", 1.0)
                    val = raw_val / factor if factor != 1.0 else raw_val
                else:
                    val = 0.0
                result.append(val)
        while len(result) < 8:
            result.append(0.0)
        return result

    def _create_layer(self) -> None:
        name = self._active_def["name"]
        type_id = self._active_def["type_id"]
        params = self.get_current_params()
        self.filter_created.emit(name, type_id, params)
        self.accept()

    def _apply_theme(self, *args) -> None:
        theme = ThemeManager.instance()
        bg_panel = theme.get_color("bg_panel", "#1e1e24")
        border = theme.get_color("border", "#2e2e38")
        text_main = theme.get_color("text_main", "#f3f4f6")
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_panel};
                color: {text_main};
            }}
            QLineEdit {{
                background-color: {theme.get_color('bg_main', '#121214')};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 4px 8px;
                color: {text_main};
            }}
        """)
