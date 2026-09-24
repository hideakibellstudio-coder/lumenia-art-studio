"""
Timelapse Recording Engine — Motor de Captura e Sessão de Gravação (ARCcC).
==========================================================================
Gerencia o ciclo de vida da gravação de traços e timelapse do canvas:
  - Captura assíncrona não-bloqueante via QThreadPool para zero stutter durante o desenho.
  - Conversão direta de buffers de display em arquivos JPEG numerados em pasta temporária.
  - Suporte a gatilho por traço (debounce de strokeFinished) e por tempo (QTimer).
  - Controle de resolução (Original, 1080p, 720p) e contabilidade de diagnósticos em disco.

Não conhece o canvas: o quadro vem da `frame_source` (padrão: documento ativo
+ motor, `frame_source.DocumentFrameSource`) e o fim de cada traço chega por
`on_stroke_finished`, que o plugin liga ao `strokeFinished` do canvas.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import logging
from typing import Callable, Optional

from PySide6 import QtCore, QtGui

from .frame_save_task import FrameSaveTask
from .frame_source import DocumentFrameSource, Frame

FrameGrabber = Callable[[bool], Optional[Frame]]

logger = logging.getLogger(__name__)


class TimelapseRecordingEngine(QtCore.QObject):
    """Motor autônomo e não-bloqueante de gravação de timelapse."""

    state_changed = QtCore.Signal(bool, bool)  # (is_recording, is_paused)
    stats_updated = QtCore.Signal(int, float, float)  # (frames, size_mb, duration_secs)
    frame_captured = QtCore.Signal(int)  # frame_count

    def __init__(self, frame_source: Optional[FrameGrabber] = None, parent: Optional[QtCore.QObject] = None):
        super().__init__(parent)
        self._grab_frame: FrameGrabber = frame_source or DocumentFrameSource()
        self.is_recording: bool = False
        self.is_paused: bool = False
        self.frame_count: int = 0
        self.elapsed_seconds: int = 0
        self.temp_dir: Optional[str] = None
        self.target_resolution: str = "Original (Canvas)"
        self.trigger_mode: str = "stroke"  # 'stroke' ou 'time'
        self.add_watermark: bool = True
        self.include_guides: bool = False
        self.fps: int = 30
        self._guides_renderer: Optional[Callable] = None
        self._thread_pool = QtCore.QThreadPool.globalInstance()

        # Timers
        self.sec_timer = QtCore.QTimer(self)
        self.sec_timer.setInterval(1000)
        self.sec_timer.timeout.connect(self._on_second_tick)

        self.time_trigger_timer = QtCore.QTimer(self)
        self.time_trigger_timer.setInterval(2000)
        self.time_trigger_timer.timeout.connect(self._on_time_trigger_tick)

        self.stroke_debounce_timer = QtCore.QTimer(self)
        self.stroke_debounce_timer.setSingleShot(True)
        self.stroke_debounce_timer.setInterval(50)
        self.stroke_debounce_timer.timeout.connect(self._execute_debounced_capture)

    def set_guides_renderer(self, renderer: Optional[Callable]) -> None:
        """Desenha guias e simetria no quadro (o plugin entrega `WorkspaceService.render_geometry_overlay`)."""
        self._guides_renderer = renderer

    def start_recording(self) -> bool:
        """Inicia uma nova sessão de gravação com pasta temporária limpa."""
        if self.is_recording:
            return False

        self.cleanup_temp_files()
        try:
            self.temp_dir = tempfile.mkdtemp(prefix="lumenia_timelapse_")
        except Exception as e:
            logger.error("[TimelapseEngine] Falha ao criar temp dir: %s", e)
            return False

        self.is_recording = True
        self.is_paused = False
        self.frame_count = 0
        self.elapsed_seconds = 0

        self.sec_timer.start()
        if self.trigger_mode == "time":
            self.time_trigger_timer.start()

        # Captura imediatamente o estado inicial do canvas como frame 1
        self.capture_current_frame()

        self.state_changed.emit(True, False)
        self._emit_stats()
        logger.info("[TimelapseEngine] Gravação iniciada em %s", self.temp_dir)
        return True

    def pause_recording(self) -> None:
        """Pausa temporariamente a gravação sem descartar os quadros."""
        if not self.is_recording or self.is_paused:
            return
        self.is_paused = True
        self.sec_timer.stop()
        self.time_trigger_timer.stop()
        self.stroke_debounce_timer.stop()
        self.state_changed.emit(True, True)
        logger.info("[TimelapseEngine] Gravação pausada.")

    def resume_recording(self) -> None:
        """Retoma uma gravação pausada."""
        if not self.is_recording or not self.is_paused:
            return
        self.is_paused = False
        self.sec_timer.start()
        if self.trigger_mode == "time":
            self.time_trigger_timer.start()
        self.state_changed.emit(True, False)
        logger.info("[TimelapseEngine] Gravação retomada.")

    def discard_recording(self) -> None:
        """Descarta e apaga permanentemente a sessão atual."""
        self.sec_timer.stop()
        self.time_trigger_timer.stop()
        self.stroke_debounce_timer.stop()
        self.cleanup_temp_files()

        self.is_recording = False
        self.is_paused = False
        self.frame_count = 0
        self.elapsed_seconds = 0

        self.state_changed.emit(False, False)
        self._emit_stats()
        logger.info("[TimelapseEngine] Gravação descartada e arquivos temporários removidos.")

    def stop_recording(self) -> Optional[str]:
        """Finaliza a gravação e retorna o caminho da pasta temporária com os frames."""
        if not self.is_recording:
            return None
        self.sec_timer.stop()
        self.time_trigger_timer.stop()
        self.stroke_debounce_timer.stop()

        self.is_recording = False
        self.is_paused = False
        self.state_changed.emit(False, False)
        return self.temp_dir

    @staticmethod
    def apply_watermark(img: QtGui.QImage) -> None:
        """Desenha a marca d'água oficial proporcional do Lumenia (ícone + nome) no canto inferior direito."""
        w, h = img.width(), img.height()
        if w < 160 or h < 120:
            return

        ref_dim = min(w, h)
        icon_target_h = max(42, int(ref_dim * 0.135))
        margin = max(18, int(ref_dim * 0.035))
        gap = max(4, int(icon_target_h * 0.06))
        font_pixel_size = max(11, int(icon_target_h * 0.16))

        font = QtGui.QFont("Segoe UI", 10, QtGui.QFont.Weight.Bold)
        font.setPixelSize(font_pixel_size)
        font.setLetterSpacing(QtGui.QFont.SpacingType.AbsoluteSpacing, max(1.5, font_pixel_size * 0.12))

        fm = QtGui.QFontMetrics(font)
        text = "LUMENIA"
        text_w = fm.horizontalAdvance(text)
        text_h = fm.height()

        # Carrega ícone com recorte justo (sem áreas transparentes excessivas)
        icon_pix = None
        try:
            from ui.core.runtime_paths import resource_path
            tight_path = str(resource_path("assets", "images", "icon_lumenia_tight.png"))
            base_path = str(resource_path("assets", "images", "icon_lumenia.png"))
            if os.path.exists(tight_path):
                src_pix = QtGui.QPixmap(tight_path)
            elif os.path.exists(base_path):
                src_pix = QtGui.QPixmap(base_path).copy(QtCore.QRect(330, 118, 362, 644))
            else:
                src_pix = None

            if src_pix and not src_pix.isNull():
                icon_pix = src_pix.scaledToHeight(
                    icon_target_h,
                    QtCore.Qt.TransformationMode.SmoothTransformation
                )
        except Exception as e:
            logger.debug("[TimelapseEngine] Falha ao carregar ícone para marca d'água: %s", e)

        icon_w = icon_pix.width() if icon_pix else icon_target_h
        icon_h = icon_pix.height() if icon_pix else icon_target_h

        total_w = max(icon_w, text_w)
        total_h = icon_h + gap + text_h

        x = float(w - total_w - margin)
        y = float(h - total_h - margin)
        icon_x = x + (total_w - icon_w) / 2.0
        icon_y = y

        painter = QtGui.QPainter(img)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)

        # 1. Ícone com sombra suave de destaque
        if icon_pix:
            shadow_offset = max(2.0, icon_target_h * 0.025)
            painter.save()
            painter.setOpacity(0.30)
            painter.drawPixmap(int(icon_x + shadow_offset), int(icon_y + shadow_offset), icon_pix)
            painter.restore()

            painter.save()
            painter.setOpacity(0.95)
            painter.drawPixmap(int(icon_x), int(icon_y), icon_pix)
            painter.restore()

        # 2. Tipografia 'LUMENIA' com contorno protetor (legibilidade em qualquer fundo)
        text_x = x + (total_w - text_w) / 2.0
        text_baseline_y = y + icon_h + gap + fm.ascent()

        path = QtGui.QPainterPath()
        path.addText(text_x, text_baseline_y, font, text)

        stroke_w = max(2.2, font_pixel_size * 0.15)
        pen = QtGui.QPen(
            QtGui.QColor(15, 18, 22, 180),
            stroke_w,
            QtCore.Qt.PenStyle.SolidLine,
            QtCore.Qt.PenCapStyle.RoundCap,
            QtCore.Qt.PenJoinStyle.RoundJoin
        )
        painter.strokePath(path, pen)
        painter.fillPath(path, QtGui.QColor(250, 252, 255, 245))

        painter.end()

    def capture_current_frame(self) -> None:
        """Pega o quadro atual da fonte e despacha o salvamento assíncrono."""
        if not self.is_recording or self.is_paused or not self.temp_dir:
            return
        frame = self._grab_frame(self.include_guides)
        if frame is None or frame.width <= 0 or frame.height <= 0:
            return

        tw, th = frame.width, frame.height
        if "1080p" in self.target_resolution:
            tw, th = 1920, 1080
        elif "720p" in self.target_resolution:
            tw, th = 1280, 720

        self.frame_count += 1
        out_path = os.path.join(self.temp_dir, f"frame_{self.frame_count:06d}.jpg")
        task = FrameSaveTask(
            frame.pixels,
            frame.width,
            frame.height,
            tw,
            th,
            out_path,
            watermark=self.add_watermark,
            guides_data=frame.guides,
            guides_renderer=self._guides_renderer if frame.guides else None,
        )
        self._thread_pool.start(task)

        self.frame_captured.emit(self.frame_count)
        self._emit_stats()

    def on_stroke_finished(self) -> None:
        """Fim de um traço (o plugin liga ao `strokeFinished` do canvas)."""
        if self.is_recording and not self.is_paused and self.trigger_mode == "stroke":
            self.stroke_debounce_timer.start()

    def _execute_debounced_capture(self) -> None:
        self.capture_current_frame()

    def _on_second_tick(self) -> None:
        self.elapsed_seconds += 1
        self._emit_stats()

    def _on_time_trigger_tick(self) -> None:
        if self.is_recording and not self.is_paused and self.trigger_mode == "time":
            self.capture_current_frame()

    def _emit_stats(self) -> None:
        size_mb = 0.0
        if self.temp_dir and os.path.isdir(self.temp_dir):
            try:
                total_bytes = sum(os.path.getsize(os.path.join(self.temp_dir, f)) for f in os.listdir(self.temp_dir))
                size_mb = total_bytes / (1024.0 * 1024.0)
            except OSError:
                pass  # arquivo sumiu durante a contagem
        duration_secs = self.frame_count / float(max(1, self.fps))
        self.stats_updated.emit(self.frame_count, size_mb, duration_secs)

    def finish_session(self) -> None:
        """Depois de exportar: apaga os quadros temporários e zera os contadores."""
        self.cleanup_temp_files()
        self.frame_count = 0
        self.elapsed_seconds = 0
        self._emit_stats()

    def cleanup_temp_files(self) -> None:
        """Remove os arquivos de rascunho temporários da gravação."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            except Exception as e:
                logger.warning("[TimelapseEngine] Erro ao limpar temp dir: %s", e)
        self.temp_dir = None
