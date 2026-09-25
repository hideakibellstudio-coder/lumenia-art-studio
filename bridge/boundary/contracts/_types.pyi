"""Typed boundary contract definitions for ALADYN native engine types."""

from enum import IntEnum
from typing import List, Optional, Sequence, Tuple

class Point2D:
    x: float
    y: float
    def __init__(self, x: float = 0.0, y: float = 0.0) -> None: ...
    def distance_to(self, other: Point2D) -> float: ...

class CurvePreset(IntEnum):
    Linear = 0
    Soft = 1
    Hard = 2
    S = 3
    Threshold = 4

class BezierCurve:
    def __init__(self, preset: CurvePreset = CurvePreset.Linear) -> None: ...
    def set_control_points(self, p1x: float, p1y: float, p2x: float, p2y: float) -> None: ...
    def set_preset(self, preset: CurvePreset) -> None: ...
    def set_power(self, power: float) -> None: ...
    def get_lut(self) -> List[float]: ...
    def set_lut(self, values: Sequence[float]) -> None: ...
    def invert(self) -> None: ...
    def sample(self, t: float) -> float: ...

class EngineType(IntEnum):
    Brush = 0
    Pencil = 1
    Inker = 2
    Eraser = 3
    Marker = 4
    Blur = 5
    Smudge = 6
    Watercolor = 7
    OilImpasto = 8

class DabBlendMode(IntEnum):
    Normal = 0
    Multiply = 1
    Additive = 2
    Erase = 3

class LayerBlendMode(IntEnum):
    Normal = 0
    Multiply = 1
    Screen = 2
    Overlay = 3
    Darken = 4
    Lighten = 5
    Erase = 6

class SelectionMode(IntEnum):
    New = 0
    Add = 1
    Subtract = 2
    Intersect = 3

class SymmetryMode(IntEnum):
    NoneMode = 0
    Mirror = 1
    DoubleMirror = 2
    Radial = 3
    Kaleidoscope = 4

class GuideType(IntEnum):
    NoneType = 0
    Straight = 1
    CurveRuler = 2
    Curvilinear = 3
    OnePoint = 4
    TwoPoint = 5
    ThreePoint = 6
    Isometric = 7

class ColorRGBA:
    r: int
    g: int
    b: int
    a: int
    def __init__(self, r: int = 0, g: int = 0, b: int = 0, a: int = 255) -> None: ...

class PointerEventType(IntEnum):
    Press = 0
    Move = 1
    Release = 2

class PointerEvent:
    type: PointerEventType
    position: Point2D
    pressure: float
    timestamp: float
    tilt_x: float
    tilt_y: float
    twist: float
    altitude: float
    azimuth: float
    def __init__(
        self,
        type: PointerEventType = PointerEventType.Move,
        position: Optional[Point2D] = None,
        pressure: float = 1.0,
        timestamp: float = 0.0,
        tilt_x: float = 0.0,
        tilt_y: float = 0.0,
        twist: float = 0.0,
    ) -> None: ...
    def compute_altitude_azimuth_from_tilt(self) -> None: ...

class DynamicStabilizer:
    def __init__(self, stabilization_percentage: float = 50.0) -> None: ...
    def set_stabilization_percentage(self, percentage: float) -> None: ...
    def get_stabilization_percentage(self) -> float: ...
    def reset(self) -> None: ...
    def reanchor_initial_position(self, new_initial_position: Point2D) -> None: ...
    def update(self, raw_position: Point2D, normalized_velocity: float) -> None: ...
    def flush(self, end_position: Point2D, steps: int) -> List[Point2D]: ...
    def get_taper_points(self, steps: int, max_distance: float) -> List[Point2D]: ...
    def get_stabilized_position(self) -> Point2D: ...
    def get_last_movement_delta(self) -> Point2D: ...

class BrushTip:
    angle: float
    aspect_ratio: float
    follow_stroke: bool
    jitter_size: float
    jitter_angle: float
    jitter_position: float
    jitter_hue: float
    jitter_saturation: float
    jitter_brightness: float
    use_twist_for_angle: bool
    tilt_to_angle: bool
    tilt_to_aspect: bool
    def __init__(self) -> None: ...

class PencilParams:
    graphite_hardness: float
    tilt_shading_enabled: bool
    def __init__(self) -> None: ...

class InkerParams:
    ink_flow_rate: float
    taper_smoothing: float
    def __init__(self) -> None: ...

class MarkerParams:
    solvent_wetness: float
    edge_darkening: float
    def __init__(self) -> None: ...

class BlurParams:
    blur_radius: float
    blur_strength: float
    def __init__(self) -> None: ...

class SmudgeParams:
    color_pickup: float
    mix_ratio: float
    smudge_stretch: float
    def __init__(self) -> None: ...

class WatercolorParams:
    water_level: float
    pigment_bleed: float
    fringe_intensity: float
    granulation: float
    def __init__(self) -> None: ...

class OilParams:
    impasto_depth: float
    bristle_grooves: float
    viscosity: float
    specular_brilliance: float
    wet_mix_factor: float
    paint_depletion: float
    def __init__(self) -> None: ...

class BrushProfile:
    def __init__(self, other: "BrushProfile | None" = None) -> None: ...
    engine_type: int
    brush_size: float
    min_size_percent: float
    opacity: float
    min_opacity_percent: float
    hardness: float
    blend_mode: int
    spacing_factor: float
    base_color: ColorRGBA
    pressure_size_enabled: bool
    pressure_flow_enabled: bool
    velocity_size_enabled: bool
    stroke_taper_enabled: bool
    scatter_count: int
    pressure_to_angle: float
    pressure_to_aspect: float
    pressure_size_curve: BezierCurve
    pressure_flow_curve: BezierCurve
    velocity_size_curve: BezierCurve
    tip: BrushTip
    time_spacing_enabled: bool
    dabs_per_second: float
    brush_grain_enabled: bool
    brush_grain_scale: float
    brush_grain_contrast: float
    brush_grain_invert: bool
    brush_texture_curve: BezierCurve
    pencil_params: PencilParams
    inker_params: InkerParams
    marker_params: MarkerParams
    blur_params: BlurParams
    smudge_params: SmudgeParams
    watercolor_params: WatercolorParams
    oil_params: OilParams

class CanvasTexture:
    background_color: ColorRGBA
    canvas_grain_enabled: bool
    canvas_grain_scale: float
    canvas_grain_contrast: float
    canvas_grain_invert: bool
    canvas_texture_curve: BezierCurve
    def __init__(self) -> None: ...
    def invalidate_lut(self) -> None: ...

class TelemetryData:
    pressure: float
    velocity: float
    output_flow: float

class RealTimeStrokeMetrics:
    last_segment_latency_us: float
    stroke_total_time_ms: float
    total_dabs_in_stroke: int
    total_dabs_per_second: int
    input_event_rate_hz: int
    time_kinematics_us: float
    time_interpolation_us: float
    time_raster_dab_us: float
    time_undo_record_us: float
    time_composite_us: float
    last_dabs_rendered: int
    last_dirty_width: int
    last_dirty_height: int
    last_dirty_area_px: int
    last_tiles_recorded: int
    last_tiles_composited: int
    active_tile_count: int
    dirty_tiles_last_stroke: int
    tile_grid_memory_mb: float
    undo_stack_memory_mb: float
    undo_steps_count: int
    raw_pressure: float
    dynamic_pressure: float
    stroke_velocity: float
    stabilizer_lag_px: float
    active_engine_id: int
    simd_active: bool
    def __init__(self) -> None: ...

class ViewportTransform:
    zoom: float
    pan_x: float
    pan_y: float
    rotation_deg: float
    def __init__(
        self,
        viewport_width: int,
        viewport_height: int,
        canvas_width: int,
        canvas_height: int,
    ) -> None: ...
    def set_viewport_size(self, width: int, height: int) -> None: ...
    def set_canvas_size(self, width: int, height: int) -> None: ...
    def set_camera(
        self,
        pan_x: float,
        pan_y: float,
        zoom: float,
        rotation_deg: float,
        flip_h: bool,
        flip_v: bool,
    ) -> None: ...
    def canvas_to_screen(self, cx: float, cy: float) -> Tuple[float, float]: ...
    def screen_to_canvas(self, sx: float, sy: float) -> Tuple[float, float]: ...
    def get_visible_canvas_bounds(self) -> Tuple[float, float, float, float]: ...
    def get_visible_tile_range(self) -> Tuple[int, int, int, int]: ...
    def is_tile_visible(self, tx: int, ty: int) -> bool: ...
