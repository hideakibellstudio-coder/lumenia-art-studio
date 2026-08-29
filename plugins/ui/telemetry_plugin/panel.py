"""
TelemetryPanel — Painel Visual de Telemetria do ALADYN ENGINE
================================================================
Exibe métricas físicas calculadas pelo motor em tempo real:
- Pressão da caneta (Pressure)
- Velocidade do traço (Velocity)
- Vazão de saída / fluxo de tinta (Output Flow)
"""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.widgets.card_box import PanelCardBox
from ui.core.theme.manager import ThemeManager


class TelemetryPanel(QtWidgets.QWidget):
    """Painel de telemetria acoplável em docas."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TelemetryPanel")
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(33)  # ~30 FPS
        self._timer.timeout.connect(self._update_telemetry)

        self._build_ui()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()
        self._timer.start()

    def _build_ui(self) -> None:
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(0)

        content = QtWidgets.QWidget()
        lo = QtWidgets.QVBoxLayout(content)
        lo.setContentsMargins(8, 8, 8, 8)
        lo.setSpacing(10)

        # 1. Indicador de Pressão
        lo.addWidget(self._make_label("PRESSÃO DA CANETA"))
        self.bar_pressure = QtWidgets.QProgressBar()
        self.bar_pressure.setRange(0, 100)
        self.bar_pressure.setValue(0)
        self.bar_pressure.setFixedHeight(14)
        self.bar_pressure.setTextVisible(False)
        self.lbl_pressure_val = QtWidgets.QLabel("0 %")
        self.lbl_pressure_val.setStyleSheet("font-size: 10px; font-weight: bold;")
        
        row_press = QtWidgets.QHBoxLayout()
        row_press.addWidget(self.bar_pressure, 1)
        row_press.addWidget(self.lbl_pressure_val)
        lo.addLayout(row_press)

        # 2. Indicador de Velocidade
        lo.addWidget(self._make_label("VELOCIDADE DO TRAÇO"))
        self.bar_velocity = QtWidgets.QProgressBar()
        self.bar_velocity.setRange(0, 1000)
        self.bar_velocity.setValue(0)
        self.bar_velocity.setFixedHeight(14)
        self.bar_velocity.setTextVisible(False)
        self.lbl_velocity_val = QtWidgets.QLabel("0 px/s")
        self.lbl_velocity_val.setStyleSheet("font-size: 10px; font-weight: bold;")

        row_vel = QtWidgets.QHBoxLayout()
        row_vel.addWidget(self.bar_velocity, 1)
        row_vel.addWidget(self.lbl_velocity_val)
        lo.addLayout(row_vel)

        # 3. Indicador de Vazão de Saída (Output Flow)
        lo.addWidget(self._make_label("VAZÃO DE SAÍDA (OUTPUT FLOW)"))
        self.bar_flow = QtWidgets.QProgressBar()
        self.bar_flow.setRange(0, 100)
        self.bar_flow.setValue(0)
        self.bar_flow.setFixedHeight(14)
        self.bar_flow.setTextVisible(False)
        self.lbl_flow_val = QtWidgets.QLabel("0 %")
        self.lbl_flow_val.setStyleSheet("font-size: 10px; font-weight: bold;")

        row_flow = QtWidgets.QHBoxLayout()
        row_flow.addWidget(self.bar_flow, 1)
        row_flow.addWidget(self.lbl_flow_val)
        lo.addLayout(row_flow)

        lo.addStretch()

        card_box = PanelCardBox("", content, self)
        main_layout.addWidget(card_box)

    def _make_label(self, text: str) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        lbl.setObjectName("TelemLabel")
        return lbl

    def _update_telemetry(self) -> None:
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "last_telemetry"):
            p, v, f = backend.last_telemetry
            
            # Pressão 0.0 .. 1.0 -> 0 .. 100%
            press_pct = int(p * 100)
            self.bar_pressure.setValue(min(100, max(0, press_pct)))
            self.lbl_pressure_val.setText(f"{press_pct} %")

            # Velocidade
            vel_val = int(v)
            self.bar_velocity.setValue(min(1000, max(0, vel_val)))
            self.lbl_velocity_val.setText(f"{vel_val} px/s")

            # Vazão 0.0 .. 1.0 -> 0 .. 100%
            flow_pct = int(f * 100)
            self.bar_flow.setValue(min(100, max(0, flow_pct)))
            self.lbl_flow_val.setText(f"{flow_pct} %")

    def _apply_theme(self, *args) -> None:
        tm = ThemeManager.instance()
        border = tm.get_color("border")
        muted = tm.get_color("text_sec")
        accent = tm.get_color("accent")
        text = tm.get_color("text_main")

        self.setStyleSheet(f"""
            QLabel#TelemLabel {{
                color: {muted};
                font-size: 9px;
                font-weight: bold;
                letter-spacing: 0.5px;
            }}
            QProgressBar {{
                background-color: rgba(0, 0, 0, 0.3);
                border: 1px solid {border};
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {accent};
                border-radius: 2px;
            }}
            QLabel {{
                color: {text};
            }}
        """)
