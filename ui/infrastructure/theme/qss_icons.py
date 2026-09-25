"""qss_icons — ícones do catálogo central em PNG, para o QSS (`image: url(...)`).

Saiu do `ThemeManager` em 2026-09-24 (o manager chegava perto da parede dos
450 linhas); o comportamento é o mesmo.
"""
import logging
import os

from PySide6 import QtCore, QtGui, QtSvg

logger = logging.getLogger(__name__)


def render_icon_png(icon_key: str, color: str, size: int = 24) -> str:
    """Renderiza um ícone do catálogo central (mesmo pipeline de ui.infrastructure.icons.get_icon)
    para um arquivo PNG em cache, para ser referenciado via QSS `image: url(...)`.

    Necessário porque QSS não resolve `currentColor` em SVGs carregados via url() -- só o
    pipeline Python de ui.infrastructure.icons faz essa substituição manualmente antes de renderizar.
    Um SVG cru com fill/stroke="currentColor" carregado direto pelo QSS (como acontecia com
    os botões close/float do QDockWidget) renderiza com a cor padrão do próprio arquivo (ou
    nem renderiza, dependendo da disponibilidade do plugin de imagem SVG do Qt) -- nunca
    reage ao tema. Ver claude/panorama-consistencia-visual-tema-2026-09-18.md (Achado #6).

    A lógica de renderização espelha ui.infrastructure.icons.svg_to_icon() -- duplicada aqui de
    propósito (não importada) para não criar um import de ui.infrastructure.icons em nível de módulo
    neste arquivo, já que ui/core/__init__.py importa ThemeManager como primeiro passo da
    inicialização do pacote `ui.core` (risco de import parcialmente circular).
    """
    import hashlib
    from ui.infrastructure.icons.svg_catalog import SVG_ICONS, ALIASES
    from ui.infrastructure.config import get_default_config_path

    name = str(icon_key).replace("-", "_").replace(" ", "_")
    resolved_name = ALIASES.get(name, name)
    svg_template = SVG_ICONS.get(resolved_name)
    if not svg_template:
        return ""

    cache_dir = os.path.join(os.path.dirname(get_default_config_path()), "theme_icon_cache")
    try:
        os.makedirs(cache_dir, exist_ok=True)
    except OSError as e:
        logger.warning(f"Tema: Falha ao criar cache de ícones de tema: {e}")
        return ""

    cache_key = hashlib.md5(f"{resolved_name}:{color}:{size}".encode("utf-8")).hexdigest()[:16]
    cache_path = os.path.join(cache_dir, f"{cache_key}.png").replace("\\", "/")

    if not os.path.exists(cache_path):
        svg_xml = svg_template.replace("currentColor", color)
        byte_array = QtCore.QByteArray(svg_xml.encode("utf-8"))
        renderer = QtSvg.QSvgRenderer(byte_array)
        pixmap = QtGui.QPixmap(QtCore.QSize(size, size))
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        if not pixmap.save(cache_path, "PNG"):
            logger.warning(f"Tema: Falha ao salvar PNG de ícone em cache: {cache_path}")
            return ""

    return cache_path
