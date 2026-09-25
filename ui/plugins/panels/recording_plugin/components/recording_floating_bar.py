"""
RecordingFloatingBar — Barra de Controle Flutuante de Gravação (ARCcC).
========================================================================
Barra flutuante compacta em cápsula (estilo HUD / Dynamic Island) ancorada
no topo do viewport com controles rápidos de gravação:
  - LED pulsante REC e cronômetro em tempo real.
  - Alternância de Pausar / Retomar.
  - Parada com solicitação de salvamento e seleção de destino.
  - Atalho de Salvamento Direto.

Os botões emitem sinais (`pauseResumeRequested`, `stopRequested`,
`saveRequested`) que o painel liga ao `RecordingActions`; o estado mostrado
chega por `update_state`. Até 2026-09-24 a barra recebia o painel e chamava
os métodos privados dele depois de conferir com `hasattr`.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6 import QtCore, QtWidgets, QtGui

from ui.core.dialogs.floating_tool_window import FloatingToolWindow
from ui.infrastructure.i18n import I18nManager, tr
from ui.infrastructure.icons import get_icon
from ui.infrastructure.theme.manager import ThemeManager

logger = logging.getLogger(__name__)


class RecordingFloatingBar(FloatingToolWindow):
    """Barra flutuante de gravação ancorada no topo do viewport."""

    pauseResumeRequested = QtCore.Signal()
    stopRequested = QtCore.Signal()
    saveRequested = QtCore.Signal()

    def __init__(
        self,
        anchor: Optional[QtWidgets.QWidget] = None,
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__(parent, transparent_stylesheet=True)
        self._anchor = anchor  # widget em cujo topo a barra se centraliza (o canvas)
        self._recording = False
        self._paused = False
        self._user_dragged: bool = False
        self._drag_pos: Optional[QtCore.QPoint] = None

        self._setup_ui()
        self._apply_theme()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        I18nManager.instance().languageChanged.connect(self._retranslate)

        if self._anchor is not None:
            self._anchor.installEventFilter(self)
            self._anchor.destroyed.connect(self._forget_anchor)

    def detach_anchor(self) -> None:
        """Solta o canvas; o painel chama ao ser desligado.

        Sem isto o canvas, que continua vivo, chamava o filtro de eventos de
        uma barra já destruída e o PySide derrubava o processo (achado em
        2026-09-25: desativar o plugin de gravação com um documento aberto).
        """
        if self._anchor is not None:
            self._anchor.destroyed.disconnect(self._forget_anchor)
            self._anchor.removeEventFilter(self)
            self._anchor = None

    def _forget_anchor(self) -> None:
        self._anchor = None

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if watched is self._anchor and event.type() in (QtCore.QEvent.Resize, QtCore.QEvent.Move):
            if self.isVisible() and not self._user_dragged:
                QtCore.QTimer.singleShot(10, self, self.reposition_to_top_anchor)
        return super().eventFilter(watched, event)

    def _setup_ui(self) -> None:
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(0)

        # Cápsula principal
        self.container = QtWidgets.QWidget(self)
        self.container.setObjectName("RecordingBarContainer")

        shadow = QtWidgets.QGraphicsDropShadowEffect(self.container)
        shadow.setBlurRadius(14)
        shadow.setXOffset(0)
        shadow.setYOffset(3)
        shadow.setColor(QtGui.QColor(0, 0, 0, 150))
        self.container.setGraphicsEffect(shadow)

        self.main_layout.addWidget(self.container)

        self.box_layout = QtWidgets.QHBoxLayout(self.container)
        self.box_layout.setContentsMargins(10, 4, 10, 4)
        self.box_layout.setSpacing(8)
        self.box_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)

        # 1. Handle sutil de arrasto
        self.drag_handle = QtWidgets.QFrame(self.container)
        self.drag_handle.setObjectName("RecordingBarDragHandle")
        self.drag_handle.setFixedSize(5, 18)
        self.drag_handle.setCursor(QtCore.Qt.CursorShape.SizeAllCursor)
        self.box_layout.addWidget(self.drag_handle)

        # 2. LED e Status
        self.lbl_led = QtWidgets.QLabel("●", self.container)
        self.lbl_led.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.box_layout.addWidget(self.lbl_led)

        self.lbl_status = QtWidgets.QLabel("REC", self.container)
        self.lbl_status.setStyleSheet("font-size: 10px; font-weight: bold;")
        self.box_layout.addWidget(self.lbl_status)

        # 3. Cronômetro e Frames
        self.lbl_time = QtWidgets.QLabel("00:00:00", self.container)
        self.lbl_time.setStyleSheet("font-family: monospace; font-size: 11px; font-weight: bold;")
        self.box_layout.addWidget(self.lbl_time)

        self.lbl_frames = QtWidgets.QLabel("(0 f)", self.container)
        self.lbl_frames.setStyleSheet("font-size: 10px;")
        self.box_layout.addWidget(self.lbl_frames)

        # 4. Divisor Vertical
        self.sep = QtWidgets.QFrame(self.container)
        self.sep.setObjectName("RecordingBarSep")
        self.sep.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        self.sep.setFixedWidth(1)
        self.sep.setFixedHeight(18)
        self.box_layout.addWidget(self.sep)

        # 5. Botão Pausar / Retomar
        self.btn_pause_resume = QtWidgets.QPushButton(self.container)
        self.btn_pause_resume.setFixedSize(28, 28)
        self.btn_pause_resume.setIconSize(QtCore.QSize(16, 16))
        self.btn_pause_resume.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_pause_resume.clicked.connect(self.pauseResumeRequested)
        self.box_layout.addWidget(self.btn_pause_resume)

        # 6. Botão Parar (Stop)
        self.btn_stop = QtWidgets.QPushButton(self.container)
        self.btn_stop.setFixedSize(28, 28)
        self.btn_stop.setIconSize(QtCore.QSize(16, 16))
        self.btn_stop.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_stop.setToolTip(tr("recording.stop_tip", "Parar Gravação (Pergunta para Salvar)"))
        self.btn_stop.clicked.connect(self.stopRequested)
        self.box_layout.addWidget(self.btn_stop)

        # 7. Botão Salvar Imediato
        self.btn_save = QtWidgets.QPushButton(self.container)
        self.btn_save.setFixedSize(28, 28)
        self.btn_save.setIconSize(QtCore.QSize(16, 16))
        self.btn_save.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_save.setToolTip(tr("recording.save_tip", "Salvar Vídeo..."))
        self.btn_save.clicked.connect(self.saveRequested)
        self.box_layout.addWidget(self.btn_save)

    def _apply_theme(self) -> None:
        theme = ThemeManager.instance()
        bg_panel = theme.get_color("bg_panel")
        border = theme.get_color("border")
        fg_muted = theme.get_color("text_muted")
        fg_main = theme.get_color("text_main")
        bg_hover = theme.get_color("accent_muted")

        self.container.setStyleSheet(f"""
            QWidget#RecordingBarContainer {{
                background-color: {bg_panel};
                border: 1px solid {border};
                border-radius: 16px;
            }}
            QFrame#RecordingBarDragHandle {{
                background-color: {fg_muted};
                border-radius: 2px;
            }}
            QFrame#RecordingBarSep {{
                background-color: {border};
                border: none;
            }}
            QLabel {{
                background-color: transparent;
                border: none;
            }}
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {bg_hover};
            }}
        """)

        self.lbl_frames.setStyleSheet(f"color: {fg_muted}; font-size: 10px;")
        self.lbl_time.setStyleSheet(f"color: {fg_main}; font-family: monospace; font-size: 11px; font-weight: bold;")
        self._update_icons()

    def _update_icons(self) -> None:
        if self._paused:
            self.btn_pause_resume.setIcon(get_icon("play"))
            self.btn_pause_resume.setToolTip(tr("recording.resume", "Retomar Gravação"))
        else:
            self.btn_pause_resume.setIcon(get_icon("pause"))
            self.btn_pause_resume.setToolTip(tr("recording.pause", "Pausar Gravação"))

        self.btn_stop.setIcon(get_icon("stop", color=ThemeManager.instance().get_color("DANGER", "#f85149")))
        self.btn_save.setIcon(get_icon("save"))

    def update_state(self, is_recording: bool, is_paused: bool) -> None:
        """Atualiza os indicadores visuais e botões conforme o estado da gravação."""
        theme = ThemeManager.instance()
        danger = theme.get_color("DANGER", "#f85149")
        warning = theme.get_color("WARNING", "#d29922")
        self._recording, self._paused = is_recording, is_paused

        if is_recording and not is_paused:
            self.lbl_status.setText("REC")
            self.lbl_status.setStyleSheet(f"color: {danger}; font-size: 10px; font-weight: bold; background: transparent;")
            self.lbl_led.setText("●")
            self.lbl_led.setStyleSheet(f"color: {danger}; font-size: 14px; background: transparent;")
        elif is_recording and is_paused:
            self.lbl_status.setText(tr("recording.bar_paused", "PAUSA"))
            self.lbl_status.setStyleSheet(f"color: {warning}; font-size: 10px; font-weight: bold; background: transparent;")
            self.lbl_led.setText("●")
            self.lbl_led.setStyleSheet(f"color: {warning}; font-size: 14px; background: transparent;")

        self._update_icons()

    def _retranslate(self) -> None:
        self.btn_stop.setToolTip(tr("recording.stop_tip", "Parar Gravação (Pergunta para Salvar)"))
        self.btn_save.setToolTip(tr("recording.save_tip", "Salvar Vídeo..."))
        self.update_state(self._recording, self._paused)

    def update_pulse(self, state: bool) -> None:
        """Sincroniza a animação de pulso do LED com o painel."""
        if self._recording and not self._paused:
            color = ThemeManager.instance().get_color("DANGER", "#f85149") if state else "transparent"
            self.lbl_led.setStyleSheet(f"color: {color}; font-size: 14px; background: transparent;")

    def update_stats(self, frames: int, elapsed_secs: int) -> None:
        """Atualiza a contagem de tempo e de quadros."""
        h = elapsed_secs // 3600
        m = (elapsed_secs % 3600) // 60
        s = elapsed_secs % 60
        self.lbl_time.setText(f"{h:02d}:{m:02d}:{s:02d}")
        self.lbl_frames.setText(f"({frames} f)")

    def reposition_to_top_anchor(self) -> None:
        """Posiciona a barra flutuante centralizada na âncora do topo do viewport (canvas)."""
        ref_widget = self._anchor
        if ref_widget is None or not ref_widget.isVisible():
            ref_widget = self.parentWidget()

        if ref_widget is None:
            return

        ref_global = ref_widget.mapToGlobal(QtCore.QPoint(0, 0))
        ref_w = ref_widget.width()

        self.adjustSize()
        bar_w = self.width() if self.width() > 50 else self.sizeHint().width()

        gx = ref_global.x() + (ref_w - bar_w) // 2
        gy = ref_global.y() + 14

        # Limita às bordas visíveis
        gx = max(ref_global.x() + 12, min(ref_global.x() + ref_w - bar_w - 12, gx))
        self.move(gx, gy)

    def show_bar(self) -> None:
        """Exibe a barra reposicionada na âncora superior."""
        self._user_dragged = False
        self.adjustSize()
        self.reposition_to_top_anchor()
        self.show()
        self.raise_()

    def hide_bar(self) -> None:
        """Oculta a barra."""
        self.hide()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._drag_pos and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self._user_dragged = True
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._drag_pos:
            self._drag_pos = None
            event.accept()
        super().mouseReleaseEvent(event)
