"""Cores das sobreposições desenhadas sobre a arte: guias de perspectiva,
formigas da seleção, alças da transformação, lupa do conta-gotas.

Não são cores de interface. Precisam contrastar com o desenho, não com o
painel, então são as mesmas em qualquer tema. Até 2026-09-25 eram 42
literais `QColor(r, g, b, a)` espalhados por `perspective_grid_renderer.py` e
`overlay_renderer.py` (Lei 5); agora cada uma tem nome e mora aqui, no pacote
do tema. Uso: `QtGui.QColor(*OverlayPalette.NOME)`.
"""

from __future__ import annotations


class OverlayPalette:
    # ── Perspectiva de 1, 2 e 3 pontos ──────────────────────────────────────
    HORIZON = (234, 88, 12, 180)             # linha do horizonte
    VANISHING_POINT = (234, 88, 12, 220)     # disco do ponto de fuga
    VANISHING_RAYS = (234, 88, 12, 90)       # raios tracejados saindo do ponto
    SNAP_RAY_ACTIVE = (255, 125, 45, 210)    # raio sob o cursor
    ISOMETRIC_GRID = (59, 130, 246, 75)

    # ── Perspectiva curvilínea (6 pontos) ───────────────────────────────────
    CURV_RING = (168, 85, 247, 220)          # anel do campo de visão
    CURV_GROUND = (100, 200, 150, 70)
    CURV_GROUND_VERTICALS = (100, 150, 255, 60)
    CURV_CEILING = (200, 150, 100, 70)
    CURV_CEILING_VERTICALS = (200, 100, 100, 60)
    CURV_CUBE = (150, 100, 255, 180)
    CURV_VERTICAL = (90, 140, 255, 110)
    CURV_HORIZONTAL = (255, 90, 130, 110)
    CURV_DEPTH = (90, 210, 130, 110)
    CURV_VP_OUTLINE = (0, 0, 0, 255)
    CURV_LETTERBOX = (255, 255, 255, 120)
    CURV_ROTATION_ARM = (150, 100, 255, 140)
    CURV_PIVOT_OUTLINE = (0, 0, 0, 180)
    CURV_PIVOT = (100, 200, 255, 240)
    CURV_ARM_HANDLE = (255, 255, 255, 240)
    CURV_HOVER_VERTICAL = (56, 189, 248, 120)
    CURV_HOVER_HORIZONTAL = (248, 113, 113, 120)
    CURV_HOVER_DEPTH = (74, 222, 128, 120)
    CURV_HOVER_OTHER = (255, 125, 45, 100)

    # ── Lupa do conta-gotas ─────────────────────────────────────────────────
    LOUPE_SHADOW = (0, 0, 0, 80)
    LOUPE_BACKGROUND = (30, 30, 30, 255)
    LOUPE_RETICLE = (255, 255, 255, 240)
    LOUPE_RETICLE_OUTLINE = (0, 0, 0, 180)
    LOUPE_RING_OUTLINE = (255, 255, 255, 140)
    LOUPE_BADGE = (15, 23, 42, 220)
    LOUPE_BADGE_TEXT = (255, 255, 255, 255)

    # ── Seleção (formigas) e transformação ──────────────────────────────────
    ANTS_DARK = (0, 0, 0, 255)
    ANTS_LIGHT = (255, 255, 255, 255)
    TRANSFORM_BOX = (0, 150, 255, 230)
    TRANSFORM_HANDLE_OUTLINE = (0, 100, 200, 255)
    TRANSFORM_HANDLE = (255, 255, 255, 255)
    TRANSFORM_PIVOT = (255, 60, 60, 230)
    TRANSFORM_PIVOT_FILL = (255, 255, 255, 180)

    # ── Prévia de forma (padrão quando a ferramenta não tem cor) ────────────
    SHAPE_STROKE_DEFAULT = (147, 51, 234, 255)
    SHAPE_FILL_DEFAULT = (192, 132, 252, 180)
