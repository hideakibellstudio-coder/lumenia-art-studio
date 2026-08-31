"""
CurveWindow — Janela de Configuração de Curvas LUT / Bézier do ALADYN ENGINE
=============================================================================
Permite ajustar graficamente os perfis Bézier do motor nativo:
- Perfil de Tamanho por Pressão
- Perfil de Fluxo / Esmaecer por Pressão
- Modificador por Velocidade

Respeita 100% o sistema de temas dinâmico (ThemeManager) da Lumenia UI.
"""

from __future__ import annotations

import math
from PySide6 import QtWidgets, QtCore, QtGui
from ui.core.theme.manager import ThemeManager


class CurveWidget(QtWidgets.QWidget):
    """Widget gráfico interativo para manipulação de Curva Bézier Carga/Pressão."""

    curveChanged = QtCore.Signal()
    PAD = 22

    PRESETS = {
        'linear': [(0.0, 0.0), (0.33, 0.33), (0.66, 0.66), (1.0, 1.0)],
        'soft':   [(0.0, 0.0), (0.12, 0.52), (0.50, 0.88), (1.0, 1.0)],
        'hard':   [(0.0, 0.0), (0.45, 0.10), (0.85, 0.45), (1.0, 1.0)],
        's':      [(0.0, 0.0), (0.18, 0.04), (0.82, 0.96), (1.0, 1.0)],
        'thresh': [(0.0, 0.0), (0.48, 0.00), (0.52, 1.00), (1.0, 1.0)],
    }

    def __init__(self, label_x="Entrada", label_y="Saída", parent=None):
        super().__init__(parent)
        self.label_x = label_x
        self.label_y = label_y
        self.setFixedSize(230, 170)
        self.setCursor(QtCore.Qt.CrossCursor)
        self.setMouseTracking(True)

        self._pts = [QtCore.QPointF(x, y) for x, y in self.PRESETS['linear']]
        self._dragging = None
        self._hover = None

    def _n2w(self, nx: float, ny: float) -> QtCore.QPointF:
        w, h, pad = self.width(), self.height(), self.PAD
        return QtCore.QPointF(pad + nx * (w - 2 * pad), (h - pad) - ny * (h - 2 * pad))

    def _w2n(self, wx: float, wy: float) -> tuple[float, float]:
        w, h, pad = self.width(), self.height(), self.PAD
        nx = (wx - pad) / (w - 2 * pad)
        ny = 1.0 - (wy - pad) / (h - 2 * pad)
        return nx, ny

    def get_control_points(self):
        return [(p.x(), p.y()) for p in self._pts]

    def set_preset(self, key: str):
        if key in self.PRESETS:
            self._pts = [QtCore.QPointF(x, y) for x, y in self.PRESETS[key]]
            self.update()
            self.curveChanged.emit()

    def invert_curve(self):
        for pt in self._pts:
            pt.setY(1.0 - pt.y())
        self.update()
        self.curveChanged.emit()

    def paintEvent(self, _):
        tm = ThemeManager.instance()
        bg_color = QtGui.QColor(tm.get_color("bg_base", "#12121a"))
        border_color = QtGui.QColor(tm.get_color("border", "#2a2a38"))
        accent_color = QtGui.QColor(tm.get_color("accent", "#6366f1"))
        text_sec = QtGui.QColor(tm.get_color("text_sec", "#9090aa"))

        qp = QtGui.QPainter(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        w, h, pad = self.width(), self.height(), self.PAD

        qp.fillRect(self.rect(), bg_color)

        # Grid interno
        qp.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 18), 1))
        inner_w = w - 2 * pad
        inner_h = h - 2 * pad
        for i in range(1, 4):
            gx = pad + i / 4.0 * inner_w
            gy = pad + i / 4.0 * inner_h
            qp.drawLine(QtCore.QPointF(gx, pad), QtCore.QPointF(gx, h - pad))
            qp.drawLine(QtCore.QPointF(pad, gy), QtCore.QPointF(w - pad, gy))

        qp.setPen(QtGui.QPen(border_color, 1))
        qp.drawRect(QtCore.QRectF(pad, pad, inner_w, inner_h))

        pw = [self._n2w(p.x(), p.y()) for p in self._pts]

        guide_pen = QtGui.QPen(QtGui.QColor(accent_color.red(), accent_color.green(), accent_color.blue(), 55), 1, QtCore.Qt.DashLine)
        qp.setPen(guide_pen)
        qp.drawLine(pw[0], pw[1])
        qp.drawLine(pw[3], pw[2])

        path = QtGui.QPainterPath()
        path.moveTo(pw[0])
        path.cubicTo(pw[1], pw[2], pw[3])
        qp.setPen(QtGui.QPen(accent_color, 2))
        qp.drawPath(path)

        for i, (pt_w, draggable) in enumerate(zip(pw, [False, True, True, False])):
            if draggable:
                radius = 6 if (self._hover == i or self._dragging == i) else 5
                qp.setBrush(QtGui.QBrush(accent_color))
                qp.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 200), 1.5))
                qp.drawEllipse(pt_w, radius, radius)
            else:
                qp.setBrush(QtGui.QBrush(QtGui.QColor(180, 180, 200, 120)))
                qp.setPen(QtCore.Qt.NoPen)
                qp.drawEllipse(pt_w, 3, 3)

        font = QtGui.QFont("Segoe UI", 7)
        qp.setFont(font)
        qp.setPen(QtGui.QPen(text_sec, 1))
        qp.drawText(QtCore.QRectF(0, h - 13, w, 12), QtCore.Qt.AlignCenter, self.label_x + " →")

        qp.save()
        qp.translate(9, h / 2.0)
        qp.rotate(-90)
        qp.drawText(QtCore.QRectF(-40, -8, 80, 14), QtCore.Qt.AlignCenter, "← " + self.label_y)
        qp.restore()

    def _nearest_draggable(self, pos: QtCore.QPointF) -> int | None:
        for i in [1, 2]:
            pt_w = self._n2w(self._pts[i].x(), self._pts[i].y())
            dx, dy = pos.x() - pt_w.x(), pos.y() - pt_w.y()
            if math.sqrt(dx * dx + dy * dy) < 12:
                return i
        return None

    def mousePressEvent(self, e):
        self._dragging = self._nearest_draggable(e.position())

    def mouseMoveEvent(self, e):
        if self._dragging is not None:
            nx, ny = self._w2n(e.position().x(), e.position().y())
            nx = max(0.0, min(1.0, nx))
            ny = max(0.0, min(1.0, ny))
            self._pts[self._dragging] = QtCore.QPointF(nx, ny)
            self.update()
            self.curveChanged.emit()
        else:
            hover = self._nearest_draggable(e.position())
            if hover != self._hover:
                self._hover = hover
                self.setCursor(QtCore.Qt.OpenHandCursor if hover else QtCore.Qt.CrossCursor)
                self.update()

    def mouseReleaseEvent(self, _):
        self._dragging = None


class CurveSection(QtWidgets.QFrame):
    """Seção colapsável/toggle com botões de presets para um perfil Bézier."""

    def __init__(self, title: str, label_x: str, parent=None):
        super().__init__(parent)
        self.setObjectName("CurveSection")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(6)

        header = QtWidgets.QHBoxLayout()
        header.setSpacing(4)

        self.chk = QtWidgets.QCheckBox()
        self.chk.setChecked(True)

        self.lbl_title = QtWidgets.QLabel(title)
        self.lbl_title.setStyleSheet("font-size: 11px; font-weight: 600; background: transparent; border: none;")

        header.addWidget(self.chk)
        header.addWidget(self.lbl_title)
        header.addStretch()

        for key, cap in [('linear', 'Lin'), ('soft', 'Suv'), ('hard', 'Dur'), ('s', 'S')]:
            btn = QtWidgets.QPushButton(cap)
            btn.setFixedHeight(20)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self.curve.set_preset(k))
            header.addWidget(btn)

        self.btn_inv = QtWidgets.QPushButton("Inverter")
        self.btn_inv.setFixedHeight(20)
        self.btn_inv.setCursor(QtCore.Qt.PointingHandCursor)
        header.addWidget(self.btn_inv)

        layout.addLayout(header)

        self.curve = CurveWidget(label_x=label_x)
        layout.addWidget(self.curve, alignment=QtCore.Qt.AlignCenter)

        self.btn_inv.clicked.connect(self.curve.invert_curve)
        self.chk.toggled.connect(self._on_toggle)

        ThemeManager.instance().themeChanged.connect(self.apply_theme)
        self.apply_theme()

    def _on_toggle(self, active: bool):
        self.curve.setEnabled(active)
        self.curve.setGraphicsEffect(None)
        opacity = 1.0 if active else 0.35
        ef = QtWidgets.QGraphicsOpacityEffect()
        ef.setOpacity(opacity)
        self.curve.setGraphicsEffect(ef)

    @property
    def active(self) -> bool:
        return self.chk.isChecked()

    def apply_theme(self):
        tm = ThemeManager.instance()
        bg_panel = tm.get_color("bg_panel", "#1a1a26")
        border = tm.get_color("border", "#2a2a3e")
        text = tm.get_color("text_main", "#e2e8f0")
        accent = tm.get_color("accent", "#6366f1")

        self.setStyleSheet(f"""
            QFrame#CurveSection {{
                background-color: {bg_panel};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QLabel {{
                color: {text};
            }}
            QPushButton {{
                background-color: {bg_panel};
                color: {text};
                border: 1px solid {border};
                border-radius: 3px;
                padding: 2px 7px;
                font-size: 10px;
            }}
            QPushButton:hover {{
                background-color: {accent};
                color: #ffffff;
            }}
        """)


from ui.core.dialogs.base_dialog import BaseFramelessDialog


class CurveWindow(BaseFramelessDialog):
    """Janela flutuante de Perfis e Curvas do Pincel (C++ ALADYN ENGINE)."""

    def __init__(self, parent=None):
        super().__init__(title="Perfis & Curvas LUT", icon_name="curve", parent=parent, modal=False)
        self.setMinimumWidth(310)

        self.pressure_sec = CurveSection("Perfil de Tamanho (Ponta)", label_x="Pressão")
        self.flow_sec = CurveSection("Perfil de Fluxo (Esmaecer)", label_x="Pressão")
        self.velocity_sec = CurveSection("Modificador por Velocidade", label_x="Velocidade")

        self.flow_sec.chk.setChecked(True)
        self.velocity_sec.chk.setChecked(False)

        self.content_layout.addWidget(self.pressure_sec)
        self.content_layout.addWidget(self.flow_sec)
        self.content_layout.addWidget(self.velocity_sec)

        self.pressure_sec.curve.curveChanged.connect(self.sync_to_engine)
        self.flow_sec.curve.curveChanged.connect(self.sync_to_engine)
        self.velocity_sec.curve.curveChanged.connect(self.sync_to_engine)

        self.pressure_sec.chk.toggled.connect(self.sync_to_engine)
        self.flow_sec.chk.toggled.connect(self.sync_to_engine)
        self.velocity_sec.chk.toggled.connect(self.sync_to_engine)

        ThemeManager.instance().themeChanged.connect(self.apply_theme)
        self.apply_theme()

        self.adjustSize()
        self.sync_to_engine()

    def sync_to_engine(self):
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if not backend:
            return

        pts_p = self.pressure_sec.curve.get_control_points()
        backend.set_curve_control_points("pressure_size", pts_p, self.pressure_sec.active)

        pts_f = self.flow_sec.curve.get_control_points()
        backend.set_curve_control_points("pressure_flow", pts_f, self.flow_sec.active)

        pts_v = self.velocity_sec.curve.get_control_points()
        backend.set_curve_control_points("velocity_size", pts_v, self.velocity_sec.active)

    def apply_theme(self):
        tm = ThemeManager.instance()
        bg_main = tm.get_color("bg_base", "#12121a")
        self.setStyleSheet(f"QWidget {{ background-color: {bg_main}; font-family: 'Segoe UI', sans-serif; }}")

    def closeEvent(self, event):
        event.ignore()
        self.hide()
