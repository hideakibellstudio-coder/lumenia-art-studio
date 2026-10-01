"""Canvas Overlays Renderer (Selection Marching Ants, Transform Gizmo, Shape Preview, Loupe HUD)."""

from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.engine.backend_protocols import CoreLifecycleProtocol, SelectionTransformProtocol
from ui.infrastructure.theme.overlay_palette import OverlayPalette
from ui.plugins.system.workspace_core.workspace.canvas.tools.transform_tool_controller import TransformToolController
from ui.plugins.system.workspace_core.workspace.canvas.tools.selection_tool_controller import SelectionToolController

class OverlayRenderer:
    """Renderizador de Overlays e Elementos de Interface Visual sobre o Canvas."""

    @staticmethod
    def render_color_loupe(painter: QtGui.QPainter, screen_pos: QtCore.QPointF, widget, backend: Optional[CoreLifecycleProtocol], cur_color: QtGui.QColor, old_color: QtGui.QColor):
        cx = screen_pos.x()
        cy = screen_pos.y() - 55.0

        r_outer = 48.0
        r_inner = 35.0

        cx = max(r_outer + 8, min(float(widget.width()) - r_outer - 8, cx))
        cy = max(r_outer + 8, min(float(widget.height()) - r_outer - 35, cy))

        # 1. Sombra suave
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(*OverlayPalette.LOUPE_SHADOW))
        painter.drawEllipse(QtCore.QPointF(cx, cy + 4), r_outer + 2, r_outer + 2)

        # 2. Miniatura ampliada do canvas sob a retícula (Zoom 4x)
        painter.save()
        clip_path = QtGui.QPainterPath()
        clip_path.addEllipse(QtCore.QPointF(cx, cy), r_inner, r_inner)
        painter.setClipPath(clip_path)
        painter.fillRect(QtCore.QRectF(cx - r_inner, cy - r_inner, r_inner * 2, r_inner * 2), QtGui.QColor(*OverlayPalette.LOUPE_BACKGROUND))

        if backend:
            world_evt = widget.to_canvas(screen_pos.x(), screen_pos.y(), 1.0, 0.0)
            wx, wy = int(world_evt.x), int(world_evt.y)

            src_size = 18
            src_rect = QtCore.QRect(wx - src_size // 2, wy - src_size // 2, src_size, src_size)
            target_rect = QtCore.QRectF(cx - r_inner, cy - r_inner, r_inner * 2, r_inner * 2)

            # Só os 18x18 pixels sob a mira, não o canvas inteiro (eram 34 ms em 4K a cada movimento
            # do mouse). Fora do canvas a lupa fica no fundo, como a cópia recortada ficava transparente.
            visible = src_rect.intersected(QtCore.QRect(0, 0, widget.canvas_w, widget.canvas_h))
            display = backend.get_display_image(1.0, visible) if not visible.isEmpty() else None
            if display is not None and not display.image.isNull():
                magnification = target_rect.width() / src_size
                destination = QtCore.QRectF(
                    target_rect.x() + (visible.x() - src_rect.x()) * magnification,
                    target_rect.y() + (visible.y() - src_rect.y()) * magnification,
                    visible.width() * magnification, visible.height() * magnification)
                painter.drawImage(destination, display.image, display.source_rect(visible))

        # 3. Retículo de Mira Central
        painter.setPen(QtGui.QPen(QtGui.QColor(*OverlayPalette.LOUPE_RETICLE), 1.5))
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRect(QtCore.QRectF(cx - 3, cy - 3, 6, 6))
        painter.setPen(QtGui.QPen(QtGui.QColor(*OverlayPalette.LOUPE_RETICLE_OUTLINE), 1.0))
        painter.drawRect(QtCore.QRectF(cx - 4, cy - 4, 8, 8))
        painter.restore()

        # 4. Anel Bipartido de Cores
        ring_thickness = r_outer - r_inner
        ring_rect = QtCore.QRectF(
            cx - r_outer + ring_thickness / 2, cy - r_outer + ring_thickness / 2,
            (r_outer - ring_thickness / 2) * 2, (r_outer - ring_thickness / 2) * 2
        )

        pen_cur = QtGui.QPen(cur_color, ring_thickness)
        pen_cur.setCapStyle(QtCore.Qt.FlatCap)
        painter.setPen(pen_cur)
        painter.drawArc(ring_rect, 0 * 16, 180 * 16)

        pen_old = QtGui.QPen(old_color, ring_thickness)
        pen_old.setCapStyle(QtCore.Qt.FlatCap)
        painter.setPen(pen_old)
        painter.drawArc(ring_rect, 180 * 16, 180 * 16)

        painter.setPen(QtGui.QPen(QtGui.QColor(*OverlayPalette.LOUPE_RING_OUTLINE), 1.0))
        painter.drawEllipse(QtCore.QPointF(cx, cy), r_outer, r_outer)
        painter.drawEllipse(QtCore.QPointF(cx, cy), r_inner, r_inner)
        painter.drawLine(QtCore.QPointF(cx - r_outer, cy), QtCore.QPointF(cx - r_inner, cy))
        painter.drawLine(QtCore.QPointF(cx + r_inner, cy), QtCore.QPointF(cx + r_outer, cy))

        # 5. Badge HEX
        badge_w, badge_h = 74.0, 18.0
        badge_rect = QtCore.QRectF(cx - badge_w / 2, cy + r_outer + 4, badge_w, badge_h)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(*OverlayPalette.LOUPE_BADGE))
        painter.drawRoundedRect(badge_rect, 4, 4)

        painter.setPen(QtGui.QColor(*OverlayPalette.LOUPE_BADGE_TEXT))
        fnt = QtGui.QFont("Segoe UI", 8, QtGui.QFont.Bold)
        painter.setFont(fnt)
        painter.drawText(badge_rect, QtCore.Qt.AlignCenter, cur_color.name().upper())

    @staticmethod
    def render_selection_overlay(painter: QtGui.QPainter, backend: SelectionTransformProtocol, zoom: float, dash_offset: float, canvas_w: int, canvas_h: int):
        bounds = backend.get_selection_bounds()
        bx, by, bw, bh = bounds
        if bw <= 0 or bh <= 0:
            return

        loops = backend.get_selection_contour_loops()

        path = QtGui.QPainterPath()
        if loops:
            for loop in loops:
                if len(loop) >= 4:
                    poly = QtGui.QPolygonF([
                        QtCore.QPointF(loop[i], loop[i+1])
                        for i in range(0, len(loop), 2)
                    ])
                    path.addPolygon(poly)
        else:
            path.addRect(QtCore.QRectF(bx, by, bw, bh))

        painter.save()
        zoom_factor = max(0.01, zoom)
        line_w = 1.0 / zoom_factor

        pen_black = QtGui.QPen(QtGui.QColor(*OverlayPalette.ANTS_DARK), line_w)
        pen_black.setStyle(QtCore.Qt.CustomDashLine)
        pen_black.setDashPattern([4, 4])
        pen_black.setDashOffset(dash_offset)

        pen_white = QtGui.QPen(QtGui.QColor(*OverlayPalette.ANTS_LIGHT), line_w)
        pen_white.setStyle(QtCore.Qt.CustomDashLine)
        pen_white.setDashPattern([4, 4])
        pen_white.setDashOffset(dash_offset + 4.0)

        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(pen_black)
        painter.drawPath(path)
        painter.setPen(pen_white)
        painter.drawPath(path)
        painter.restore()

    @staticmethod
    def render_selection_drag_preview(painter: QtGui.QPainter, widget, zoom: float):
        painter.save()
        zoom_factor = max(0.01, zoom)
        line_w = 1.0 / zoom_factor

        pen_black = QtGui.QPen(QtGui.QColor(*OverlayPalette.ANTS_DARK), line_w)
        pen_black.setStyle(QtCore.Qt.CustomDashLine)
        pen_black.setDashPattern([4, 4])

        pen_white = QtGui.QPen(QtGui.QColor(*OverlayPalette.ANTS_LIGHT), line_w)
        pen_white.setStyle(QtCore.Qt.CustomDashLine)
        pen_white.setDashPattern([4, 4])
        pen_white.setDashOffset(4.0)

        painter.setBrush(QtCore.Qt.NoBrush)

        modifiers = QtWidgets.QApplication.keyboardModifiers()
        is_shift = bool(modifiers & QtCore.Qt.ShiftModifier)
        is_alt = bool(modifiers & QtCore.Qt.AltModifier)

        ctrl: SelectionToolController = widget.selection_ctrl
        active_tool = widget.active_tool

        if active_tool in ("rect_select", "ellipse_select"):
            drag_active = ctrl.drag_active
            if drag_active:
                p1 = ctrl.drag_start
                p2 = ctrl.drag_current
                dx = p2.x() - p1.x()
                dy = p2.y() - p1.y()

                if is_shift:
                    side = max(abs(dx), abs(dy))
                    dx = side if dx >= 0 else -side
                    dy = side if dy >= 0 else -side

                if is_alt:
                    rx = abs(dx)
                    ry = abs(dy)
                    rect = QtCore.QRectF(p1.x() - rx, p1.y() - ry, rx * 2.0, ry * 2.0)
                else:
                    rect = QtCore.QRectF(min(p1.x(), p1.x() + dx), min(p1.y(), p1.y() + dy), abs(dx), abs(dy))

                if active_tool == "rect_select":
                    painter.setPen(pen_black)
                    painter.drawRect(rect)
                    painter.setPen(pen_white)
                    painter.drawRect(rect)
                elif active_tool == "ellipse_select":
                    painter.setPen(pen_black)
                    painter.drawEllipse(rect)
                    painter.setPen(pen_white)
                    painter.drawEllipse(rect)

        elif active_tool == "lasso":
            pts = ctrl.lasso_points
            if len(pts) >= 1:
                path = QtGui.QPainterPath()
                path.moveTo(pts[0])
                for p in pts[1:]:
                    path.lineTo(p)

                lasso_cfg = ctrl.lasso_settings
                hover_pt = ctrl.lasso_hover_pt
                if lasso_cfg.get("lasso_type") == "polygonal" and hover_pt:
                    path.lineTo(hover_pt)

                painter.setPen(pen_black)
                painter.drawPath(path)
                painter.setPen(pen_white)
                painter.drawPath(path)

        painter.restore()

    @staticmethod
    def render_transform_overlay(painter: QtGui.QPainter, transform_ctrl: TransformToolController, zoom: float):
        if not transform_ctrl.active or not transform_ctrl.source_qimage:
            return
        t_mat = transform_ctrl.get_transform_matrix()
        src_rect = transform_ctrl.source_rect
        pv = transform_ctrl.pivot

        painter.save()
        painter.setTransform(t_mat, combine=True)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
        painter.drawImage(src_rect, transform_ctrl.source_qimage)
        painter.restore()

        painter.save()
        zf = max(0.01, zoom)
        lw, hs = 1.2 / zf, 8.0 / zf
        painter.setPen(QtGui.QPen(QtGui.QColor(*OverlayPalette.TRANSFORM_BOX), lw))
        painter.setBrush(QtCore.Qt.NoBrush)

        c_tl, c_tr = t_mat.map(src_rect.topLeft()), t_mat.map(src_rect.topRight())
        c_br, c_bl = t_mat.map(src_rect.bottomRight()), t_mat.map(src_rect.bottomLeft())
        painter.drawPolygon(QtGui.QPolygonF([c_tl, c_tr, c_br, c_bl]))

        c_tc = t_mat.map(QtCore.QPointF(src_rect.center().x(), src_rect.top()))
        c_bc = t_mat.map(QtCore.QPointF(src_rect.center().x(), src_rect.bottom()))
        c_ml = t_mat.map(QtCore.QPointF(src_rect.left(), src_rect.center().y()))
        c_mr = t_mat.map(QtCore.QPointF(src_rect.right(), src_rect.center().y()))

        painter.setPen(QtGui.QPen(QtGui.QColor(*OverlayPalette.TRANSFORM_HANDLE_OUTLINE), lw))
        painter.setBrush(QtGui.QBrush(QtGui.QColor(*OverlayPalette.TRANSFORM_HANDLE)))
        for pt in (c_tl, c_tr, c_br, c_bl, c_tc, c_bc, c_ml, c_mr):
            painter.drawRect(QtCore.QRectF(pt.x() - hs/2, pt.y() - hs/2, hs, hs))

        if transform_ctrl.quad is not None:  # Distorcer: sem pivô nem rotação
            painter.restore()
            return
        pvm = t_mat.map(pv)
        pr = 7.0 / zf
        painter.setPen(QtGui.QPen(QtGui.QColor(*OverlayPalette.TRANSFORM_PIVOT), lw * 1.5))
        painter.setBrush(QtGui.QBrush(QtGui.QColor(*OverlayPalette.TRANSFORM_PIVOT_FILL)))
        painter.drawEllipse(QtCore.QRectF(pvm.x() - pr, pvm.y() - pr, pr * 2.0, pr * 2.0))
        painter.drawLine(QtCore.QPointF(pvm.x() - pr - 2, pvm.y()), QtCore.QPointF(pvm.x() + pr + 2, pvm.y()))
        painter.drawLine(QtCore.QPointF(pvm.x(), pvm.y() - pr - 2), QtCore.QPointF(pvm.x(), pvm.y() + pr + 2))
        painter.restore()

    @staticmethod
    def render_shape_drag_preview(painter: QtGui.QPainter, shape_ctrl):
        path = shape_ctrl.calculate_path()
        if not path:
            return
        cfg = shape_ctrl.settings
        dm = cfg.get("draw_mode", "both")
        sw = float(cfg.get("stroke_width", 4))
        sc = QtGui.QColor(cfg.get("stroke_color", QtGui.QColor(*OverlayPalette.SHAPE_STROKE_DEFAULT)))
        fc = QtGui.QColor(cfg.get("fill_color", QtGui.QColor(*OverlayPalette.SHAPE_FILL_DEFAULT)))

        painter.save()
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setPen(QtGui.QPen(sc, sw, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin) if dm in ("both", "stroke") else QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QBrush(fc) if dm in ("both", "fill") else QtCore.Qt.NoBrush)

        if isinstance(path, QtGui.QPainterPath): painter.drawPath(path)
        elif isinstance(path, QtCore.QLineF): painter.drawLine(path)
        elif isinstance(path, QtCore.QRectF): painter.drawRect(path)
        painter.restore()
