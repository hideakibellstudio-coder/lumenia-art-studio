"""
PresetGallery — coluna de presets do diálogo de Novo Documento.
===============================================================
Abas de categoria (Ilustração, Web, Social, Cinema) e os cards da categoria
ativa. Clicar num card emite `presetChosen(largura, altura, dpi)`; o diálogo
avisa as medidas digitadas por `match(...)`, e a galeria marca o card que
corresponde (em qualquer orientação) ou nenhum.

Separada do `NewDocumentDialog` em 2026-09-24 (o diálogo estava na parede dos
450 linhas com a galeria e o formulário juntos).
"""
from __future__ import annotations

from typing import List, Optional

from PySide6 import QtCore, QtWidgets

from ui.core.i18n import tr

from .preset_card import PresetCard
from .preset_catalog import PRESET_CATEGORIES


class PresetGallery(QtWidgets.QWidget):
    presetChosen = QtCore.Signal(int, int, int)  # largura, altura, dpi

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._category_keys = list(PRESET_CATEGORIES.keys())
        self._category = self._category_keys[0]
        self._selected_id: Optional[str] = None
        self._cards: List[PresetCard] = []

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        title = QtWidgets.QLabel(tr("dialogs.presets_title", "PRESETS DE PROJETO"))
        title.setStyleSheet("font-size: 10px; font-weight: bold;")
        layout.addWidget(title)

        self.tab_categories = QtWidgets.QTabBar()
        self.tab_categories.setExpanding(False)
        self.tab_categories.setCursor(QtCore.Qt.PointingHandCursor)
        for key in self._category_keys:
            self.tab_categories.addTab(PRESET_CATEGORIES[key]["name"])
        self.tab_categories.currentChanged.connect(self._on_category_changed)
        layout.addWidget(self.tab_categories)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self._cards_container = QtWidgets.QWidget()
        self._cards_layout = QtWidgets.QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0, 4, 6, 4)
        self._cards_layout.setSpacing(6)
        scroll.setWidget(self._cards_container)
        layout.addWidget(scroll, 1)

        self._show_category(self._category)
        if self._cards:  # começa com o primeiro preset da primeira categoria
            self._selected_id = self._cards[0].preset_id
            self._cards[0].set_selected(True)

    # ── Leitura ───────────────────────────────────────────────────────────

    @property
    def category(self) -> str:
        return self._category

    @property
    def selected_preset_id(self) -> Optional[str]:
        return self._selected_id

    @property
    def cards(self) -> List[PresetCard]:
        return list(self._cards)

    # ── Medidas digitadas → card marcado ─────────────────────────────────

    def match(self, width: int, height: int, dpi: int) -> None:
        """Marca o card com essas medidas (retrato ou paisagem); sem par, nenhum."""
        self._selected_id = None
        for card in self._cards:
            same = card.p_dpi == dpi and (width, height) in (
                (card.p_width, card.p_height), (card.p_height, card.p_width))
            card.set_selected(same)
            if same:
                self._selected_id = card.preset_id

    # ── Interno ──────────────────────────────────────────────────────────

    def _on_category_changed(self, index: int) -> None:
        if 0 <= index < len(self._category_keys):
            self._category = self._category_keys[index]
            self._show_category(self._category)

    def _show_category(self, key: str) -> None:
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cards.clear()
        for pid, name, w, h, dpi, icon_name, desc in PRESET_CATEGORIES.get(key, {}).get("presets", []):
            card = PresetCard(preset_id=pid, name=name, width=w, height=h, dpi=dpi,
                              icon_name=icon_name, description=desc, parent=self._cards_container)
            card.clicked.connect(self._on_card_clicked)
            card.set_selected(pid == self._selected_id)
            self._cards_layout.addWidget(card)
            self._cards.append(card)
        self._cards_layout.addStretch()

    def _on_card_clicked(self, pid: str, width: int, height: int, dpi: int) -> None:
        self._selected_id = pid
        for card in self._cards:
            card.set_selected(card.preset_id == pid)
        self.presetChosen.emit(width, height, dpi)
