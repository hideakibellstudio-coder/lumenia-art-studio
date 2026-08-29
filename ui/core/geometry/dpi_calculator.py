"""
ui.core.geometry.dpi_calculator — Utilitário de Conversão e Métricas Físicas Baseadas em DPI
===========================================================================================
Fornece cálculos precisos para dimensões físicas de impressão, conversão de unidades
(mm, cm, polegadas, pontos tipográficos pt) e suporte a réguas calibradas por documento.
"""

from typing import Tuple

MM_PER_INCH = 25.4
POINTS_PER_INCH = 72.0


def px_to_inches(px: float, dpi: float = 300.0) -> float:
    """Converte pixels para polegadas físicas."""
    if dpi <= 0:
        return 0.0
    return px / dpi


def inches_to_px(inches: float, dpi: float = 300.0) -> int:
    """Converte polegadas físicas para pixels."""
    return int(round(inches * max(1.0, dpi)))


def px_to_mm(px: float, dpi: float = 300.0) -> float:
    """Converte pixels para milímetros físicos."""
    return px_to_inches(px, dpi) * MM_PER_INCH


def mm_to_px(mm: float, dpi: float = 300.0) -> int:
    """Converte milímetros físicos para pixels."""
    return inches_to_px(mm / MM_PER_INCH, dpi)


def px_to_cm(px: float, dpi: float = 300.0) -> float:
    """Converte pixels para centímetros físicos."""
    return px_to_mm(px, dpi) / 10.0


def cm_to_px(cm: float, dpi: float = 300.0) -> int:
    """Converte centímetros físicos para pixels."""
    return mm_to_px(cm * 10.0, dpi)


def pt_to_px(pt: float, dpi: float = 300.0) -> float:
    """Converte pontos tipográficos (pt, 1/72 polegada) para pixels em uma dada resolução DPI."""
    return (pt / POINTS_PER_INCH) * max(1.0, dpi)


def px_to_pt(px: float, dpi: float = 300.0) -> float:
    """Converte pixels para pontos tipográficos (pt) na resolução DPI indicada."""
    if dpi <= 0:
        return 0.0
    return (px / dpi) * POINTS_PER_INCH


def calculate_print_dimensions(w_px: int, h_px: int, dpi: float = 300.0) -> Tuple[float, float, str]:
    """
    Retorna a largura e altura em milímetros e uma string formatada para exibição em UI.
    Exemplo: (210.0, 297.0, '210.0 × 297.0 mm (A4) @ 300 DPI')
    """
    w_mm = px_to_mm(w_px, dpi)
    h_mm = px_to_mm(h_px, dpi)
    formatted = f"{w_mm:.1f} × {h_mm:.1f} mm ({w_px}×{h_px} px @ {int(dpi)} DPI)"
    return w_mm, h_mm, formatted
