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
from ui.core.dialogs.base_dialog import BaseFramelessDialog


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
        
        self.name_lbl = QtWidgets.QLabel(self.filter_def["name"])
        self.name_lbl.setStyleSheet("font-size: 13px; font-weight: bold;")
        
        self.desc_lbl = QtWidgets.QLabel(self.filter_def.get("description", ""))
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setStyleSheet("font-size: 11px;")

        info_box.addWidget(self.name_lbl)
        info_box.addWidget(self.desc_lbl)
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
        bg_card = theme.get_color("bg_card", "#1e1e24")
        border = theme.get_color("border", "#2e2e38")
        accent = theme.get_color("accent", "#6366f1")
        text_main = theme.get_color("text_main", "#f3f4f6")
        text_sec = theme.get_color("text_sec", "#9ca3af")

        bg_color = theme.get_color("bg_hover", "#2a2a32") if self.is_selected else bg_card
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
        if hasattr(self, "name_lbl"):
            self.name_lbl.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {text_main};")
        if hasattr(self, "desc_lbl"):
            self.desc_lbl.setStyleSheet(f"font-size: 11px; color: {text_sec};")


class FilterAdjustmentDialog(BaseFramelessDialog):
    """
    Diálogo principal de criação de Camadas de Ajuste e Filtros com visual de 2 colunas.
    """

    filter_created = QtCore.Signal(str, int, list)     # (name, type_id, params)
    preview_changed = QtCore.Signal(str, int, list)    # (name, type_id, params)
    preview_cancelled = QtCore.Signal()

    def __init__(self, parent=None, initial_key: str | None = None):
        super().__init__(title="Filtros & Camadas de Ajuste", icon_name="filter", parent=parent, modal=True)
        self.resize(840, 520)
        self.setMinimumSize(760, 440)

        target_def = FILTER_DEFINITIONS[0]
        if initial_key:
            for fdef in FILTER_DEFINITIONS:
                if fdef.get("key") == initial_key:
                    target_def = fdef
                    break

        self._active_def: dict = target_def
        self._param_widgets: Dict[str, Any] = {}

        self._preview_timer = QtCore.QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(16)
        self._preview_timer.timeout.connect(self._do_emit_preview)

        self._build_ui()
        self._select_filter(target_def)

        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

    def _build_ui(self) -> None:
        cols_widget = QtWidgets.QWidget()
        cols_layout = QtWidgets.QHBoxLayout(cols_widget)
        cols_layout.setContentsMargins(0, 0, 0, 0)
        cols_layout.setSpacing(12)
        self.content_layout.addWidget(cols_widget, 1)

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
        self.title_lbl = QtWidgets.QLabel("GALERIA DE FILTROS")
        self.title_lbl.setStyleSheet("font-size: 13px; font-weight: bold; text-transform: uppercase;")
        title_box.addWidget(icon_gallery)
        title_box.addWidget(self.title_lbl)
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

        cols_layout.addWidget(left_box, 4)

        # Divisor vertical
        self.v_line = QtWidgets.QFrame()
        self.v_line.setFrameShape(QtWidgets.QFrame.VLine)
        cols_layout.addWidget(self.v_line)

        # ── Coluna Direita: Inspector de Parâmetros ────────────────────────
        right_box = QtWidgets.QWidget(self)
        right_layout = QtWidgets.QVBoxLayout(right_box)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        self.inspector_title = QtWidgets.QLabel("PARÂMETROS DO FILTRO")
        self.inspector_title.setProperty("heading", "true")
        right_layout.addWidget(self.inspector_title)

        self.inspector_desc = QtWidgets.QLabel("Ajuste os parâmetros abaixo para criar a camada.")
        self.inspector_desc.setWordWrap(True)
        self.inspector_desc.setProperty("muted", "true")
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

        self.btn_cancel = QtWidgets.QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_apply = QtWidgets.QPushButton("Criar Camada de Ajuste")
        self.btn_apply.setIcon(get_icon("plus"))
        self.btn_apply.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_apply.clicked.connect(self._create_layer)

        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_apply)

        right_layout.addLayout(btn_box)
        cols_layout.addWidget(right_box, 5)

        from ui.core.i18n import I18nManager
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        from ui.core.i18n import tr
        title = tr("filters.gallery", "Galeria de Filtros")
        self.setWindowTitle(title)
        if hasattr(self, "title_bar") and self.title_bar:
            self.title_bar.set_title(title)
        if hasattr(self, "title_lbl"):
            self.title_lbl.setText(tr("filters.gallery", "GALERIA DE FILTROS").upper())
        if hasattr(self, "search_input"):
            self.search_input.setPlaceholderText(tr("filters.search_placeholder", "Pesquisar ajuste..."))
        if hasattr(self, "btn_cancel"):
            self.btn_cancel.setText(tr("dialogs.cancel", "Cancelar"))
        if hasattr(self, "btn_apply"):
            self.btn_apply.setText(tr("filters.create_adjustment_layer", "Criar Camada de Ajuste"))

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

        self._do_emit_preview()

    def _emit_preview(self, *args) -> None:
        if not self._active_def:
            return
        if not self._preview_timer.isActive():
            self._preview_timer.start()

    def _do_emit_preview(self) -> None:
        if not self._active_def:
            return
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

    def get_current_params(self) -> list[float]:
        if not self._active_def:
            return [0.0] * 8
        result = []
        for p in self._active_def["params"]:
            pid = p["id"]
            w = self._param_widgets.get(pid)
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
        bg_main = theme.get_color("bg_main", "#0f172a")
        bg_panel = theme.get_color("bg_panel", "#1e1e24")
        bg_card = theme.get_color("bg_card", "#1e1e24")
        bg_input = theme.get_color("bg_input", "#121214")
        border = theme.get_color("border", "#2e2e38")
        text_main = theme.get_color("text_main", "#f3f4f6")
        text_sec = theme.get_color("text_sec", "#9ca3af")
        accent = theme.get_color("accent", "#6366f1")
        accent_hover = theme.get_color("accent_hover", "#4f46e5")

        if hasattr(self, "root_container") and self.root_container:
            self.root_container.setStyleSheet(f"""
                QWidget#DialogRootContainer {{
                    background-color: {bg_main};
                    border: 1px solid {border};
                    border-radius: 10px;
                }}
                QFrame#DialogHeaderSep {{
                    background-color: {border};
                    border: none;
                }}
            """)

        self.setStyleSheet(f"""
            QLabel {{ color: {text_main}; }}
            QLineEdit {{
                background-color: {bg_input};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 10px;
                color: {text_main};
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border-color: {accent};
            }}
            QPushButton {{
                background-color: {bg_panel};
                color: {text_main};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {accent};
                color: #ffffff;
                border-color: {accent};
            }}
        """)
        if hasattr(self, "title_lbl"):
            self.title_lbl.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {text_sec};")
        if hasattr(self, "inspector_title"):
            self.inspector_title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {text_main};")
        if hasattr(self, "inspector_desc"):
            self.inspector_desc.setStyleSheet(f"font-size: 11px; color: {text_sec};")
        if hasattr(self, "v_line"):
            self.v_line.setStyleSheet(f"border: none; background-color: {border}; max-width: 1px;")
        if hasattr(self, "btn_apply"):
            self.btn_apply.setStyleSheet(f"""
                QPushButton {{
                    background-color: {accent};
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    padding: 6px 14px;
                    font-size: 11px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {accent_hover};
                }}
            """)
