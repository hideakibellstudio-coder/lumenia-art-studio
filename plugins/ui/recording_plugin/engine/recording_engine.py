"""
Timelapse Recording Engine — Motor de Captura e Sessão de Gravação (ARCcC).
==========================================================================
Gerencia o ciclo de vida da gravação de traços e timelapse do canvas:
  - Captura assíncrona não-bloqueante via QThreadPool para zero stutter durante o desenho.
  - Conversão direta de buffers de display em arquivos JPEG numerados em pasta temporária.
  - Suporte a gatilho por traço (debounce de strokeFinished) e por tempo (QTimer).
  - Controle de resolução (Original, 1080p, 720p) e contabilidade de diagnósticos em disco.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import logging
from typing import Optional

from PySide6 import QtCore, QtGui

logger = logging.getLogger(__name__)


class FrameSaveTask(QtCore.QRunnable):
    """Tarefa assíncrona de escrita de imagem para não engasgar o traçado da caneta."""

    def __init__(self, raw_bytes: bytes, width: int, height: int, target_w: int, target_h: int, output_path: str):
        super().__init__()
        self.raw_bytes = raw_bytes
        self.width = width
        self.height = height
        self.target_w = target_w
        self.target_h = target_h
        self.output_path = output_path

    def run(self) -> None:
        try:
            # Constrói QImage a partir do buffer RGBA
            img = QtGui.QImage(
                self.raw_bytes,
                self.width,
                self.height,
                self.width * 4,
                QtGui.QImage.Format.Format_RGBA8888
            )
            if img.isNull():
                return

            # Redimensiona se resolução alvo for diferente e válida
            if self.target_w > 0 and self.target_h > 0 and (self.target_w != self.width or self.target_h != self.height):
                img = img.scaled(
                    self.target_w,
                    self.target_h,
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation
                )

            # Salva JPEG com compressão otimizada
            img.save(self.output_path, "JPEG", 90)
        except Exception as e:
            logger.error("[TimelapseEngine] Falha ao salvar frame %s: %s", self.output_path, e)


class TimelapseRecordingEngine(QtCore.QObject):
    """Motor autônomo e não-bloqueante de gravação de timelapse."""

    state_changed = QtCore.Signal(bool, bool)  # (is_recording, is_paused)
    stats_updated = QtCore.Signal(int, float, float)  # (frames, size_mb, duration_secs)
    frame_captured = QtCore.Signal(int)  # frame_count

    def __init__(self, parent: Optional[QtCore.QObject] = None):
        super().__init__(parent)
        self.is_recording: bool = False
        self.is_paused: bool = False
        self.frame_count: int = 0
        self.elapsed_seconds: int = 0
        self.temp_dir: Optional[str] = None
        self.target_resolution: str = "Original (Canvas)"
        self.trigger_mode: str = "stroke"  # 'stroke' ou 'time'

        self._connected_canvas = None
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

    def attach_canvas(self, canvas: QtCore.QObject) -> None:
        """Conecta o sinal strokeFinished do canvas ativo para captura automática."""
        if self._connected_canvas == canvas:
            return
        if self._connected_canvas is not None and hasattr(self._connected_canvas, "strokeFinished"):
            try:
                self._connected_canvas.strokeFinished.disconnect(self._on_canvas_stroke_finished)
            except Exception:
                pass

        self._connected_canvas = canvas
        if canvas is not None and hasattr(canvas, "strokeFinished"):
            canvas.strokeFinished.connect(self._on_canvas_stroke_finished)
            logger.info("[TimelapseEngine] Conectado ao canvas com sucesso.")

    def detach_canvas(self) -> None:
        """Desconecta o canvas."""
        if self._connected_canvas is not None and hasattr(self._connected_canvas, "strokeFinished"):
            try:
                self._connected_canvas.strokeFinished.disconnect(self._on_canvas_stroke_finished)
            except Exception:
                pass
        self._connected_canvas = None

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

    def capture_current_frame(self) -> None:
        """Extrai o buffer de pixels atual da engine e despacha para salvamento assíncrono."""
        if not self.is_recording or self.is_paused or not self.temp_dir:
            return
        if self._connected_canvas is None:
            return

        canvas = self._connected_canvas
        backend = getattr(canvas, "engine_backend", None)
        if backend is None or not hasattr(backend, "get_display_pixel_buffer"):
            return

        raw_buf = backend.get_display_pixel_buffer()
        if not raw_buf:
            return

        # Garante cópia isolada dos bytes em memória para a thread secundária
        raw_bytes = bytes(raw_buf)
        cw = int(getattr(canvas, "canvas_w", 0))
        ch = int(getattr(canvas, "canvas_h", 0))
        if cw <= 0 or ch <= 0:
            return

        # Resolução alvo calculada
        tw, th = cw, ch
        if "1080p" in self.target_resolution:
            tw, th = 1920, 1080
        elif "720p" in self.target_resolution:
            tw, th = 1280, 720

        self.frame_count += 1
        frame_name = f"frame_{self.frame_count:06d}.jpg"
        out_path = os.path.join(self.temp_dir, frame_name)

        task = FrameSaveTask(raw_bytes, cw, ch, tw, th, out_path)
        self._thread_pool.start(task)

        self.frame_captured.emit(self.frame_count)
        self._emit_stats()

    def _on_canvas_stroke_finished(self) -> None:
        """Gatilho acionado ao término de cada traçado."""
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
            except Exception:
                pass
        duration_secs = self.frame_count / 30.0
        self.stats_updated.emit(self.frame_count, size_mb, duration_secs)

    def cleanup_temp_files(self) -> None:
        """Remove os arquivos de rascunho temporários da gravação."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            except Exception as e:
                logger.warning("[TimelapseEngine] Erro ao limpar temp dir: %s", e)
        self.temp_dir = None
