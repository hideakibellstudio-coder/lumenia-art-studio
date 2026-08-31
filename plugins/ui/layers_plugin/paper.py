import logging
import os
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QPushButton, 
                               QColorDialog, QDialog, QSlider, QVBoxLayout, QMenu, QApplication,
                               QComboBox, QCheckBox)
from PySide6.QtGui import QColor, QPainter, QBrush, QPixmap, QIcon, QPen, QAction
from PySide6.QtCore import Qt, QSize, Signal, QPoint
from ui.core.icons import get_icon

logger = logging.getLogger(__name__)

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
        from ui.core.i18n import tr
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

class TexturePopup(QDialog):
    presetChanged = Signal(int)
    depthChanged = Signal(float)
    scaleChanged = Signal(float)
    invertChanged = Signal(bool)
    enabledChanged = Signal(bool)

    PRESETS = [
        (0, "Grão Fino (Fine Grain)"),
        (1, "Papel Aquarela (Rough Cotton)"),
        (2, "Tela de Óleo (Linen Canvas)"),
        (3, "Ruído Puro (Noise)"),
    ]

    def __init__(self, parent=None, preset_id=0, depth=0.5, scale=1.0, invert=False, enabled=True):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.preset_id = preset_id

        from ui.core.theme.manager import ThemeManager
        qss = """
            QDialog { 
                background-color: @BG_DARKER; 
                border: 1px solid @BORDER; 
                border-radius: @RADIUS_MEDIUM; 
            }
            QLabel { 
                color: @FG_PRIMARY; 
                font-family: @FONT_FAMILY;
                font-size: 11px; 
            }
            QComboBox {
                padding: 4px 6px;
                background-color: @BG_MID;
                color: @FG_PRIMARY;
                border: 1px solid @BORDER;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton {
                padding: 4px 8px;
                background-color: @BG_MID;
                color: @FG_PRIMARY;
                border: 1px solid @BORDER;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: @ACCENT;
                color: #ffffff;
            }
            QSlider::groove:horizontal { 
                border: 1px solid @BORDER; 
                height: 4px; 
                background: @BG_DARKEST; 
                border-radius: 2px; 
            }
            QSlider::handle:horizontal { 
                background: @ACCENT; 
                width: 12px; 
                margin: -4px 0; 
                border-radius: 6px; 
            }
        """
        self.setStyleSheet(ThemeManager.instance().compile_qss(qss))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        from ui.core.i18n import tr

        # Title
        lbl_title = QLabel(tr("layers.paper_texture_title", "Textura da Tela (Papel Background)"))
        lbl_title.setStyleSheet("font-weight: bold; font-size: 11px; color: @ACCENT;")
        layout.addWidget(lbl_title)

        # Row 1: Preview + Presets Combobox
        row_c = QHBoxLayout()
        row_c.setSpacing(6)
        self.preview_c_grain = QLabel()
        self.preview_c_grain.setFixedSize(46, 46)
        self.preview_c_grain.setStyleSheet("border:1px solid #3a3a4e;background:#181824;border-radius:4px;")
        
        self.cmb_c_grain = QComboBox()
        for pid, name in self.PRESETS:
            self.cmb_c_grain.addItem(name, pid)
        if 0 <= preset_id < len(self.PRESETS):
            self.cmb_c_grain.setCurrentIndex(preset_id)
        self.cmb_c_grain.currentIndexChanged.connect(self._on_preset_changed)

        row_c.addWidget(self.preview_c_grain)
        row_c.addWidget(self.cmb_c_grain, 1)
        layout.addLayout(row_c)

        # Button: Carregar PNG do Papel
        from ui.core.icons import get_icon
        self.btn_load_c = QPushButton(tr("layers.load_paper_png", "Carregar PNG do Papel"))
        self.btn_load_c.setIcon(get_icon("folder"))
        self.btn_load_c.setCursor(Qt.PointingHandCursor)
        self.btn_load_c.clicked.connect(self._on_load_paper_png)
        layout.addWidget(self.btn_load_c)

        # Checkbox: Ativar Relevo no Papel
        self.chk_c_grain = QCheckBox(tr("layers.enable_paper_relief", "Ativar Relevo no Papel"))
        self.chk_c_grain.setChecked(enabled)
        self.chk_c_grain.toggled.connect(self.enabledChanged.emit)
        layout.addWidget(self.chk_c_grain)

        # Scale slider
        layout.addWidget(QLabel(f"{tr('brush.scale', 'Escala do Relevo')}:"))
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(10, 500)
        self.scale_slider.setValue(int(scale * 100))
        self.scale_slider.valueChanged.connect(lambda v: self.scaleChanged.emit(v / 100.0))
        layout.addWidget(self.scale_slider)

        # Contrast/Depth slider
        layout.addWidget(QLabel(f"{tr('brush.contrast', 'Contraste / Dureza do Relevo')}:"))
        self.depth_slider = QSlider(Qt.Horizontal)
        self.depth_slider.setRange(10, 300)
        self.depth_slider.setValue(int(depth * 100))
        self.depth_slider.valueChanged.connect(lambda v: self.depthChanged.emit(v / 100.0))
        layout.addWidget(self.depth_slider)

        # Checkbox: Inverter Topografia
        self.chk_c_invert = QCheckBox(tr("brush.invert", "Inverter Topografia"))
        self.chk_c_invert.setChecked(invert)
        self.chk_c_invert.toggled.connect(self.invertChanged.emit)
        layout.addWidget(self.chk_c_invert)

        self._update_preview(self.cmb_c_grain.currentIndex())

    def _on_preset_changed(self, idx: int):
        self.preset_id = idx
        self._update_preview(idx)
        self.presetChanged.emit(idx)

    def _on_load_paper_png(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Carregar PNG de Textura do Papel", "", "Imagens PNG (*.png *.jpg *.jpeg)"
        )
        if path:
            try:
                pix = QPixmap(path)
                if not pix.isNull():
                    self.preview_c_grain.setPixmap(pix.scaled(46, 46, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
            except Exception:
                pass

    def _update_preview(self, idx: int):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b:
            b.set_canvas_height_preset(idx)
            try:
                buf = b.get_canvas_height_preview_buffer()
                w, h = b.get_canvas_height_preview_dimensions()
                if buf and w > 0 and h > 0:
                    from PySide6.QtGui import QImage
                    img = QImage(bytes(buf), w, h, w, QImage.Format_Grayscale8)
                    pix = QPixmap.fromImage(img).scaled(46, 46, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.preview_c_grain.setPixmap(pix)
                    return
            except Exception:
                pass

        pix = QPixmap(46, 46)
        pix.fill(QColor(24, 24, 32))
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        if idx == 0:  # Grão Fino
            p.setPen(QPen(QColor(255, 255, 255, 30), 1))
            for y in range(0, 46, 4):
                for x in range(0, 46, 4):
                    if (x + y) % 8 == 0:
                        p.drawPoint(x, y)
        elif idx == 1:  # Papel Aquarela
            p.setPen(QPen(QColor(255, 255, 255, 45), 1))
            for y in range(0, 46, 6):
                for x in range(0, 46, 6):
                    if (x * y) % 11 < 5:
                        p.drawRect(x, y, 3, 3)
        elif idx == 2:  # Tela de Óleo
            p.setPen(QPen(QColor(255, 255, 255, 55), 1))
            for i in range(0, 46, 5):
                p.drawLine(i, 0, i, 46)
                p.drawLine(0, i, 46, i)
        else:  # Ruído Puro
            import random
            p.setPen(QPen(QColor(255, 255, 255, 40), 1))
            for _ in range(120):
                p.drawPoint(random.randint(0, 45), random.randint(0, 45))
        p.end()
        self.preview_c_grain.setPixmap(pix)

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

class PaperLayerWidget(QWidget):
    def __init__(self, bridge=None, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.setObjectName("PaperLayerWidget")

        self.visible = True
        self.color = QColor(255, 255, 255, 255)
        self.depth = 1.0
        self.scale = 1.0
        self.preset_id = 0
        self.enabled = False
        self.invert = False

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

        self.color_btn = ColorCircleButton(self.color, self)
        self.color_btn.colorChanged.connect(self._on_color_changed)
        layout.addWidget(self.color_btn)

        self.tex_btn = TextureCircleButton(self)
        self.tex_btn.openPopupRequested.connect(self._show_texture_popup)
        layout.addWidget(self.tex_btn)

        self.setFixedHeight(36)
        self._update_vis_icon()

    def _update_vis_icon(self):
        icon_name = "eye" if self.visible else "eye-off"
        icon = get_icon(icon_name, "FG_PRIMARY" if self.visible else "text_sec")
        self.vis_btn.setIcon(icon)
        self.vis_btn.setIconSize(QSize(16, 16))

    def set_paper_state(self, color=None, visible=None, preset_id=None, enabled=None):
        if color is not None:
            self.color = color
            self.color_btn.color = color
            self.color_btn.update()
        if visible is not None:
            self.visible = visible
            self._update_vis_icon()
        if preset_id is not None:
            self.preset_id = preset_id
        if enabled is not None:
            self.enabled = enabled
            self.tex_btn.set_has_texture(self.enabled and self.preset_id > 0)
        self._sync_state()

    def _show_texture_popup(self):
        popup = TexturePopup(
            self,
            preset_id=self.preset_id,
            depth=self.depth,
            scale=self.scale,
            invert=self.invert,
            enabled=self.enabled
        )
        popup.presetChanged.connect(self._on_preset_changed)
        popup.depthChanged.connect(self._on_depth_changed)
        popup.scaleChanged.connect(self._on_scale_changed)
        popup.invertChanged.connect(self._on_invert_changed)
        popup.enabledChanged.connect(self._on_enabled_changed)

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

    def _on_color_changed(self, color):
        self.color = color
        self._sync_state()

    def _on_preset_changed(self, pid: int):
        self.preset_id = pid
        self.tex_btn.set_has_texture(self.enabled and pid > 0)
        self._sync_state()

    def _on_depth_changed(self, val):
        self.depth = val
        self._sync_state()

    def _on_scale_changed(self, val):
        self.scale = val
        self._sync_state()

    def _on_invert_changed(self, invert: bool):
        self.invert = invert
        self._sync_state()

    def _on_enabled_changed(self, enabled: bool):
        self.enabled = enabled
        self.tex_btn.set_has_texture(enabled and self.preset_id > 0)
        self._sync_state()

    def _toggle_visibility(self):
        self.visible = not self.visible
        self._update_vis_icon()
        self._sync_state()

    def _sync_state(self):
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend:
            effective_preset = self.preset_id if self.enabled else 0
            backend.set_canvas_paper_state(self.color, self.visible, effective_preset, self.enabled)
            backend.set_canvas_grain_scale(float(self.scale))
            backend.set_canvas_grain_contrast(float(self.depth))
            backend.set_canvas_grain_invert(bool(self.invert))

        # Atualiza documento ativo
        from ui.core.document.manager import DocumentManager
        active_doc = DocumentManager.instance().active_document()
        if active_doc:
            active_doc.paper_color = self.color

        # Procura globalmente o CanvasWidget em todas as janelas ativas
        for top_w in QApplication.topLevelWidgets():
            if hasattr(top_w, "workspace") and hasattr(top_w.workspace, "canvas_widget"):
                cw = top_w.workspace.canvas_widget
                if cw:
                    cw.paper_visible = self.visible
                    cw.paper_color = self.color
                    cw.update()
            elif hasattr(top_w, "canvas_widget"):
                cw = top_w.canvas_widget
                if cw:
                    cw.paper_visible = self.visible
                    cw.paper_color = self.color
                    cw.update()

    def update_theme(self, colors):
        from ui.core.theme.manager import ThemeManager
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
