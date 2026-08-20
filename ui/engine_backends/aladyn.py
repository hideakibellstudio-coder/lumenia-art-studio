"""
AladynBackend — Adaptador do ALADYN ENGINE (C++ PyBind11 / aladyn_engine_native)
================================================================================
Adaptador que implementa a interface `EngineBackend` da Lumenia UI e conversa
diretamente com a `PaintEngineFacade` do ALADYN ENGINE.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from PySide6.QtGui import QImage
from ui.core.engine.backend import EngineBackend, PointerEvent

logger = logging.getLogger(__name__)


class AladynBackend(EngineBackend):
    """Backend nativo que encapsula a PaintEngineFacade do ALADYN ENGINE."""

    name = "aladyn"

    def __init__(self) -> None:
        self._native: Any = None
        self._facade: Any = None
        self._width: int = 800
        self._height: int = 600
        self.last_telemetry: tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._action_stack: list[tuple[str, int]] = []
        self._redo_stack: list[tuple[str, int]] = []
        self._is_filling: bool = False

        try:
            import aladyn_engine_native
            self._native = aladyn_engine_native
            logger.info("[AladynBackend] Módulo nativo aladyn_engine_native carregado com sucesso.")
        except Exception as e:
            logger.info(
                f"[AladynBackend] aladyn_engine_native indisponível "
                f"({type(e).__name__}: {e}). Modo casca pura mantido."
            )
            self._native = None

    # ── Disponibilidade & ciclo de vida ──────────────────────────────────

    @property
    def available(self) -> bool:
        return self._native is not None

    def init_renderer(self, hwnd: int, width: int, height: int, canvas_w: int, canvas_h: int) -> None:
        if self._native is None:
            return
        try:
            self._width = max(1, canvas_w)
            self._height = max(1, canvas_h)
            self._facade = self._native.PaintEngineFacade(self._width, self._height)
            if hasattr(self._facade, "get_canvas_texture"):
                c_tex = self._facade.get_canvas_texture()
                if c_tex:
                    c_tex.canvas_grain_enabled = False
            logger.info(f"[AladynBackend] PaintEngineFacade inicializada com canvas {self._width}x{self._height}.")
        except Exception as e:
            logger.error(f"[AladynBackend] Falha ao inicializar PaintEngineFacade: {e}")
            self._facade = None

    def resize(self, width: int, height: int) -> None:
        if self._facade:
            self._width = max(1, width)
            self._height = max(1, height)
            self._facade.resize_canvas(self._width, self._height)

    def render(self, pan_x: float, pan_y: float, zoom: float, rotation_rad: float) -> None:
        # A renderização do ALADYN ENGINE ocorre diretamente via buffer de pixels RGBA em get_pixel_buffer()
        pass

    # ── Traço (stroke) ───────────────────────────────────────────────────

    def start_stroke(self, x: float, y: float, pressure: float) -> None:
        self._last_x = float(x)
        self._last_y = float(y)
        if self._facade and self._native:
            pt = self._native.Point2D(float(x), float(y))
            evt = self._native.PointerEvent(
                self._native.PointerEventType.Press, pt, float(pressure), time.time()
            )
            self._facade.begin_stroke(evt)

    def paint_stroke(self, x: float, y: float, pressure: float) -> None:
        self._last_x = float(x)
        self._last_y = float(y)
        if self._facade and self._native:
            pt = self._native.Point2D(float(x), float(y))
            evt = self._native.PointerEvent(
                self._native.PointerEventType.Move, pt, float(pressure), time.time()
            )
            telemetry = self._facade.update_stroke(evt)
            if telemetry:
                self.last_telemetry = (
                    float(telemetry.pressure),
                    float(telemetry.velocity),
                    float(telemetry.output_flow),
                )

    def end_stroke(self, x: float | None = None, y: float | None = None) -> None:
        if self._facade and self._native:
            rx = float(x) if x is not None else getattr(self, "_last_x", 0.0)
            ry = float(y) if y is not None else getattr(self, "_last_y", 0.0)
            pt = self._native.Point2D(rx, ry)
            evt = self._native.PointerEvent(
                self._native.PointerEventType.Release, pt, 0.0, time.time()
            )
            self._facade.end_stroke(evt)
            if not getattr(self, "_is_filling", False):
                self._action_stack.append(("stroke", 1))
                self._redo_stack.clear()

    def clear_canvas(self) -> None:
        if self._facade:
            self._facade.clear_canvas()

    def clear_layer(self, index: int) -> None:
        if self._facade:
            self._facade.clear_layer(index)

    def set_layer_alpha_lock(self, index: int, locked: bool) -> None:
        if self._facade:
            self._facade.set_layer_alpha_lock(index, locked)

    def set_layer_clipping_mask(self, index: int, clipped: bool) -> None:
        if self._facade:
            self._facade.set_layer_clipping_mask(index, clipped)

    def set_layer_blend_mode(self, index: int, mode_val) -> None:
        if self._facade and self._native:
            if isinstance(mode_val, int):
                bm_enum = self._native.LayerBlendMode(mode_val)
            elif isinstance(mode_val, str):
                blend_map = {
                    "Normal": 0, "Multiply": 1, "Multiplicação": 1,
                    "Screen": 2, "Divisão": 2, "Overlay": 3, "Sobreposição": 3,
                    "Darken": 4, "Escurecer": 4, "Lighten": 5, "Clarear": 5,
                    "Erase": 6, "Borracha": 6, "Pass-Through": 7, "Atravessar": 7, "PassThrough": 7,
                    "ColorDodge": 8, "Color Dodge": 8, "Subexposição (Dodge)": 8, "Subexposição": 8,
                    "ColorBurn": 9, "Color Burn": 9, "Superexposição (Burn)": 9, "Superexposição": 9,
                    "Difference": 10, "Diferença": 10,
                    "Exclusion": 11, "Exclusão": 11,
                    "Add": 12, "Adicionar (Add)": 12, "Adicionar": 12
                }
                bm_enum = self._native.LayerBlendMode(blend_map.get(mode_val, 0))
            else:
                bm_enum = mode_val
            self._facade.set_layer_blend_mode(index, bm_enum)

    def reorder_layer(self, from_index: int, to_index: int) -> bool:
        if self._facade:
            return self._facade.reorder_layer(from_index, to_index)
        return False

    def reorder_layers(self, new_order: list[int]) -> bool:
        if self._facade and hasattr(self._facade, "reorder_layers"):
            return self._facade.reorder_layers(new_order)
        return False

    def set_layer_parents(self, parent_indices: list[int]) -> bool:
        if self._facade and hasattr(self._facade, "set_layer_parents"):
            return self._facade.set_layer_parents(parent_indices)
        return False

    def add_group(self, name: str = "Novo Grupo") -> int:
        if self._facade and hasattr(self._facade, "add_group"):
            return self._facade.add_group(name)
        return -1

    def add_filter_layer(self, name: str, filter_type_id: int) -> int:
        if self._facade and hasattr(self._facade, "add_filter_layer"):
            return self._facade.add_filter_layer(name, filter_type_id)
        return -1

    def set_filter_params(self, index: int, params: list[float]) -> None:
        if self._facade and hasattr(self._facade, "set_filter_params"):
            self._facade.set_filter_params(index, [float(x) for x in params])

    def get_filter_params(self, index: int) -> list[float]:
        if self._facade and hasattr(self._facade, "get_filter_params"):
            return list(self._facade.get_filter_params(index))
        return []

    def get_filter_type(self, index: int) -> int:
        if self._facade and hasattr(self._facade, "get_filter_type"):
            return self._facade.get_filter_type(index)
        return -1

    def is_filter_layer(self, index: int) -> bool:
        if self._facade and hasattr(self._facade, "is_filter_layer"):
            return self._facade.is_filter_layer(index)
        return False

    def set_layer_name(self, index: int, name: str) -> None:
        if self._facade and hasattr(self._facade, "set_layer_name"):
            self._facade.set_layer_name(index, name)

    def is_group(self, index: int) -> bool:
        if self._facade and hasattr(self._facade, "is_group"):
            return self._facade.is_group(index)
        return False

    def set_group_pass_through(self, index: int, pass_through: bool) -> bool:
        if self._facade and hasattr(self._facade, "set_group_pass_through"):
            return self._facade.set_group_pass_through(index, pass_through)
        return False

    def duplicate_layer(self, index: int) -> int:
        if self._facade and hasattr(self._facade, "duplicate_layer"):
            return self._facade.duplicate_layer(index)
        return -1

    def flatten_group(self, index: int) -> bool:
        if self._facade and hasattr(self._facade, "flatten_group"):
            return self._facade.flatten_group(index)
        return False

    def merge_layer_down(self, index: int) -> bool:
        if self._facade:
            return self._facade.merge_layer_down(index)
        return False

    def set_background_color(self, r: int, g: int, b: int, a: int = 255) -> None:
        if self._facade and hasattr(self._facade, "set_background_color"):
            self._facade.set_background_color(int(r), int(g), int(b), int(a))

    def set_canvas_grain_enabled(self, enabled: bool) -> None:
        if self._facade and hasattr(self._facade, "get_canvas_texture"):
            c_tex = self._facade.get_canvas_texture()
            if c_tex:
                c_tex.canvas_grain_enabled = bool(enabled)

    def set_brush_grain_enabled(self, enabled: bool) -> None:
        if self._facade and hasattr(self._facade, "get_brush_profile"):
            prof = self._facade.get_brush_profile()
            if prof:
                prof.brush_grain_enabled = bool(enabled)

    # ── Pincel & Motor ───────────────────────────────────────────────────

    def set_engine_type(self, type_id: int) -> None:
        if self._facade:
            self._facade.set_engine_type(type_id)

    def undo(self) -> bool:
        if self._facade and hasattr(self._facade, "undo"):
            return self._facade.undo()
        return False

    def redo(self) -> bool:
        if self._facade and hasattr(self._facade, "redo"):
            return self._facade.redo()
        return False

    def get_active_engine_type(self) -> int:
        if self._facade:
            return self._facade.get_active_engine_type()
        return 0

    def set_brush_color(self, r: float, g: float, b: float) -> None:
        if self._facade and self._native:
            prof = self._facade.get_brush_profile()
            r_int = int(r * 255) if 0.0 <= r <= 1.0 else int(r)
            g_int = int(g * 255) if 0.0 <= g <= 1.0 else int(g)
            b_int = int(b * 255) if 0.0 <= b <= 1.0 else int(b)
            prof.base_color = self._native.ColorRGBA(r_int, g_int, b_int, 255)

    def set_brush_size(self, size: float) -> None:
        if self._facade:
            prof = self._facade.get_brush_profile()
            prof.brush_size = float(size)

    def set_brush_opacity(self, opacity: float) -> None:
        if self._facade:
            prof = self._facade.get_brush_profile()
            prof.opacity = float(opacity)

    def set_brush_spacing(self, spacing: float) -> None:
        if self._facade:
            prof = self._facade.get_brush_profile()
            prof.spacing_factor = float(spacing)

    def set_stabilizer_weight(self, weight: float) -> None:
        if self._facade:
            stab = self._facade.get_stabilizer()
            stab.set_stabilization_percentage(float(weight * 100.0 if weight <= 1.0 else weight))

    def set_brush_contrast(self, contrast: float) -> None:
        if self._facade:
            prof = self._facade.get_brush_profile()
            prof.hardness = float(contrast / 10.0 if contrast > 1.0 else contrast)

    def set_brush_pressure(self, pressure: float) -> None: pass
    def set_brush_invert_height(self, invert: bool) -> None: pass
    def set_pressure_curve_power(self, power: float) -> None: pass
    def set_min_density_active(self, active: bool) -> None: pass
    def set_min_density_value(self, value: float) -> None: pass

    # ── Texturas ─────────────────────────────────────────────────────────

    def set_shape_texture(self, pixels: bytes, width: int, height: int) -> None:
        if self._facade:
            self._facade.load_shape_texture(width, height, pixels)

    def set_heightmap_texture(self, pixels: bytes, width: int, height: int) -> None:
        if self._facade:
            self._facade.load_brush_height_texture(width, height, pixels)

    # ── Viewport / Câmera ────────────────────────────────────────────────

    def update_view(self, zoom: float, pan_x: float, pan_y: float, rotation: float) -> None:
        pass

    def to_canvas(self, screen_x: float, screen_y: float, pressure: float, timestamp: float) -> PointerEvent:
        return PointerEvent(x=screen_x, y=screen_y, pressure=pressure, timestamp=timestamp)

    # ── Buffer de Pixels & QImage ────────────────────────────────────────

    def get_pixel_buffer(self) -> Any:
        if self._facade:
            return self._facade.get_pixel_buffer()
        return None

    def get_display_pixel_buffer(self) -> Any:
        if self._facade:
            if hasattr(self._facade, "get_display_pixel_buffer"):
                return self._facade.get_display_pixel_buffer()
            return self._facade.get_pixel_buffer()
        return None

    def get_qimage(self) -> Optional[QImage]:
        if self._facade:
            memview = self.get_display_pixel_buffer()
            if memview:
                w, h = self._facade.get_width(), self._facade.get_height()
                return QImage(memview, w, h, w * 4, QImage.Format_RGBA8888)
        return None

    # ── Amostragem de Cores (Eyedropper) ─────────────────────────────────

    def pick_color_merged(self, x: int, y: int, sample_radius: int = 0) -> tuple:
        if self._facade and hasattr(self._facade, "pick_color_merged"):
            return self._facade.pick_color_merged(int(x), int(y), int(sample_radius))
        return (0, 0, 0, 0)

    def pick_color_layer(self, layer_index: int, x: int, y: int, sample_radius: int = 0) -> tuple:
        if self._facade and hasattr(self._facade, "pick_color_layer"):
            return self._facade.pick_color_layer(int(layer_index), int(x), int(y), int(sample_radius))
        return (0, 0, 0, 0)

    # ── Sistema de Seleção & Varinha Mágica ──────────────────────────────

    def magic_wand_select(
        self, seed_x: int, seed_y: int, tolerance: int = 20, contiguous: bool = True,
        expand_px: int = 0, anti_aliasing: bool = True, mode: int = 0,
        sample_all_layers: bool = True
    ) -> bool:
        if self._facade and hasattr(self._facade, "magic_wand_select"):
            return self._facade.magic_wand_select(
                int(seed_x), int(seed_y), int(tolerance), bool(contiguous),
                int(expand_px), bool(anti_aliasing), int(mode), bool(sample_all_layers)
            )
        return False

    def select_rect(self, x: int, y: int, w: int, h: int, mode: int = 0, feather_px: int = 0, corner_radius_px: int = 0) -> bool:
        if self._facade and hasattr(self._facade, "select_rect"):
            return self._facade.select_rect(int(x), int(y), int(w), int(h), int(mode), int(feather_px), int(corner_radius_px))
        return False

    def select_ellipse(self, cx: int, cy: int, rx: int, ry: int, mode: int = 0, anti_aliasing: bool = True, feather_px: int = 0) -> bool:
        if self._facade and hasattr(self._facade, "select_ellipse"):
            return self._facade.select_ellipse(int(cx), int(cy), int(rx), int(ry), int(mode), bool(anti_aliasing), int(feather_px))
        return False

    def select_polygon(self, flat_points: list[int], mode: int = 0, anti_aliasing: bool = True, feather_px: int = 0) -> bool:
        if self._facade and hasattr(self._facade, "select_polygon"):
            return self._facade.select_polygon([int(p) for p in flat_points], int(mode), bool(anti_aliasing), int(feather_px))
        return False

    def clear_selection(self) -> None:
        if self._facade and hasattr(self._facade, "clear_selection"):
            self._facade.clear_selection()

    def invert_selection(self) -> None:
        if self._facade and hasattr(self._facade, "invert_selection"):
            self._facade.invert_selection()

    def select_all(self) -> None:
        if self._facade and hasattr(self._facade, "select_all"):
            self._facade.select_all()

    def has_selection(self) -> bool:
        if self._facade and hasattr(self._facade, "has_selection"):
            return self._facade.has_selection()
        return False

    def delete_selection_on_active_layer(self) -> bool:
        if self._facade and hasattr(self._facade, "delete_selection_on_active_layer"):
            return self._facade.delete_selection_on_active_layer()
        return False

    def fill_selection_on_active_layer(self, fill_color: QtGui.QColor) -> bool:
        if self._facade and self._native and hasattr(self._facade, "fill_selection_on_active_layer"):
            c = self._native.ColorRGBA(int(fill_color.red()), int(fill_color.green()), int(fill_color.blue()), int(fill_color.alpha()))
            return self._facade.fill_selection_on_active_layer(c)
        return False

    def get_selection_bounds(self) -> tuple[int, int, int, int]:
        if self._facade and hasattr(self._facade, "get_selection_bounds"):
            b = self._facade.get_selection_bounds()
            if len(b) >= 4:
                return (b[0], b[1], b[2], b[3])
        return (0, 0, 0, 0)

    def get_selection_contour_segments(self) -> list[int]:
        if self._facade and hasattr(self._facade, "get_selection_contour_segments"):
            return self._facade.get_selection_contour_segments()
        return []

    def get_selection_contour_loops(self) -> list[list[int]]:
        if self._facade and hasattr(self._facade, "get_selection_contour_loops"):
            return self._facade.get_selection_contour_loops()
        return []

    def get_selection_mask_qimage(self) -> Optional[QImage]:
        if self._facade and hasattr(self._facade, "get_selection_mask_buffer"):
            memview = self._facade.get_selection_mask_buffer()
            if memview:
                w, h = self._facade.get_width(), self._facade.get_height()
                return QImage(memview, w, h, w, QImage.Format_Grayscale8)
        return None

    # ── Ferramenta de Transformação Livre (Transform Tool) ──────────────────

    def begin_transform(self) -> bool:
        if self._facade and hasattr(self._facade, "begin_transform"):
            return self._facade.begin_transform()
        return False

    def is_transform_active(self) -> bool:
        if self._facade and hasattr(self._facade, "is_transform_active"):
            return self._facade.is_transform_active()
        return False

    def get_transform_source_bounds(self) -> tuple[float, float, float, float]:
        if self._facade and hasattr(self._facade, "get_transform_source_bounds"):
            b = self._facade.get_transform_source_bounds()
            if len(b) >= 4:
                return (b[0], b[1], b[2], b[3])
        return (0.0, 0.0, 0.0, 0.0)

    def get_transform_pivot(self) -> tuple[float, float]:
        if self._facade and hasattr(self._facade, "get_transform_pivot"):
            p = self._facade.get_transform_pivot()
            if len(p) >= 2:
                return (p[0], p[1])
        return (0.0, 0.0)

    def commit_transform(
        self,
        dx: float, dy: float,
        scale_x: float, scale_y: float,
        rotation_deg: float,
        pivot_x: float, pivot_y: float,
        flip_h: bool = False,
        flip_v: bool = False,
        interp_mode: int = 2
    ) -> bool:
        if self._facade and hasattr(self._facade, "commit_transform"):
            return self._facade.commit_transform(
                float(dx), float(dy),
                float(scale_x), float(scale_y),
                float(rotation_deg),
                float(pivot_x), float(pivot_y),
                bool(flip_h), bool(flip_v),
                int(interp_mode)
            )
        return False

    def cancel_transform(self) -> bool:
        if self._facade and hasattr(self._facade, "cancel_transform"):
            return self._facade.cancel_transform()
        return False

    def flip_active_layer(self, horizontal: bool) -> bool:
        if self._facade and hasattr(self._facade, "flip_active_layer"):
            return self._facade.flip_active_layer(bool(horizontal))
        return False

    def rotate_active_layer_90(self, clockwise: bool) -> bool:
        if self._facade and hasattr(self._facade, "rotate_active_layer_90"):
            return self._facade.rotate_active_layer_90(bool(clockwise))
        return False

    def get_transform_source_qimage(self) -> Optional[QImage]:
        if self._facade and hasattr(self._facade, "get_transform_source_buffer"):
            memview = self._facade.get_transform_source_buffer()
            if memview:
                sz = self._facade.get_transform_source_buffer_size()
                if sz[0] > 0 and sz[1] > 0:
                    return QImage(memview, sz[0], sz[1], sz[0] * 4, QImage.Format_RGBA8888)
        return None

    # ── Gerenciamento de Perfis de Cor (Color Profiles) ───────────────────

    def set_color_profile(self, profile_id: int) -> None:
        self._color_profile_id = int(profile_id)
        if self._facade and hasattr(self._facade, "set_color_profile"):
            self._facade.set_color_profile(int(profile_id))

    def get_color_profile(self) -> int:
        if self._facade and hasattr(self._facade, "get_color_profile"):
            return self._facade.get_color_profile()
        return getattr(self, "_color_profile_id", 0)

    def get_color_profile_name(self, profile_id: int) -> str:
        profiles = self.get_available_color_profiles()
        for p in profiles:
            if p.get("id") == int(profile_id):
                return p.get("name", "Padrão (sRGB)")
        return "Padrão (sRGB)"

    def get_available_color_profiles(self) -> list[dict]:
        if self._native and hasattr(self._native, "get_available_color_profiles"):
            return self._native.get_available_color_profiles()
        return [
            # 1. Digital (RGB)
            {
                "id": 0,
                "name": "Padrão (sRGB)",
                "category": "Digital (RGB)",
                "description": "Espaço de cor universal padrão para web, monitores convencionais e dispositivos móveis.",
                "gamut": "sRGB IEC61966-2.1",
                "whitepoint": "D65 (6500K)",
                "gamma": "2.2"
            },
            {
                "id": 1,
                "name": "Display P3 (Wide Gamut)",
                "category": "Digital (RGB)",
                "description": "Gamut cinematográfico e telas modernas (Apple Retina, monitores HDR). 25% mais cores que sRGB.",
                "gamut": "DCI-P3 D65",
                "whitepoint": "D65 (6500K)",
                "gamma": "sRGB Transfer"
            },
            {
                "id": 2,
                "name": "Adobe RGB (1998)",
                "category": "Digital (RGB)",
                "description": "Excelente amplitude em tons verdes e cianos, ideal para fotografia profissional e preparação para gráfica.",
                "gamut": "Adobe RGB 1998",
                "whitepoint": "D65 (6500K)",
                "gamma": "2.2"
            },
            {
                "id": 3,
                "name": "Rec. 2020 (UHD TV)",
                "category": "Digital (RGB)",
                "description": "Gamut ultra-amplo para masterização de vídeo 4K/8K HDR e arte digital de próxima geração.",
                "gamut": "BT.2020",
                "whitepoint": "D65 (6500K)",
                "gamma": "ITU-R BT.2020"
            },

            # 2. Impressão (CMYK Pro)
            {
                "id": 4,
                "name": "U.S. Web Coated (SWOP) v2",
                "category": "Impressão (CMYK)",
                "description": "Padrão norte-americano e brasileiro para impressão comercial rotativa em papel couché.",
                "gamut": "SWOP v2 (CMYK)",
                "whitepoint": "D50 (5000K)",
                "gamma": "Press Tone Value"
            },
            {
                "id": 5,
                "name": "ISO Coated v2 (ECI / FOGRA39)",
                "category": "Impressão (CMYK)",
                "description": "Referência oficial europeia para offset plano em papel brilhante/fosco de alta qualidade.",
                "gamut": "FOGRA39 (CMYK)",
                "whitepoint": "D50 (5000K)",
                "gamma": "ISO 12647-2"
            },
            {
                "id": 6,
                "name": "GRACoL 2006 (Coated 1v2)",
                "category": "Impressão (CMYK)",
                "description": "Especificação premium para gráficas de ponta e provas contratuais com G7 Calibration.",
                "gamut": "GRACoL 2006",
                "whitepoint": "D50 (5000K)",
                "gamma": "G7 Curves"
            },
            {
                "id": 7,
                "name": "Japan Color 2001 Coated",
                "category": "Impressão (CMYK)",
                "description": "Padrão industrial da indústria gráfica japonesa para mangás, artbooks e ilustrações.",
                "gamut": "Japan Color 2001",
                "whitepoint": "D50 (5000K)",
                "gamma": "Japan Print Std"
            },

            # 3. Acessibilidade & Prova de Daltonismo
            {
                "id": 8,
                "name": "Protanopia (Sem Vermelho)",
                "category": "Acessibilidade",
                "description": "Simulação em tempo real para avaliar legibilidade de ilustrações sem cones L (vermelho).",
                "gamut": "Simulação Protanopia",
                "whitepoint": "D65",
                "gamma": "Linear Match"
            },
            {
                "id": 9,
                "name": "Deuteranopia (Sem Verde)",
                "category": "Acessibilidade",
                "description": "Simulação do tipo mais comum de daltonismo (ausência de cones M - verde).",
                "gamut": "Simulação Deuteranopia",
                "whitepoint": "D65",
                "gamma": "Linear Match"
            },
            {
                "id": 10,
                "name": "Tritanopia (Sem Azul/Amarelo)",
                "category": "Acessibilidade",
                "description": "Simulação de percepção visual com ausência de cones S (azul).",
                "gamut": "Simulação Tritanopia",
                "whitepoint": "D65",
                "gamma": "Linear Match"
            },
            {
                "id": 11,
                "name": "Acromatopsia (Monocromático)",
                "category": "Acessibilidade",
                "description": "Prova rigorosa de luminância, hierarquia tonal e contraste puro em preto e branco.",
                "gamut": "Luminância Pura (Y)",
                "whitepoint": "D65",
                "gamma": "Luminance Rec.709"
            },

            # 4. Pipeline do Motor & VFX
            {
                "id": 12,
                "name": "Linear sRGB (Physical Blending)",
                "category": "Motor Físico",
                "description": "Cálculo de mistura física fotométrica sem distorção gama, ideal para iluminação e sombras reais.",
                "gamut": "sRGB Primaries",
                "whitepoint": "D65",
                "gamma": "1.0 (Linear Puro)"
            },
            {
                "id": 13,
                "name": "ACEScg (Academy Color Encoding)",
                "category": "Motor Físico",
                "description": "Padrão da indústria de cinema e efeitos visuais (VFX) com suporte a iluminação com alcance dinâmico infinito.",
                "gamut": "AP1 Primaries",
                "whitepoint": "D60 (ACES)",
                "gamma": "1.0 (Linear Float)"
            }
        ]

    def fill_area(
        self,
        seed_x: int,
        seed_y: int,
        fill_color: QtGui.QColor,
        tolerance: int = 20,
        contiguous: bool = True,
        expand_px: int = 1,
        gap_closing_px: int = 0,
        aa: bool = True,
        sample_all: bool = True,
    ) -> bool:
        """Executa Flood Fill ultra-rápido (<1ms) diretamente no motor nativo C++."""
        if not self._facade or not self._native:
            return False

        if not hasattr(self._facade, "flood_fill"):
            return False

        native_color = self._native.ColorRGBA(
            int(fill_color.red()),
            int(fill_color.green()),
            int(fill_color.blue()),
            int(fill_color.alpha()),
        )

        return self._facade.flood_fill(
            int(seed_x),
            int(seed_y),
            native_color,
            int(tolerance),
            bool(contiguous),
            int(expand_px),
            int(gap_closing_px),
            bool(aa),
            bool(sample_all),
        )

    def dispatch(self, command: Any) -> None:
        pass
