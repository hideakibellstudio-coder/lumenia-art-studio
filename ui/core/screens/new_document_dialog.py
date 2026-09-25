"""
NewDocumentDialog — Diálogo Moderno de Novo Documento (Lumenia V2)
===================================================================
Interface profissional de 2 colunas no padrão Lumenia V2:
  - Coluna da Esquerda: Abas de categorias (Ilustração, Web, Social, Cinema) com cards visuais interativos.
  - Coluna da Direita: Dimensões, inversão de orientação rápida, resolução DPI, perfis de cor e papel de fundo.
  - Rodapé: Estimativa dinâmica de consumo de memória RAM e botões de ação.

A coluna de presets é o `PresetGallery` (new_document/preset_gallery.py):
clicar num card preenche as medidas; medidas digitadas marcam o card que
corresponde.
"""

from __future__ import annotations
from typing import Dict, Optional, Any
from PySide6 import QtCore, QtGui, QtWidgets

from ui.infrastructure.theme.manager import ThemeManager
from ui.infrastructure.icons import get_icon
from ui.core.dialogs.base_dialog import BaseFramelessDialog
from ui.infrastructure.i18n import tr
from .new_document import (
    BACKGROUND_COLORS,
    PAPER_TEXTURES,
    COLOR_PROFILES,
    estimate_ram_usage_mb,
    PresetGallery,
)


class NewDocumentDialog(BaseFramelessDialog):
    """Diálogo enriquecido para criação de novo documento com cards visuais de presets."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(title=tr("dialogs.new_document_title", "Novo Documento"), icon_name="document", parent=parent, modal=True)
        self.resize(780, 540)
        self.setMinimumSize(720, 490)

        self._build_ui()
        self._update_ram_estimate()

        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

    def _build_ui(self):
        # ── Área Central de 2 Colunas ─────────────────────────────────
        content_split = QtWidgets.QHBoxLayout()
        content_split.setSpacing(14)

        # === COLUNA ESQUERDA: CATÁLOGO DE PRESETS ====================
        self.gallery = PresetGallery()
        self.gallery.presetChosen.connect(self._on_preset_chosen)
        content_split.addWidget(self.gallery, 11)

        # Divisor Vertical
        v_sep = QtWidgets.QFrame()
        v_sep.setFrameShape(QtWidgets.QFrame.VLine)
        v_sep.setObjectName("DialogDivider")
        content_split.addWidget(v_sep)

        # === COLUNA DIREITA: DETALHES E PROPRIEDADES ==================
        right_col = QtWidgets.QVBoxLayout()
        right_col.setSpacing(10)

        # 1. Nome do Documento
        row_name = QtWidgets.QHBoxLayout()
        row_name.setSpacing(8)
        lbl_name = QtWidgets.QLabel(f"{tr('dialogs.doc_name', 'Nome')}:")
        lbl_name.setStyleSheet("font-size: 11px; font-weight: bold;")
        self.txt_name = QtWidgets.QLineEdit(tr("dialogs.untitled_doc", "Sem Título-1"))
        self.txt_name.setFixedHeight(26)
        row_name.addWidget(lbl_name)
        row_name.addWidget(self.txt_name, 1)
        right_col.addLayout(row_name)

        # 2. Grupo: Dimensões do Canvas
        grp_dim = QtWidgets.QGroupBox(tr("dialogs.canvas_dimensions", "Dimensões do Canvas"))
        lay_dim = QtWidgets.QVBoxLayout(grp_dim)
        lay_dim.setContentsMargins(10, 10, 10, 10)
        lay_dim.setSpacing(8)

        # Largura & Altura com botão Swap
        row_wh = QtWidgets.QHBoxLayout()
        row_wh.setSpacing(8)

        # Largura
        v_w = QtWidgets.QVBoxLayout()
        v_w.setSpacing(2)
        lbl_w = QtWidgets.QLabel(f"{tr('dialogs.width', 'Largura')}:")
        lbl_w.setStyleSheet("font-size: 10px;")
        self.spn_width = QtWidgets.QSpinBox()
        self.spn_width.setRange(100, 16384)
        self.spn_width.setValue(2480)
        self.spn_width.setSuffix(" px")
        self.spn_width.setFixedHeight(26)
        self.spn_width.valueChanged.connect(self._on_dimension_changed)
        v_w.addWidget(lbl_w)
        v_w.addWidget(self.spn_width)
        row_wh.addLayout(v_w, 1)

        # Botão Swap Orientação
        self.btn_swap_orient = QtWidgets.QToolButton()
        self.btn_swap_orient.setFixedSize(30, 26)
        self.btn_swap_orient.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_swap_orient.setToolTip(tr("dialogs.swap_orientation", "Alternar Orientação (Paisagem ⤨ Retrato)"))
        self.btn_swap_orient.clicked.connect(self._on_swap_orientation)
        v_btn = QtWidgets.QVBoxLayout()
        v_btn.setContentsMargins(0, 12, 0, 0)
        v_btn.addWidget(self.btn_swap_orient)
        row_wh.addLayout(v_btn)

        # Altura
        v_h = QtWidgets.QVBoxLayout()
        v_h.setSpacing(2)
        lbl_h = QtWidgets.QLabel(f"{tr('dialogs.height', 'Altura')}:")
        lbl_h.setStyleSheet("font-size: 10px;")
        self.spn_height = QtWidgets.QSpinBox()
        self.spn_height.setRange(100, 16384)
        self.spn_height.setValue(3508)
        self.spn_height.setSuffix(" px")
        self.spn_height.setFixedHeight(26)
        self.spn_height.valueChanged.connect(self._on_dimension_changed)
        v_h.addWidget(lbl_h)
        v_h.addWidget(self.spn_height)
        row_wh.addLayout(v_h, 1)

        lay_dim.addLayout(row_wh)

        # Resolução DPI
        row_dpi = QtWidgets.QHBoxLayout()
        row_dpi.setSpacing(8)
        lbl_dpi = QtWidgets.QLabel(f"{tr('dialogs.resolution', 'Resolução')}:")
        lbl_dpi.setStyleSheet("font-size: 10px;")
        self.spn_dpi = QtWidgets.QSpinBox()
        self.spn_dpi.setRange(72, 1200)
        self.spn_dpi.setValue(300)
        self.spn_dpi.setSuffix(" DPI")
        self.spn_dpi.setFixedHeight(24)
        self.spn_dpi.valueChanged.connect(self._on_dpi_changed)
        row_dpi.addWidget(lbl_dpi)
        row_dpi.addWidget(self.spn_dpi, 1)
        lay_dim.addLayout(row_dpi)

        # Perfil de Cor
        row_prof = QtWidgets.QHBoxLayout()
        row_prof.setSpacing(8)
        lbl_prof = QtWidgets.QLabel(f"{tr('dialogs.color_space', 'Espaço de Cor')}:")
        lbl_prof.setStyleSheet("font-size: 10px;")
        self.cmb_color_prof = QtWidgets.QComboBox()
        self.cmb_color_prof.setFixedHeight(24)
        for pid, name in COLOR_PROFILES:
            self.cmb_color_prof.addItem(name, pid)
        row_prof.addWidget(lbl_prof)
        row_prof.addWidget(self.cmb_color_prof, 1)
        lay_dim.addLayout(row_prof)

        right_col.addWidget(grp_dim)

        # 3. Grupo: Papel de Fundo (Layer 0)
        grp_paper = QtWidgets.QGroupBox(tr("dialogs.paper_background", "Papel de Fundo (Layer 0)"))
        lay_paper = QtWidgets.QVBoxLayout(grp_paper)
        lay_paper.setContentsMargins(10, 10, 10, 10)
        lay_paper.setSpacing(8)

        row_bg = QtWidgets.QHBoxLayout()
        row_bg.setSpacing(8)
        lbl_bg = QtWidgets.QLabel(f"{tr('dialogs.paper_color', 'Cor')}:")
        lbl_bg.setStyleSheet("font-size: 10px;")
        self.cmb_bg_color = QtWidgets.QComboBox()
        self.cmb_bg_color.setFixedHeight(24)
        for name, color in BACKGROUND_COLORS:
            self.cmb_bg_color.addItem(name, color)
        row_bg.addWidget(lbl_bg)
        row_bg.addWidget(self.cmb_bg_color, 1)
        lay_paper.addLayout(row_bg)

        row_tex = QtWidgets.QHBoxLayout()
        row_tex.setSpacing(8)
        lbl_tex = QtWidgets.QLabel(f"{tr('dialogs.paper_texture', 'Textura')}:")
        lbl_tex.setStyleSheet("font-size: 10px;")
        self.cmb_paper_tex = QtWidgets.QComboBox()
        self.cmb_paper_tex.setFixedHeight(24)
        for name, tid in PAPER_TEXTURES:
            self.cmb_paper_tex.addItem(name, tid)
        row_tex.addWidget(lbl_tex)
        row_tex.addWidget(self.cmb_paper_tex, 1)
        lay_paper.addLayout(row_tex)

        right_col.addWidget(grp_paper)
        right_col.addStretch()

        content_split.addLayout(right_col, 9)
        self.content_layout.addLayout(content_split, 1)

        # ── Rodapé Informativo & Botões de Ação ───────────────────────
        h_sep = QtWidgets.QFrame()
        h_sep.setFrameShape(QtWidgets.QFrame.HLine)
        h_sep.setObjectName("DialogDivider")
        self.content_layout.addWidget(h_sep)

        foot_row = QtWidgets.QHBoxLayout()
        foot_row.setSpacing(10)

        # Indicador de RAM Estimada
        self.lbl_ram_estimate = QtWidgets.QLabel()
        self.lbl_ram_estimate.setStyleSheet("font-size: 10px;")
        foot_row.addWidget(self.lbl_ram_estimate)
        foot_row.addStretch()

        self.btn_cancel = QtWidgets.QPushButton(tr("dialogs.cancel", "Cancelar"))
        self.btn_cancel.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cancel.setFixedSize(90, 30)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_create = QtWidgets.QPushButton(tr("dialogs.create_document", "Criar Documento"))
        self.btn_create.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_create.setDefault(True)
        self.btn_create.setFixedHeight(30)
        self.btn_create.clicked.connect(self.accept)

        foot_row.addWidget(self.btn_cancel)
        foot_row.addWidget(self.btn_create)
        self.content_layout.addLayout(foot_row)

    def _on_preset_chosen(self, width: int, height: int, dpi: int) -> None:
        for spin, value in ((self.spn_width, width), (self.spn_height, height), (self.spn_dpi, dpi)):
            spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(False)
        self._update_ram_estimate()

    def _on_dimension_changed(self):
        # Medidas digitadas: marca o preset que corresponde (ou nenhum).
        self._on_dpi_changed()
        self._update_ram_estimate()

    def _on_dpi_changed(self):
        self.gallery.match(self.spn_width.value(), self.spn_height.value(), self.spn_dpi.value())

    def _on_swap_orientation(self):
        w = self.spn_width.value()
        h = self.spn_height.value()
        self.spn_width.setValue(h)
        self.spn_height.setValue(w)

    def _update_ram_estimate(self):
        w = self.spn_width.value()
        h = self.spn_height.value()
        mb = estimate_ram_usage_mb(w, h, num_layers=3)
        mp = (float(w) * float(h)) / 1_000_000.0
        self.lbl_ram_estimate.setText(f"{mp:.1f} Megapixels  •  RAM estimada: ~{mb:.1f} MB (3 camadas)")

    def get_document_params(self) -> Dict[str, Any]:
        """Retorna todos os parâmetros de criação do documento para inicialização do motor."""
        return {
            "name": self.txt_name.text().strip() or "Sem Título",
            "width": self.spn_width.value(),
            "height": self.spn_height.value(),
            "dpi": self.spn_dpi.value(),
            "color_profile_id": self.cmb_color_prof.currentData(),
            "bg_color": self.cmb_bg_color.currentData(),
            "paper_texture_id": self.cmb_paper_tex.currentData(),
        }

    def get_values(self) -> tuple[str, int, int]:
        """Compatibilidade backward com chamadas antigas."""
        p = self.get_document_params()
        return p["name"], p["width"], p["height"]

    def _apply_theme(self, *_):
        tm = ThemeManager.instance()
        bg_main = tm.get_color("bg_base", "#12121a")
        bg_card = tm.get_color("bg_card", "#1e1e24")
        bg_input = tm.get_color("bg_input", "#18181f")
        border = tm.get_color("border", "#2e2e38")
        text = tm.get_color("text_main", "#f3f4f6")
        muted = tm.get_color("text_muted", "#9ca3af")
        accent = tm.get_color("accent", "#6366f1")

        self.btn_swap_orient.setIcon(get_icon("refresh", color=text))
        self.lbl_ram_estimate.setStyleSheet(f"font-size: 10px; color: {muted};")

        self.setStyleSheet(f"""
            NewDocumentDialog {{
                background-color: {bg_main};
                color: {text};
            }}
            QGroupBox {{
                background-color: {bg_card};
                border: 1px solid {border};
                border-radius: 8px;
                margin-top: 8px;
                padding: 10px;
                font-weight: bold;
                font-size: 10px;
                color: {accent};
            }}
            QLabel {{
                color: {text};
            }}
            QLineEdit, QComboBox, QSpinBox {{
                background-color: {bg_input};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 2px 6px;
                color: {text};
                font-size: 11px;
            }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
                border-color: {accent};
            }}
            QToolButton {{
                background-color: {bg_card};
                border: 1px solid {border};
                border-radius: 4px;
            }}
            QToolButton:hover {{
                border-color: {accent};
            }}
            QPushButton {{
                background-color: {accent};
                color: {text};
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
            QPushButton#btnCancel {{
                background-color: {bg_card};
                color: {text};
                border: 1px solid {border};
            }}
            #DialogDivider {{
                color: {border};
                background-color: {border};
            }}
        """)
