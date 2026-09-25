"""Selection Tool Controller (Magic Wand, Rect, Ellipse, Lasso)."""

import logging
from typing import Optional, List
from PySide6 import QtCore, QtWidgets
from ui.core.engine.backend import EngineBackend
from ui.core.engine.registry import EngineRegistry
from ui.core.tool_settings import default_tool_settings
from ui.core.document.history import layer_transaction
from ui.core.document.manager import DocumentManager

logger = logging.getLogger(__name__)


class SelectionToolController:
    """Controlador de ferramentas de seleção e confinamento da máscara nativa C++."""

    def __init__(self, widget):
        self.widget = widget
        self.wand_settings = default_tool_settings("wand")
        self.geom_select_settings = default_tool_settings("rect_select")
        self.lasso_settings = default_tool_settings("lasso")
        self.drag_active: bool = False
        self.drag_start: QtCore.QPointF = QtCore.QPointF(0, 0)
        self.drag_current: QtCore.QPointF = QtCore.QPointF(0, 0)
        self.lasso_points: List[QtCore.QPointF] = []
        self.lasso_is_drawing: bool = False
        self.lasso_hover_pt: Optional[QtCore.QPointF] = None

        self.selection_dash_offset: float = 0.0
        self.selection_timer = QtCore.QTimer(widget)
        self.selection_timer.setInterval(60)
        self.selection_timer.timeout.connect(self._on_timer_tick)

    def _on_timer_tick(self):
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "has_selection") and backend.has_selection():
            self.selection_dash_offset = (self.selection_dash_offset + 1.0) % 16.0
            self.widget.update()
        else:
            self.selection_timer.stop()

    def do_magic_wand_select(self, screen_x: float, screen_y: float):
        backend = EngineRegistry.instance().get_backend()
        if not backend:
            return

        world_evt = self.widget.to_canvas(screen_x, screen_y, 1.0, 0.0)
        wx, wy = int(world_evt.x), int(world_evt.y)

        if wx < 0 or wx >= self.widget.canvas_w or wy < 0 or wy >= self.widget.canvas_h:
            return

        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if (modifiers & QtCore.Qt.ShiftModifier) and (modifiers & QtCore.Qt.AltModifier):
            mode = 3
        elif modifiers & QtCore.Qt.ShiftModifier:
            mode = 1
        elif modifiers & QtCore.Qt.AltModifier:
            mode = 2
        else:
            mode = self.wand_settings.get("mode", 0)

        tol = int(self.wand_settings.get("tolerance", 20))
        contig = bool(self.wand_settings.get("contiguous", True))
        exp = int(self.wand_settings.get("expand_px", 0))
        aa = bool(self.wand_settings.get("aa", True))
        sample_all = bool(self.wand_settings.get("sample_all", True))

        ok = False
        if hasattr(backend, "magic_wand_select"):
            ok = backend.magic_wand_select(
                seed_x=wx,
                seed_y=wy,
                tolerance=tol,
                contiguous=contig,
                expand_px=exp,
                anti_aliasing=aa,
                mode=mode,
                sample_all_layers=sample_all
            )

        if ok and backend.has_selection():
            if not self.selection_timer.isActive():
                self.selection_timer.start()
        else:
            self.selection_timer.stop()

        self.widget.update()

    def finish_geom_selection(self):
        backend = EngineRegistry.instance().get_backend()
        if not backend:
            return

        modifiers = QtWidgets.QApplication.keyboardModifiers()
        is_shift = bool(modifiers & QtCore.Qt.ShiftModifier)
        is_alt = bool(modifiers & QtCore.Qt.AltModifier)

        p1 = self.drag_start
        p2 = self.drag_current

        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()

        if is_shift:
            side = max(abs(dx), abs(dy))
            dx = side if dx >= 0 else -side
            dy = side if dy >= 0 else -side

        if is_alt:
            rx = abs(dx)
            ry = abs(dy)
            cx = p1.x()
            cy = p1.y()
            x = cx - rx
            y = cy - ry
            w = rx * 2.0
            h = ry * 2.0
        else:
            x = min(p1.x(), p1.x() + dx)
            y = min(p1.y(), p1.y() + dy)
            w = abs(dx)
            h = abs(dy)
            cx = x + w / 2.0
            cy = y + h / 2.0
            rx = w / 2.0
            ry = h / 2.0

        if w < 2 or h < 2:
            return

        cfg = self.geom_select_settings
        if (modifiers & QtCore.Qt.ShiftModifier) and (modifiers & QtCore.Qt.AltModifier):
            mode = 3
        elif modifiers & QtCore.Qt.ShiftModifier and not is_alt:
            mode = 1
        elif modifiers & QtCore.Qt.AltModifier and not is_shift:
            mode = 2
        else:
            mode = cfg.get("mode", 0)

        feather_px = int(cfg.get("feather_px", 0))
        aa = bool(cfg.get("aa", True))

        if self.widget.active_tool == "rect_select":
            if hasattr(backend, "select_rect"):
                backend.select_rect(int(x), int(y), int(w), int(h), mode=mode, feather_px=feather_px)
        elif self.widget.active_tool == "ellipse_select":
            if hasattr(backend, "select_ellipse"):
                backend.select_ellipse(int(cx), int(cy), int(rx), int(ry), mode=mode, anti_aliasing=aa, feather_px=feather_px)

        if hasattr(backend, "has_selection") and backend.has_selection():
            if not self.selection_timer.isActive():
                self.selection_timer.start()
        else:
            self.selection_timer.stop()

        self.widget.update()

    def finish_lasso_selection(self):
        backend = EngineRegistry.instance().get_backend()
        if not backend or len(self.lasso_points) < 3:
            self.lasso_points = []
            self.widget.update()
            return

        flat_pts = []
        for pt in self.lasso_points:
            flat_pts.append(int(pt.x()))
            flat_pts.append(int(pt.y()))

        self.lasso_points = []

        cfg = self.lasso_settings
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if (modifiers & QtCore.Qt.ShiftModifier) and (modifiers & QtCore.Qt.AltModifier):
            mode = 3
        elif modifiers & QtCore.Qt.ShiftModifier:
            mode = 1
        elif modifiers & QtCore.Qt.AltModifier:
            mode = 2
        else:
            mode = cfg.get("mode", 0)

        feather_px = int(cfg.get("feather_px", 0))
        aa = bool(cfg.get("aa", True))

        if hasattr(backend, "select_polygon"):
            backend.select_polygon(flat_pts, mode=mode, anti_aliasing=aa, feather_px=feather_px)

        if hasattr(backend, "has_selection") and backend.has_selection():
            if not self.selection_timer.isActive():
                self.selection_timer.start()
        else:
            self.selection_timer.stop()

        self.widget.update()

    def clear_selection(self) -> None:
        """Limpa a seleção ativa e interrompe o timer de marching ants."""
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "clear_selection"):
            backend.clear_selection()
        if self.selection_timer.isActive():
            self.selection_timer.stop()
        self.widget.update()

    def select_all(self) -> None:
        """Seleciona todo o canvas e inicia a animação de marching ants."""
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "select_all"):
            backend.select_all()
        if not self.selection_timer.isActive():
            self.selection_timer.start()
        self.widget.update()

    def invert_selection(self) -> None:
        """Inverte a seleção ativa e sincroniza o timer de animação."""
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "invert_selection"):
            backend.invert_selection()
        self._sync_marching_ants(backend)

    # ── Contrato de `layer_transaction` (modify_selection é uma transação) ──

    @property
    def layer_manager(self):
        """A transação é do documento ativo (a máscara de seleção é dele)."""
        doc = DocumentManager.instance().active_document()
        return doc.layer_manager if doc is not None else None

    def show_status(self, message: str) -> None:
        # Quem chama (menu Seleção) recebe False e avisa o usuário.
        logger.warning("Modificar seleção falhou: %s", message)

    @layer_transaction
    def modify_selection(self, mode: str, radius_px: int) -> bool:
        """Seleção -> Modificar: "expand", "contract" ou "feather" (raio em px).

        Dentro de uma transação de documento: o motor grava a máscara antes e
        depois, então Desfazer/Refazer voltam a seleção anterior.
        """
        backend: Optional[EngineBackend] = EngineRegistry.instance().get_backend()
        operations = {
            "expand": backend.expand_selection,
            "contract": backend.contract_selection,
            "feather": backend.feather_selection,
        } if backend else {}
        operation = operations.get(mode)
        ok = bool(operation and operation(int(radius_px)))
        self._sync_marching_ants(backend)
        return ok

    def _sync_marching_ants(self, backend) -> None:
        """Liga/desliga o marching ants conforme a seleção existe e repinta."""
        if backend and hasattr(backend, "has_selection") and backend.has_selection():
            if not self.selection_timer.isActive():
                self.selection_timer.start()
        elif self.selection_timer.isActive():
            self.selection_timer.stop()
        self.widget.update()

