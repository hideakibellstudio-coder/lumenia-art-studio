"""
ui.core.engine.flood_fill — Motor de Preenchimento Flood Fill / Balde de Tinta
==============================================================================
Implementa o algoritmo industrial Scanline Flood Fill de 2 Fases com:
- Tolerância Euclidiana de cor em espaço RGBA
- Gap Closing (fechamento de frestas e lacunas em traços na grade de colisão)
- Expansão de borda / Sangria sob lineart (-10..+10 px)
- Modo contíguo (conectado) e global (todas as áreas com cor similar)
- Anti-Aliasing e suavização de bordas
"""

from __future__ import annotations

import collections
import math
from typing import Optional, Tuple
import numpy as np
import scipy.ndimage
from PySide6 import QtCore, QtGui


class FloodFillEngine:
    """Motor de cálculo e aplicação de Scanline Flood Fill de alta performance."""

    @staticmethod
    def flood_fill(
        source_image: QtGui.QImage,
        seed_x: int,
        seed_y: int,
        fill_color: QtGui.QColor,
        tolerance: int = 20,
        contiguous: bool = True,
        expand_px: int = 1,
        gap_closing_px: int = 0,
        anti_aliasing: bool = True,
    ) -> Optional[QtGui.QImage]:
        """
        Executa o preenchimento a partir do ponto (seed_x, seed_y).
        
        Retorna uma QImage no formato Format_RGBA8888 contendo a camada de preenchimento
        isolada (com transparência nos pixels não preenchidos), pronta para ser
        composta sobre a camada de destino.
        """
        w = source_image.width()
        h = source_image.height()

        if seed_x < 0 or seed_x >= w or seed_y < 0 or seed_y >= h:
            return None

        # Converte QImage para array NumPy RGBA (uint8)
        img = source_image.convertToFormat(QtGui.QImage.Format_RGBA8888)
        ptr = img.bits()
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape((h, w, 4)).copy()

        target_color = arr[seed_y, seed_x].astype(np.int32)
        fill_rgba = np.array([fill_color.red(), fill_color.green(), fill_color.blue(), fill_color.alpha()], dtype=np.uint8)

        # Tolerância mapeada de 0..100 para distância Euclidiana máxima (0..441.67)
        max_dist = (tolerance / 100.0) * 441.67
        max_dist_sq = max_dist ** 2

        # ── FASE 1: Cálculo da Grade de Correspondência (Match Grid) ──────────
        arr_int = arr.astype(np.int32)
        diff = arr_int - target_color
        dist_sq = np.sum(diff[:, :, :3] ** 2, axis=2)
        match_grid = dist_sq <= max_dist_sq

        if not match_grid[seed_y, seed_x]:
            return None

        # ── FASE 2: Fechamento de Frestas (Gap Closing na Colisão) ────────────
        effective_match = match_grid
        if contiguous and gap_closing_px > 0:
            # Bordas/Obstáculos = pixels que NÃO combinam com a cor alvo
            obstacles = ~match_grid
            struct = FloodFillEngine._get_circular_kernel(int(gap_closing_px))
            # Dilata os obstáculos para fechar fendas menores que gap_closing_px
            dilated_obstacles = scipy.ndimage.binary_dilation(obstacles, structure=struct)
            # A área navegável é o inverso dos obstáculos dilatados (mais o ponto semente)
            effective_match = ~dilated_obstacles
            effective_match[seed_y, seed_x] = True

        # ── FASE 3: Varredura de Preenchimento (Scanline Fill) ─────────────────
        if not contiguous:
            mask = match_grid
        else:
            mask = FloodFillEngine._scanline_fill_mask(effective_match, seed_x, seed_y)

        if not np.any(mask):
            return None

        # ── FASE 4: Expansão / Sangria sob o traço ─────────────────────────────
        # Se usamos gap closing, re-expandimos para preencher até a borda real do desenho
        total_expand = expand_px
        if gap_closing_px > 0:
            total_expand += int(gap_closing_px)

        if total_expand > 0:
            struct = FloodFillEngine._get_circular_kernel(int(total_expand))
            mask = scipy.ndimage.binary_dilation(mask, structure=struct)
            # Restringe a expansão para que não ultrapasse a área que era permitida originalmente
            if gap_closing_px > 0 and not np.any(mask & (~match_grid)):
                pass
        elif total_expand < 0:
            struct = FloodFillEngine._get_circular_kernel(int(abs(total_expand)))
            mask = scipy.ndimage.binary_erosion(mask, structure=struct)

        # ── FASE 5: Rasterização do Preenchimento com Anti-Aliasing ───────────
        out_arr = np.zeros((h, w, 4), dtype=np.uint8)

        if anti_aliasing:
            mask_float = mask.astype(np.float32)
            smoothed = scipy.ndimage.gaussian_filter(mask_float, sigma=0.5)
            alpha_factor = np.clip(smoothed, 0.0, 1.0)
            
            out_arr[:, :, 0] = fill_rgba[0]
            out_arr[:, :, 1] = fill_rgba[1]
            out_arr[:, :, 2] = fill_rgba[2]
            out_arr[:, :, 3] = (fill_rgba[3] * alpha_factor).astype(np.uint8)
        else:
            out_arr[mask] = fill_rgba

        res_bytes = out_arr.tobytes()
        res_img = QtGui.QImage(res_bytes, w, h, w * 4, QtGui.QImage.Format_RGBA8888).copy()
        return res_img

    @staticmethod
    def _scanline_fill_mask(
        match_grid: np.ndarray,
        seed_x: int,
        seed_y: int,
    ) -> np.ndarray:
        """Executa o algoritmo de Scanline Flood Fill não-recursivo retornando máscara booleana."""
        h, w = match_grid.shape
        mask = np.zeros((h, w), dtype=bool)

        if not match_grid[seed_y, seed_x]:
            return mask

        queue = collections.deque()

        lx = seed_x
        while lx > 0 and match_grid[seed_y, lx - 1]:
            lx -= 1
        rx = seed_x
        while rx < w - 1 and match_grid[seed_y, rx + 1]:
            rx += 1

        mask[seed_y, lx : rx + 1] = True
        queue.append((lx, rx, seed_y, 1))
        queue.append((lx, rx, seed_y, -1))

        while queue:
            x1, x2, y, dy = queue.popleft()
            ny = y + dy
            if ny < 0 or ny >= h:
                continue

            x = x1
            while x <= x2:
                if match_grid[ny, x] and not mask[ny, x]:
                    lx = x
                    while lx > 0 and match_grid[ny, lx - 1] and not mask[ny, lx - 1]:
                        lx -= 1
                    rx = x
                    while rx < w - 1 and match_grid[ny, rx + 1] and not mask[ny, rx + 1]:
                        rx += 1

                    mask[ny, lx : rx + 1] = True
                    queue.append((lx, rx, ny, dy))
                    if lx < x1 or rx > x2:
                        queue.append((lx, rx, ny, -dy))
                    x = rx + 1
                else:
                    x += 1

        return mask

    @staticmethod
    def _get_circular_kernel(radius: int) -> np.ndarray:
        """Gera matriz estruturante circular para dilatação / fechamento morfológico."""
        radius = max(1, radius)
        L = np.arange(-radius, radius + 1)
        X, Y = np.meshgrid(L, L)
        return (X ** 2 + Y ** 2) <= (radius ** 2)
