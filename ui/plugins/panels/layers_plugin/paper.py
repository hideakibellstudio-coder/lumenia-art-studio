import logging
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QPushButton, 
                               QColorDialog)
from PySide6.QtGui import QColor, QPainter, QBrush, QPen
from PySide6.QtCore import Qt, QSize, Signal, QPoint
from ui.infrastructure.icons import get_icon

logger = logging.getLogger(__name__)

from .paper_texture_dialog import TexturePopup

class CircleButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self.setStyleSheet("border: none; background: transparent; min-width: 24px; max-width: 24px; min-height: 24px; max-height: 24px; padding: 0px; margin: 0px;")
        self.setCursor(Qt.PointingHandCursor)

class ColorCircleButton(CircleButton):
    colorChanged = Signal(QColor)
    
    def __init__(self, color=QColor(255, 255, 255, 255), parent=None):
        super().__init__(parent)
        self.color = color
        self.clicked.connect(self._choose_color)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect().adjusted(2, 2, -2, -2)
        
        painter.setBrush(QBrush(Qt.gray, Qt.Dense4Pattern))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(rect)
        
        painter.setBrush(QBrush(self.color))
        painter.drawEllipse(rect)
        
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawEllipse(rect)
        
        painter.end()
        
    def _choose_color(self):
        from ui.infrastructure.i18n import tr
        dlg = QColorDialog(self.color)
        dlg.setWindowTitle(tr("dialogs.paper_color_dialog", "Cor do Papel de Fundo (Layer 0)"))
        dlg.setOption(QColorDialog.ShowAlphaChannel, True)
        dlg.resize(600, 460)
        dlg.setMinimumSize(540, 420)
        if dlg.exec() == QColorDialog.Accepted:
            new_color = dlg.selectedColor()
            if new_color.isValid():
                self.color = new_color
                self.update()
                self.colorChanged.emit(new_color)

class TextureCircleButton(CircleButton):
    openPopupRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.has_texture = False
        self.clicked.connect(self.openPopupRequested.emit)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(2, 2, -2, -2)

        if self.has_texture:
            painter.setBrush(QBrush(Qt.lightGray, Qt.CrossPattern))
        else:
            painter.setBrush(QBrush(Qt.darkGray))

        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawEllipse(rect)
        painter.end()

    def set_has_texture(self, has_tex):
        self.has_texture = has_tex
        self.update()

# Cor mostrada sem documento aberto (a mesma do papel padrão do Document).
_DEFAULT_PAPER = QColor(255, 255, 255, 255)


class PaperLayerWidget(QWidget):
    """View do papel do documento (linha "Papel / Fundo" do painel de camadas).

    Mostra `Document.paper_*` e edita só por `Document.set_paper(...)`; o
    documento sincroniza o motor e repinta o canvas. Até 2026-09-24 o widget
    guardava a própria cópia do papel (cor, visível, textura, grão) e
    escrevia no motor, no documento e no canvas (Lei do rio nº 1).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PaperLayerWidget")
        self._document = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        self.vis_btn = QPushButton()
        self.vis_btn.setFixedSize(20, 20)
        self.vis_btn.setCursor(Qt.PointingHandCursor)
        self.vis_btn.setStyleSheet("background: transparent; border: none;")
        self.vis_btn.clicked.connect(self._toggle_visibility)
        layout.addWidget(self.vis_btn)

        name_lbl = QLabel("Papel / Fundo")
        name_lbl.setObjectName("PaperLabel")
        layout.addWidget(name_lbl)

        layout.addStretch()

        self.color_btn = ColorCircleButton(_DEFAULT_PAPER, self)
        self.color_btn.colorChanged.connect(lambda color: self._edit(color=color))
        layout.addWidget(self.color_btn)

        self.tex_btn = TextureCircleButton(self)
        self.tex_btn.openPopupRequested.connect(self._show_texture_popup)
        layout.addWidget(self.tex_btn)

        self.setFixedHeight(36)
        self._show()

    # ── Documento ─────────────────────────────────────────────────────────

    def show_document(self, document) -> None:
        """Passa a mostrar o papel de `document` (None = sem documento)."""
        if self._document is not None:
            self._document.paper_changed.disconnect(self._on_paper_changed)
        self._document = document
        if document is not None:
            document.paper_changed.connect(self._on_paper_changed)
        self._show()

    def _on_paper_changed(self, _changed) -> None:
        self._show()

    def _edit(self, **changes) -> None:
        if self._document is not None:
            self._document.set_paper(**changes)

    def _show(self) -> None:
        doc = self._document
        self.color_btn.color = doc.paper_color if doc else _DEFAULT_PAPER
        self.color_btn.update()
        self._update_vis_icon()
        self.tex_btn.set_has_texture(bool(doc and doc.paper_texture_enabled and doc.paper_texture_id > 0))

    def _update_vis_icon(self):
        visible = self._document.paper_visible if self._document else True
        icon = get_icon("eye" if visible else "eye-off", "FG_PRIMARY" if visible else "text_sec")
        self.vis_btn.setIcon(icon)
        self.vis_btn.setIconSize(QSize(16, 16))

    # ── Edição ────────────────────────────────────────────────────────────

    def _toggle_visibility(self):
        if self._document is not None:
            self._edit(visible=not self._document.paper_visible)

    def _show_texture_popup(self):
        doc = self._document
        if doc is None:
            return
        popup = TexturePopup(
            self,
            preset_id=doc.paper_texture_id,
            depth=doc.paper_contrast,
            scale=doc.paper_scale,
            invert=doc.paper_invert,
            enabled=doc.paper_texture_enabled,
        )
        popup.presetChanged.connect(lambda pid: self._edit(texture_id=pid))
        popup.depthChanged.connect(lambda value: self._edit(contrast=value))
        popup.scaleChanged.connect(lambda value: self._edit(scale=value))
        popup.invertChanged.connect(lambda invert: self._edit(invert=invert))
        popup.enabledChanged.connect(lambda enabled: self._edit(texture_enabled=enabled))

        btn_global = self.tex_btn.mapToGlobal(QPoint(0, 0))
        popup.adjustSize()
        popup_w = max(250, popup.sizeHint().width())
        popup_h = max(240, popup.sizeHint().height())

        # Abre alinhado para a esquerda da borda direita do botão
        x = btn_global.x() + self.tex_btn.width() - popup_w
        y = btn_global.y() + self.tex_btn.height() + 4

        win = self.window()
        if win:
            win_right = win.mapToGlobal(QPoint(win.width(), 0)).x()
            win_left = win.mapToGlobal(QPoint(0, 0)).x()
            win_bottom = win.mapToGlobal(QPoint(0, win.height())).y()

            if x + popup_w > win_right - 10:
                x = win_right - popup_w - 10
            if x < win_left + 10:
                x = win_left + 10

            if y + popup_h > win_bottom - 10:
                y = btn_global.y() - popup_h - 4

        popup.move(x, y)
        popup.show()

    def update_theme(self, colors):
        from ui.infrastructure.theme.manager import ThemeManager
        qss = """
            QWidget#PaperLayerWidget {
                background-color: @BG_PANEL;
                border-top: 1px solid @BORDER;
                border-bottom: 1px solid @BORDER;
            }
            QLabel#PaperLabel {
                font-weight: bold;
                color: @FG_SECONDARY;
                font-size: 11px;
            }
        """
        self.setStyleSheet(ThemeManager.instance().compile_qss(qss))
        self._update_vis_icon()
