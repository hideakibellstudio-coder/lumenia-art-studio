"""
FilterAdjustmentDialog — Diálogo Principal de Criação de Camadas de Filtro & Ajuste
===================================================================================
Interface moderna de 2 colunas no padrão Lumenia V2 (inspirada no PluginsWindow):
  - Coluna da Esquerda: Lista/Galeria de Cards de Filtros (Cores, Iluminação, Efeitos).
  - Coluna da Direita: Inspector de Parâmetros com sliders e botões de controle (- / +).
100% modularizado conforme ARCcC e sem hardcodes de cores.
"""

from __future__ import annotations

from typing import List, Optional
from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.theme.manager import ThemeManager
from ui.core.icons import get_icon
from ui.core.dialogs.base_dialog import BaseFramelessDialog
from .filter_definitions import FILTER_DEFINITIONS
from .filter_card import FilterCard
from .filter_inspector import FilterInspector


class FilterAdjustmentDialog(BaseFramelessDialog):
    """Diálogo visual de 2 colunas para escolha e parametrização de filtros de camada."""

    filter_created = QtCore.Signal(str, int, list)
    preview_changed = QtCore.Signal(str, int, list)
    preview_cancelled = QtCore.Signal()

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
        initial_key: Optional[str] = None,
        initial_filter_id: Optional[str] = None
    ) -> None:
        super().__init__(
            title="Galeria de Filtros",
            icon_name="filter",
            parent=parent,
            modal=True
        )
        self.resize(780, 520)
        self.setMinimumSize(640, 440)

        target_key = initial_key or initial_filter_id
        matched = next((f for f in FILTER_DEFINITIONS if f["key"] == target_key or f.get("id") == target_key), None)
        self._active_def: dict = matched if matched else FILTER_DEFINITIONS[0]
        self._preview_timer = QtCore.QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(30)
        self._preview_timer.timeout.connect(self._dispatch_preview)

        self._build_two_column_ui()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

        # Seleciona o filtro ativo inicial
        self._select_filter(self._active_def)

    def _build_two_column_ui(self) -> None:
        cols_layout = QtWidgets.QHBoxLayout()
        cols_layout.setContentsMargins(12, 12, 12, 12)
        cols_layout.setSpacing(14)
        self.content_layout.addLayout(cols_layout)

        # ── Coluna Esquerda: Galeria de Cards ──────────────────────────────
        left_box = QtWidgets.QWidget(self)
        left_layout = QtWidgets.QVBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # Header da Galeria
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

        self.inspector = FilterInspector(self)
        self.inspector.params_changed.connect(lambda *_: self._schedule_preview())
        right_layout.addWidget(self.inspector, 1)

        # Botões de Ação
        btn_box = QtWidgets.QHBoxLayout()
        btn_box.setSpacing(8)

        self.btn_cancel = QtWidgets.QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self._on_cancel)

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
        self.inspector.set_filter_def(fdef)

    def _filter_cards(self, text: str) -> None:
        query = text.strip().lower()
        for card in self.cards:
            match = (
                query in card.filter_def["name"].lower()
                or query in card.filter_def["category"].lower()
                or query in card.filter_def["description"].lower()
            )
            card.setVisible(match)

    def _schedule_preview(self) -> None:
        self._preview_timer.start()

    def _dispatch_preview(self) -> None:
        name = self._active_def["name"]
        type_id = self._active_def["type_id"]
        params = self.get_current_params()
        self.preview_changed.emit(name, type_id, params)

    def get_current_params(self) -> list[float]:
        params = self.inspector.get_param_values()
        while len(params) < 8:
            params.append(0.0)
        return params

    def _create_layer(self) -> None:
        name = self._active_def["name"]
        type_id = self._active_def["type_id"]
        params = self.get_current_params()
        self.filter_created.emit(name, type_id, params)
        self.accept()

    def _on_cancel(self) -> None:
        self.preview_cancelled.emit()
        self.reject()

    def reject(self) -> None:
        self.preview_cancelled.emit()
        super().reject()

    def _apply_theme(self, *args) -> None:
        theme = ThemeManager.instance()
        bg_main = theme.get_color("bg_main")
        bg_panel = theme.get_color("bg_panel")
        bg_input = theme.get_color("bg_input")
        border = theme.get_color("border")
        text_main = theme.get_color("text_main")
        text_sec = theme.get_color("text_sec")
        accent = theme.get_color("accent")
        accent_hover = theme.get_color("accent_hover")
        text_on_accent = theme.get_color("text_on_accent")

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
                color: {text_on_accent};
                border-color: {accent};
            }}
        """)
        if hasattr(self, "title_lbl"):
            self.title_lbl.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {text_sec};")
        if hasattr(self, "v_line"):
            self.v_line.setStyleSheet(f"border: none; background-color: {border}; max-width: 1px;")
        if hasattr(self, "btn_apply"):
            self.btn_apply.setStyleSheet(f"""
                QPushButton {{
                    background-color: {accent};
                    color: {text_on_accent};
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
