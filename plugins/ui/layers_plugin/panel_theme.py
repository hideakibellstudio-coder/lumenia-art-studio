"""
LayersPanelTheme — Aplicação de Temas e Ícones no Painel de Camadas
=====================================================================
Sincroniza paleta do ThemeManager com delegados, cabeçalho e botões do LayersPanel.
"""

from __future__ import annotations
from typing import Any
from ui.core.icons import get_icon
from ui.core.theme.manager import ThemeManager


def apply_layers_panel_theme(panel: Any) -> None:
    tm = ThemeManager.instance()
    
    colors = {
        "bg_panel": tm.get_color("bg_panel"),
        "bg_main": tm.get_color("bg_main"),
        "border": tm.get_color("border"),
        "ACCENT": tm.get_color("accent"),
        "text_main": tm.get_color("text_main"),
        "text_sec": tm.get_color("text_sec"),
        # Bug corrigido (panorama-consistencia-visual-tema-2026-09-18.md, Achado #1):
        # isto apontava para "bg_panel", fazendo o destaque de layer-filtro (delegate.py)
        # nunca aparecer diferenciado do fundo, em nenhum tema.
        "ACCENT_MUTED": tm.get_color("accent_muted"),
        # Chaves que faltavam (Achado #2): sem elas, os indicadores de "clipping mask" e
        # "alpha lock" do delegate caíam sempre no fallback hardcoded (#10b981/#f59e0b),
        # nunca de fato reagindo ao tema ativo.
        "SUCCESS": tm.get_color("success"),
        "WARNING": tm.get_color("warning"),
    }
    
    border = colors.get("border", "#374151")
    
    if hasattr(panel, 'v_divider'):
        panel.v_divider.setStyleSheet(f"background-color: {border}; border: none;")
    
    if hasattr(panel, 'header'):
        panel.header.on_theme_changed(colors)
        
    if hasattr(panel, 'paper_widget'):
        panel.paper_widget.update_theme(colors)
    
    panel.delegate.set_colors(colors)
    panel.view.setStyleSheet("""
        QTreeView, QTreeView::item, QTreeView::branch { background: transparent; border: none; outline: 0; }
        QTreeView::branch:has-children:!has-siblings:closed, QTreeView::branch:closed:has-children:has-siblings,
        QTreeView::branch:open:has-children:!has-siblings, QTreeView::branch:open:has-children:has-siblings { image: none; }
    """)
    panel.view.viewport().update()

    icon_color = colors.get("text_main", "#f3f4f6")
    for btn in panel.primary_box.buttons + panel.secondary_bar.buttons:
        icon_name = btn.property("icon_name")
        if icon_name:
            btn.setIcon(get_icon(icon_name, icon_color))
        btn.style().unpolish(btn)
        btn.style().polish(btn)

    bg_panel = colors.get("bg_panel", "#1f2937")
    panel.primary_box.setStyleSheet(f"""
        QWidget#PrimaryBox {{ background-color: {bg_panel}; border: 1px solid {border}; border-radius: 8px; }}
        QFrame[class="GridSeparator"] {{ background-color: {border}; max-height: 1px; border: none; }}
    """)
