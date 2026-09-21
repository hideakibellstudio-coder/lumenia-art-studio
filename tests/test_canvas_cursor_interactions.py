"""
Testes de Regressão e Contrato para o Sistema de Cursor do Canvas (ARCcC v2)
=============================================================================
Valida o comportamento dos cursores de viewport, renderizadores de ferramentas,
feedback tátil de pan/zoom e sincronização reativa do raio de pincel.
"""

import pytest
from PySide6 import QtWidgets, QtCore, QtGui

from plugins.system.workspace_core.workspace.canvas.renderers.tool_cursor_renderer import ToolCursorRenderer
from plugins.system.workspace_core.workspace.canvas.viewport.cursor_controller import CanvasCursorController
from plugins.system.workspace_core.workspace.canvas.viewport.input_router import CanvasInputRouter
from plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget
from ui.core.icon_svg_catalog import ALIASES
from ui.core.icons import get_icon


@pytest.fixture(scope="module")
def qapp():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


def test_tool_cursor_renderer_hotspots_and_icons(qapp):
    """Verifica resolução de cursores customizados SVG, catálogo e hotspots."""
    assert ALIASES.get("eyedropper") == "eyedrop"

    # Tanto 'eyedrop' quanto 'eyedropper' devem gerar cursor válido sem fallback nulo
    cur_eyedrop = ToolCursorRenderer.create_custom_cursor("eyedrop")
    assert cur_eyedrop is not None
    assert cur_eyedrop.shape() == QtCore.Qt.CursorShape.BitmapCursor

    cur_eyedropper = ToolCursorRenderer.create_custom_cursor("eyedropper")
    assert cur_eyedropper is not None
    assert cur_eyedropper.shape() == QtCore.Qt.CursorShape.BitmapCursor

    for tool in ("bucket", "wand", "transform"):
        cursor = ToolCursorRenderer.create_custom_cursor(tool)
        assert cursor is not None
        assert cursor.shape() == QtCore.Qt.CursorShape.BitmapCursor


def test_tool_cursor_renderer_precision_chevron(qapp):
    """Verifica geração vetorial e cache do chevron de precisão nativo."""
    chevron = ToolCursorRenderer.create_precision_chevron_cursor(dpr=1.0)
    assert chevron is not None
    assert chevron.shape() == QtCore.Qt.CursorShape.BitmapCursor
    assert chevron.hotSpot() == QtCore.QPoint(0, 0)

    # Cache determinístico por DPR
    chevron_2x = ToolCursorRenderer.create_precision_chevron_cursor(dpr=2.0)
    assert chevron_2x is not None
    assert chevron_2x.shape() == QtCore.Qt.CursorShape.BitmapCursor


def test_canvas_cursor_controller_tool_shapes(qapp):
    """Verifica formas de cursor atribuídas para cada ferramenta ativa quando dentro e fora da viewport."""
    widget = QtWidgets.QWidget()
    widget.active_tool = "brush"
    widget.canvas_w = 800
    widget.canvas_h = 600
    controller = CanvasCursorController(widget)

    # Fora da viewport: deve ser SEMPRE ArrowCursor
    controller.cursor_in_viewport = False
    controller.update_cursor_shape()
    assert widget.cursor().shape() == QtCore.Qt.CursorShape.ArrowCursor

    # Dentro da viewport: ferramentas especializadas ativas em toda a área
    controller.cursor_in_viewport = True

    # Ferramentas com chevron de precisão (BitmapCursor por padrão)
    for tool in ("brush", "eraser", "smudge"):
        widget.active_tool = tool
        controller.update_cursor_shape()
        assert widget.cursor().shape() == QtCore.Qt.CursorShape.BitmapCursor

    # Suporte ao modo BlankCursor configurável
    controller.cursor_settings["mode"] = "blank"
    controller.update_cursor_shape()
    assert widget.cursor().shape() == QtCore.Qt.CursorShape.BlankCursor

    # Modo de sistema: deve usar ArrowCursor
    controller.cursor_settings["mode"] = "system"
    controller.update_cursor_shape()
    assert widget.cursor().shape() == QtCore.Qt.CursorShape.ArrowCursor
    controller.cursor_settings["mode"] = "ring_and_dot"

    # Permanece especializado mesmo no fundo neutro fora do documento (viewport-wide)
    controller._is_over_canvas = False
    controller.update_cursor_shape()
    assert widget.cursor().shape() == QtCore.Qt.CursorShape.BitmapCursor

    # Formas vetoriais e seleções: CrossCursor
    for tool in ("lasso", "rect_select", "ellipse_select", "shapes", "shape_rectangle", "shape_circle"):
        widget.active_tool = tool
        controller.update_cursor_shape()
        assert widget.cursor().shape() == QtCore.Qt.CursorShape.CrossCursor

    # Tipografia: IBeamCursor
    widget.active_tool = "text"
    controller.update_cursor_shape()
    assert widget.cursor().shape() == QtCore.Qt.CursorShape.IBeamCursor

    # Custom SVG tools
    for tool in ("eyedrop", "eyedropper", "bucket", "wand", "transform"):
        widget.active_tool = tool
        controller.update_cursor_shape()
        assert widget.cursor().shape() == QtCore.Qt.CursorShape.BitmapCursor

    # Ferramenta não mapeada: ArrowCursor
    widget.active_tool = "unknown_tool_xyz"
    controller.update_cursor_shape()
    assert widget.cursor().shape() == QtCore.Qt.CursorShape.ArrowCursor


def test_canvas_cursor_controller_smudge_dirty_rects(qapp):
    """Verifica que smudge gera dirty rects para re-renderização do anel."""
    widget = QtWidgets.QWidget()
    widget.active_tool = "smudge"
    widget.current_brush_radius = 25.0
    widget.zoom = 1.0
    widget.canvas_w = 800
    widget.canvas_h = 600
    widget._get_canvas_transform = lambda: QtGui.QTransform()

    controller = CanvasCursorController(widget)
    # Movendo o cursor dentro da área do canvas
    dirty = controller.handle_move(QtCore.QPointF(100, 100), brush_radius=25.0, zoom=1.0, is_drawing=False)
    assert dirty is not None
    assert not dirty.isEmpty()


def test_render_widget_brush_size_reactive_radius(qapp):
    """Verifica que RenderWidget.brush_size reage síncronamente atualizando _cached_brush_radius."""
    rw = RenderWidget()
    rw.brush_size = 40.0
    assert rw.brush_size == 40.0
    assert rw._cached_brush_radius == 20.0
    assert rw.current_brush_radius == 20.0

    rw.brush_size = 150.0
    assert rw.brush_size == 150.0
    assert rw._cached_brush_radius == 75.0
    assert rw.current_brush_radius == 75.0

    # Normalização de valor mínimo
    rw.brush_size = -10.0
    assert rw.brush_size == 0.5
    assert rw._cached_brush_radius == 0.25


def test_input_router_pan_and_zoom_cursor_feedback(qapp):
    """Verifica que Pan e Zoom Drag ativam ClosedHandCursor e SizeVerCursor e restauram ao soltar."""
    rw = RenderWidget()
    rw.active_tool = "brush"
    rw.cursor_ctrl.cursor_in_viewport = True
    rw.cursor_ctrl._is_over_canvas = True
    rw.cursor_ctrl.update_cursor_shape()
    assert rw.cursor().shape() == QtCore.Qt.CursorShape.BitmapCursor

    router = CanvasInputRouter(rw)

    # Inicia Pan via MiddleButton
    router.handle_pointer_press(
        QtCore.QPointF(100, 100),
        QtCore.Qt.MouseButton.MiddleButton,
        pressure=1.0,
        modifiers=QtCore.Qt.KeyboardModifier.NoModifier,
    )
    assert rw.is_panning is True
    assert rw.cursor().shape() == QtCore.Qt.CursorShape.ClosedHandCursor

    # Solta Pan
    router.handle_pointer_release(
        QtCore.QPointF(120, 120),
        QtCore.Qt.MouseButton.MiddleButton,
        modifiers=QtCore.Qt.KeyboardModifier.NoModifier,
    )
    assert rw.is_panning is False
    assert rw.cursor().shape() == QtCore.Qt.CursorShape.BitmapCursor

    # Inicia Zoom Drag via Alt + RightButton
    router.handle_pointer_press(
        QtCore.QPointF(100, 100),
        QtCore.Qt.MouseButton.RightButton,
        pressure=1.0,
        modifiers=QtCore.Qt.KeyboardModifier.AltModifier,
    )
    assert rw.is_zoom_dragging is True
    assert rw.cursor().shape() == QtCore.Qt.CursorShape.SizeVerCursor

    # Solta Zoom Drag
    router.handle_pointer_release(
        QtCore.QPointF(100, 150),
        QtCore.Qt.MouseButton.RightButton,
        modifiers=QtCore.Qt.KeyboardModifier.NoModifier,
    )
    assert rw.is_zoom_dragging is False
    assert rw.cursor().shape() == QtCore.Qt.CursorShape.BitmapCursor


def test_tool_cursor_renderer_eraser_dashed_and_smudge(qapp):
    """Verifica renderização visual de anéis específicos para borracha (tracejado) e smudge."""
    img = QtGui.QImage(100, 100, QtGui.QImage.Format_ARGB32_Premultiplied)
    img.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(img)
    try:
        # Borracha (tool_id="eraser") -> deve desenhar sem erro com estilo tracejado
        ToolCursorRenderer.render_cursor(p, 50, 50, 20.0, 1.0, tool_id="eraser")

        # Borrador (tool_id="smudge") -> deve desenhar sem erro com anel especializado
        ToolCursorRenderer.render_cursor(p, 50, 50, 20.0, 1.0, tool_id="smudge")

        # Micro-pincel (raio < 3.0) -> ponto central preservado
        ToolCursorRenderer.render_cursor(p, 50, 50, 1.0, 1.0, tool_id="brush")
    finally:
        p.end()


def test_space_key_pan_navigation(qapp):
    """Valida ciclo completo de navegação com Barra de Espaço + Clique Esquerdo do mouse (panning estilo padrão da indústria)."""
    rw = RenderWidget()
    rw.resize(800, 600)
    rw.canvas_w = 800
    rw.canvas_h = 600
    rw.active_tool = "brush"
    rw.cursor_ctrl.handle_enter(QtGui.QEnterEvent(QtCore.QPointF(100, 100), QtCore.QPointF(100, 100), QtCore.QPointF(100, 100)))

    router = rw.input_router

    # 1. Estado inicial: cursor de precisão
    assert rw.is_space_held is False
    assert rw.is_panning is False
    assert rw.cursor().shape() == QtCore.Qt.CursorShape.BitmapCursor

    # 2. Pressiona tecla Espaço -> Ativa cursor de mão aberta (OpenHandCursor)
    press_space = QtGui.QKeyEvent(QtCore.QEvent.Type.KeyPress, QtCore.Qt.Key.Key_Space, QtCore.Qt.KeyboardModifier.NoModifier)
    consumed = router.handle_key_press(press_space)
    assert consumed is True
    assert rw.is_space_held is True
    assert rw.is_panning is False
    assert rw.cursor().shape() == QtCore.Qt.CursorShape.OpenHandCursor

    # 3. Pressiona botão esquerdo do mouse com Espaço pressionado -> Inicia Pan com mão fechada (ClosedHandCursor)
    initial_pan_x, initial_pan_y = rw.pan_x, rw.pan_y
    router.handle_pointer_press(
        QtCore.QPointF(200, 200),
        QtCore.Qt.MouseButton.LeftButton,
        pressure=1.0,
        modifiers=QtCore.Qt.KeyboardModifier.NoModifier,
    )
    assert rw.is_panning is True
    assert rw.cursor().shape() == QtCore.Qt.CursorShape.ClosedHandCursor
    # Não deve ter iniciado traço de pincel!
    assert rw.drawing is False

    # 4. Move o mouse -> desloca câmera/pan
    router.handle_pointer_move(
        QtCore.QPointF(250, 280),
        pressure=1.0,
        modifiers=QtCore.Qt.KeyboardModifier.NoModifier,
    )
    assert rw.pan_x == initial_pan_x + 50
    assert rw.pan_y == initial_pan_y + 80

    # 5. Solta botão esquerdo mas mantém Espaço -> Volta para mão aberta
    router.handle_pointer_release(
        QtCore.QPointF(250, 280),
        QtCore.Qt.MouseButton.LeftButton,
        modifiers=QtCore.Qt.KeyboardModifier.NoModifier,
    )
    assert rw.is_panning is False
    assert rw.cursor().shape() == QtCore.Qt.CursorShape.OpenHandCursor

    # 6. Solta tecla Espaço -> Restaura cursor da ferramenta ativa
    release_space = QtGui.QKeyEvent(QtCore.QEvent.Type.KeyRelease, QtCore.Qt.Key.Key_Space, QtCore.Qt.KeyboardModifier.NoModifier)
    consumed = router.handle_key_release(release_space)
    assert consumed is True
    assert rw.is_space_held is False
    assert rw.cursor().shape() == QtCore.Qt.CursorShape.BitmapCursor

    # 7. Cenário: soltar Espaço DURANTE o arrasto mantém pan até soltar o mouse
    router.handle_key_press(press_space)
    router.handle_pointer_press(
        QtCore.QPointF(100, 100),
        QtCore.Qt.MouseButton.LeftButton,
        pressure=1.0,
        modifiers=QtCore.Qt.KeyboardModifier.NoModifier,
    )
    assert rw.is_panning is True
    router.handle_key_release(release_space)  # Solta espaço enquanto ainda arrasta
    assert rw.is_space_held is False
    assert rw.is_panning is True  # Pan continua ativo!

    router.handle_pointer_release(
        QtCore.QPointF(120, 120),
        QtCore.Qt.MouseButton.LeftButton,
        modifiers=QtCore.Qt.KeyboardModifier.NoModifier,
    )
    assert rw.is_panning is False
    assert rw.cursor().shape() == QtCore.Qt.CursorShape.BitmapCursor

    # 8. Focus out limpa estado de espaço
    router.handle_key_press(press_space)
    assert rw.is_space_held is True
    router.handle_focus_out()
    assert rw.is_space_held is False
    assert rw.cursor().shape() == QtCore.Qt.CursorShape.BitmapCursor
