"""
Timelapse Export Worker — Compilador Assíncrono FFmpeg e Fallback ZIP (ARCcC).
=============================================================================
Converte sequências de imagens de timelapse em vídeos MP4 H.264 ou pacotes ZIP:
  - Detecção transparente do executável FFmpeg no PATH do sistema.
  - Execução assíncrona via QProcess com streaming de progresso em tempo real.
  - Empacotamento direto em arquivo ZIP como fallback universal ou opção nativa.
"""

from __future__ import annotations

import os
import shutil
import zipfile
import logging
from typing import Optional

from PySide6 import QtCore

logger = logging.getLogger(__name__)


class TimelapseExportWorker(QtCore.QObject):
    """Worker de compilação de vídeo e empacotamento com suporte a cancelamento."""

    progress = QtCore.Signal(int, str, str)  # (percent, status_text, details_text)
    finished = QtCore.Signal(bool, str, str)  # (success, message, output_path)

    def __init__(self, temp_dir: str, total_frames: int, parent: Optional[QtCore.QObject] = None):
        super().__init__(parent)
        self.temp_dir = temp_dir
        self.total_frames = max(1, total_frames)
        self._process: Optional[QtCore.QProcess] = None
        self._is_cancelled: bool = False

    @staticmethod
    def is_ffmpeg_available() -> bool:
        """Verifica se o utilitário FFmpeg está acessível no ambiente."""
        return shutil.which("ffmpeg") is not None

    def export(self, target_path: str, format_type: str = "mp4") -> None:
        """Dispara a compilação do timelapse no formato selecionado."""
        self._is_cancelled = False
        target_ext = os.path.splitext(target_path)[1].lower()

        if target_ext == ".zip" or "zip" in format_type.lower():
            self._export_zip(target_path)
        else:
            if self.is_ffmpeg_available():
                self._export_ffmpeg(target_path)
            else:
                fallback_zip = os.path.splitext(target_path)[0] + ".zip"
                self._export_zip(fallback_zip, was_fallback=True)

    def cancel(self) -> None:
        """Interrompe a exportação em andamento."""
        self._is_cancelled = True
        if self._process is not None and self._process.state() != QtCore.QProcess.ProcessState.NotRunning:
            try:
                self._process.kill()
            except Exception as e:
                logger.warning("[ExportWorker] Erro ao interromper FFmpeg: %s", e)
        self.finished.emit(False, "Exportação cancelada pelo usuário.", "")

    def _export_ffmpeg(self, output_mp4: str) -> None:
        """Compila a sequência em MP4 H.264 via processo externo FFmpeg."""
        ffmpeg_bin = shutil.which("ffmpeg")
        if not ffmpeg_bin:
            self.finished.emit(False, "Executável FFmpeg não encontrado.", "")
            return

        self.progress.emit(5, "Iniciando compilação de vídeo...", "Configurando decodificador H.264...")

        self._process = QtCore.QProcess(self)
        self._process.setWorkingDirectory(self.temp_dir)

        args = [
            "-y",
            "-r", "30",
            "-f", "image2",
            "-i", "frame_%06d.jpg",
            "-vcodec", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "23",
            output_mp4
        ]

        def on_ready_read_stderr():
            if self._is_cancelled or not self._process:
                return
            try:
                raw_out = self._process.readAllStandardError().data().decode("utf-8", errors="ignore")
                if "frame=" in raw_out:
                    parts = raw_out.split("frame=")[1].strip().split()
                    if parts:
                        cur_frame = int(parts[0])
                        pct = min(95, int((cur_frame / self.total_frames) * 90) + 5)
                        self.progress.emit(
                            pct,
                            "Codificando quadros em H.264...",
                            f"Quadro {cur_frame} de {self.total_frames} processado."
                        )
            except Exception:
                pass

        def on_process_finished(exit_code: int, exit_status: QtCore.QProcess.ExitStatus):
            if self._is_cancelled:
                return
            if exit_code == 0:
                self.progress.emit(100, "Concluído com sucesso!", f"Vídeo gravado em {os.path.basename(output_mp4)}")
                self.finished.emit(True, f"Timelapse exportado com sucesso para:\n{output_mp4}", output_mp4)
            else:
                logger.error("[ExportWorker] FFmpeg falhou com código %d", exit_code)
                fallback_zip = os.path.splitext(output_mp4)[0] + ".zip"
                self._export_zip(fallback_zip, was_fallback=True)

        self._process.readyReadStandardError.connect(on_ready_read_stderr)
        self._process.finished.connect(on_process_finished)
        self._process.start(ffmpeg_bin, args)

    def _export_zip(self, output_zip: str, was_fallback: bool = False) -> None:
        """Compacta todos os frames JPEG em um arquivo ZIP com feedback progressivo."""
        if not self.temp_dir or not os.path.isdir(self.temp_dir):
            self.finished.emit(False, "Pasta de rascunhos temporários inválida ou vazia.", "")
            return

        self.progress.emit(5, "Empacotando sequência de imagens...", "Inicializando arquivo ZIP...")
        try:
            files = sorted([f for f in os.listdir(self.temp_dir) if f.startswith("frame_") and f.endswith(".jpg")])
            total = len(files)
            if total == 0:
                self.finished.emit(False, "Nenhum quadro disponível para exportar.", "")
                return

            with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                for idx, fname in enumerate(files):
                    if self._is_cancelled:
                        return
                    fpath = os.path.join(self.temp_dir, fname)
                    zf.write(fpath, fname)

                    if idx % 10 == 0 or idx == total - 1:
                        pct = min(98, int(((idx + 1) / total) * 90) + 8)
                        self.progress.emit(
                            pct,
                            "Comprimindo quadros JPEG...",
                            f"Compactando {idx + 1} de {total}..."
                        )

            self.progress.emit(100, "Concluído!", f"Salvo em: {os.path.basename(output_zip)}")
            msg = f"Sequência de quadros exportada com sucesso em:\n{output_zip}"
            if was_fallback:
                msg = f"FFmpeg não foi localizado no PATH do sistema.\nA sequência de {total} quadros foi empacotada em:\n{output_zip}"
            self.finished.emit(True, msg, output_zip)
        except Exception as e:
            logger.error("[ExportWorker] Erro ao criar ZIP: %s", e)
            self.finished.emit(False, f"Falha ao empacotar sequência: {e}", "")
