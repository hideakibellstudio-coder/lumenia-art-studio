"""interface_tweaks — ajustes finos do usuário por cima do tema (raio dos cantos e fonte).

Os temas definem `RADIUS_SMALL/MEDIUM/LARGE/XLARGE` e `FONT_FAMILY` nas
métricas; os módulos QSS usam esses tokens. O usuário pode sobrepor os dois
no diálogo de temas (valem para qualquer tema e ficam nas preferências).
Até 2026-09-24 os combos "Raio dos Cantos" e "Família da Fonte" existiam no
diálogo sem estar ligados a nada.
"""
from __future__ import annotations

from typing import Optional

# Raio base (px) oferecido no diálogo; None = o do tema.
RADIUS_CHOICES: tuple[Optional[int], ...] = (None, 0, 4, 8, 16)

# Fonte oferecida no diálogo; None = a do tema (Segoe UI em todos os temas embutidos).
FONT_STACKS: dict[str, str] = {
    "roboto": "Roboto, -apple-system, 'Segoe UI', Arial, sans-serif",
    "inter": "'Inter', 'Inter Display', 'Segoe UI', Arial, sans-serif",
    "helvetica": "'Helvetica Neue', Helvetica, Arial, sans-serif",
}
FONT_CHOICES: tuple[Optional[str], ...] = (None, "roboto", "inter", "helvetica")


def radius_metrics(base_px: int) -> dict[str, str]:
    """Raios derivados de um raio base (o padrão dos temas, 4/6/8/12, é base 8)."""
    base = max(0, int(base_px))
    return {
        "RADIUS_SMALL": f"{round(base * 0.5)}px",
        "RADIUS_MEDIUM": f"{round(base * 0.75)}px",
        "RADIUS_LARGE": f"{base}px",
        "RADIUS_XLARGE": f"{round(base * 1.5)}px",
    }


def tweak_metrics(radius_px: Optional[int], font_key: Optional[str]) -> dict[str, str]:
    """Métricas que sobrepõem as do tema (vazio = nada sobreposto)."""
    metrics: dict[str, str] = {}
    if radius_px is not None:
        metrics.update(radius_metrics(radius_px))
    if font_key in FONT_STACKS:
        metrics["FONT_FAMILY"] = FONT_STACKS[font_key]
    return metrics


def valid_radius(value) -> Optional[int]:
    """Valor salvo nas preferências → raio oferecido, ou None (o do tema)."""
    return value if type(value) is int and value in RADIUS_CHOICES else None


def valid_font(value) -> Optional[str]:
    return value if value in FONT_STACKS else None
