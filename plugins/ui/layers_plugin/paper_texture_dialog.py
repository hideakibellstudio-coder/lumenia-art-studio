"""TexturePopup — Diálogo popup para configuração de relevo e textura do papel.

Decoupled under ARCcC v2 (< 220 LOC).
"""

import random
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QCheckBox, QSlider, QFileDialog
)
from PySide6.QtGui import QColor, QPainter, QPixmap, QPen
from PySide6.QtCore import Qt, Signal

from ui.core.theme.manager import ThemeManager
from ui.core.i18n import tr
from ui.core.icons import get_icon


class TexturePopup(QDialog):
    """Popup de ajustes para textura e relevo do papel de fundo."""

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
            QLabel#PaperGrainPreview {
                border: 1px solid @BORDER;
                background-color: @BG_DARKEST;
                border-radius: 4px;
            }
        """
        self.setStyleSheet(ThemeManager.instance().compile_qss(qss))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Title
        lbl_title = QLabel(tr("layers.paper_texture_title", "Textura da Tela (Papel Background)"))
        lbl_title.setProperty("accent", "true")
        layout.addWidget(lbl_title)

        # Row 1: Preview + Presets Combobox
        row_c = QHBoxLayout()
        row_c.setSpacing(6)
        self.preview_c_grain = QLabel()
        self.preview_c_grain.setObjectName("PaperGrainPreview")
        self.preview_c_grain.setFixedSize(46, 46)
        
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
            p.setPen(QPen(QColor(255, 255, 255, 40), 1))
            for _ in range(120):
                p.drawPoint(random.randint(0, 45), random.randint(0, 45))
        p.end()
        self.preview_c_grain.setPixmap(pix)
