"""Pixel characterization of the nine brush engines (S0.6).

These tests do not describe the *correct* behaviour. They pin the CURRENT one,
so that a change in an engine proves it altered only what it meant to alter.
Same role as `test_stroke_characterization.py` (one engine, stabilizer cells)
and `test_compositing_characterization.py` (blending and filters).

Until 2026-10-01 only the default engine had a pixel reference; no test painted
with Blur or Smudge, and the other six engines had "left ink" assertions only.
The nine `renderDab` implementations repeat the same selection / alpha lock /
clipping code, so any change to one of them (or to the shared core that will
replace the copies) must be checked against all nine.

Each cell is one engine x one variant:

  plain         stroke over three coloured bars on layer 0
  alpha_locked  the same, layer 0 alpha lock on
  selected      the same, a rectangular selection over the left half
  clipped       layer 1 (clipping mask over layer 0) carries the bars; the
                stroke goes on layer 1

and, added before the nine `renderDab` were rebuilt on a common core (S2.1), the
brush shapes the first four never reached (the engines had texture, ellipse and
hardness paths that no pin touched):

  textured      a bristle shape texture, brush grain and canvas grain (all procedural)
  elliptical    a flattened, rotated tip (aspect 0.45, angle 35) with pressure-to-aspect
  soft, hard    hardness 0.0 and 1.0 (the other cells use 0.6)
  multiply,     the dab blend modes (only the default engine reads them; the others
  additive      must keep ignoring them)
  engine_params every engine-specific parameter away from its default (graphite
                hardness, ink flow, solvent, blur radius, pickup, water, impasto...)
  textured_params  the two above together: grain-driven branches (watercolor
                granulation, oil bristle grooves) only run with both

The digest covers the composite and the active layer buffer. Delete
`tests/golden/engines_golden.json` to record everything again, only when the
pixel change is deliberate and you know what it is.
"""

from __future__ import annotations

import hashlib
import json
import pathlib

import pytest

native = pytest.importorskip(
    "aladyn_engine_native", reason="native module not built in this environment"
)

GOLDEN = pathlib.Path(__file__).parent / "golden" / "engines_golden.json"
WIDTH, HEIGHT = 128, 96

ENGINES = {
    "brush": native.EngineType.Brush,
    "pencil": native.EngineType.Pencil,
    "inker": native.EngineType.Inker,
    "eraser": native.EngineType.Eraser,
    "marker": native.EngineType.Marker,
    "blur": native.EngineType.Blur,
    "smudge": native.EngineType.Smudge,
    "watercolor": native.EngineType.Watercolor,
    "oil": native.EngineType.OilImpasto,
}
SCENE_VARIANTS = ("plain", "alpha_locked", "selected", "clipped")
BRUSH_VARIANTS = ("textured", "elliptical", "soft", "hard", "multiply", "additive", "engine_params", "textured_params")
VARIANTS = SCENE_VARIANTS + BRUSH_VARIANTS
CELLS = [(engine, variant) for engine in ENGINES for variant in VARIANTS]
# A stroke that changes nothing, on purpose: alpha lock protects exactly what
# the eraser changes.
NO_OP_BY_DESIGN = {("eraser", "alpha_locked")}

# The engines that do not read a brush variant, as measured when the variants were added: their
# cell equals the "plain" one. Recording them keeps a pin from pinning nothing, and a future
# engine that starts reading a setting has to update this table on purpose.
IGNORED_BY_DESIGN = {
    "textured": {"inker", "marker", "blur", "smudge", "oil"},
    "elliptical": {"blur"},
    "multiply": set(ENGINES) - {"brush"},
    "additive": set(ENGINES) - {"brush"},
    "engine_params": {"brush", "eraser"},
}

# Three horizontal bars (colour, y): content for Blur, Smudge and Eraser to act on.
BARS = (((220, 40, 40), 28), ((40, 80, 220), 48), ((230, 200, 40), 68))
# Diagonal stroke across the bars, with varying pressure.
SAMPLES = [(14.0 + i * 2.5, 12.0 + i * 1.85, 0.6 + 0.4 * ((i % 5) / 4.0)) for i in range(40)]
TESTED_COLOR = (30, 160, 60)


def _stroke(eng, points):
    """Explicit timestamps on every sample: without them the engine falls back
    to the clock and the stroke stops being reproducible."""
    x0, y0, p0 = points[0]
    eng.begin_stroke_raw(x0, y0, p0, 1.0)
    for i, (x, y, pressure) in enumerate(points[1:], start=1):
        eng.update_stroke_raw(x, y, pressure, 8.0 * (i + 1))
    eng.end_stroke_raw()


def _use_engine(eng, engine_type, color, size, opacity=1.0, hardness=0.6):
    eng.set_engine_type(int(engine_type))
    profile = eng.get_brush_profile()
    profile.brush_size = size
    profile.opacity = opacity
    profile.hardness = hardness
    profile.base_color = native.ColorRGBA(*color, 255)


def _texture_the_brush(eng):
    eng.set_shape_preset(2)  # dry bristles
    eng.set_brush_height_preset(3)  # noise grain
    profile = eng.get_brush_profile()
    profile.brush_grain_enabled = True
    profile.brush_grain_scale = 3.0
    profile.brush_grain_contrast = 1.4
    eng.set_canvas_height_preset(1)  # watercolor paper
    canvas_texture = eng.get_canvas_texture()
    canvas_texture.canvas_grain_enabled = True
    canvas_texture.canvas_grain_scale = 1.5
    canvas_texture.invalidate_lut()


def _move_engine_params(eng):
    profile = eng.get_brush_profile()
    profile.pencil_params.graphite_hardness = 0.85
    profile.pencil_params.tilt_shading_enabled = True
    profile.inker_params.ink_flow_rate = 0.6
    profile.inker_params.taper_smoothing = 0.8
    profile.marker_params.solvent_wetness = 0.9
    profile.marker_params.edge_darkening = 0.7
    profile.blur_params.blur_radius = 4
    profile.blur_params.blur_strength = 0.4
    profile.smudge_params.color_pickup = 0.4
    profile.smudge_params.mix_ratio = 0.8
    profile.smudge_params.smudge_stretch = 1.6
    profile.watercolor_params.water_level = 0.9
    profile.watercolor_params.pigment_bleed = 0.8
    profile.watercolor_params.fringe_intensity = 0.7
    profile.watercolor_params.granulation = 0.8
    profile.oil_params.impasto_depth = 0.9
    profile.oil_params.bristle_grooves = 0.8
    profile.oil_params.viscosity = 0.3
    profile.oil_params.specular_brilliance = 0.8


def _textured_with_params(eng):
    _texture_the_brush(eng)
    _move_engine_params(eng)


def _flatten_the_tip(eng):
    profile = eng.get_brush_profile()
    profile.tip.aspect_ratio = 0.45
    profile.tip.angle = 35.0
    profile.pressure_to_aspect = 0.3


def _set_hardness(value):
    def apply(eng):
        eng.get_brush_profile().hardness = value
    return apply


def _set_dab_blend(mode):
    def apply(eng):
        eng.get_brush_profile().blend_mode = mode
    return apply


# What each brush variant does to the profile after the engine is chosen.
BRUSH_SETUP = {
    "textured": _texture_the_brush,
    "elliptical": _flatten_the_tip,
    "soft": _set_hardness(0.0),
    "hard": _set_hardness(1.0),
    "multiply": _set_dab_blend(native.DabBlendMode.Multiply),
    "additive": _set_dab_blend(native.DabBlendMode.Additive),
    "engine_params": _move_engine_params,
    "textured_params": _textured_with_params,
}


def _paint_bars(eng, shift_x=0.0):
    for color, y in BARS:
        _use_engine(eng, native.EngineType.Inker, color, size=12.0)
        _stroke(eng, [(8.0 + shift_x + i * 5.0, float(y), 1.0) for i in range(22)])


def _digest(eng, layer_index):
    sha = hashlib.sha256()
    sha.update(bytes(eng.get_pixel_buffer()))
    sha.update(bytes(eng.get_layer_pixel_buffer(layer_index)))
    return sha.hexdigest()


def _scenario(engine, variant):
    """Run one cell. `engine=None` paints only the bars (the control)."""
    eng = native.PaintEngineFacade(WIDTH, HEIGHT)
    eng.set_render_options(low_latency=False, linear_gamma=False, deep_color=False)
    eng.get_stabilizer().set_stabilization_percentage(0.0)

    active = 0
    _paint_bars(eng)
    if variant == "clipped":
        active = eng.add_layer("clipped")
        eng.select_layer(active)
        _paint_bars(eng, shift_x=18.0)
        eng.set_layer_clipping_mask(active, True)
    elif variant == "alpha_locked":
        eng.set_layer_alpha_lock(active, True)
    elif variant == "selected":
        eng.select_rect(0, 0, WIDTH // 2, HEIGHT)

    if engine is not None:
        _use_engine(eng, ENGINES[engine], TESTED_COLOR, size=18.0)
        if variant in BRUSH_SETUP:
            BRUSH_SETUP[variant](eng)
        _stroke(eng, SAMPLES)
    return _digest(eng, active)


def _label(engine, variant):
    return f"{engine}__{variant}"


@pytest.fixture(scope="module")
def pins() -> dict:
    """Load the pins, recording any that are missing.

    Completing instead of failing matters: a new cell enters the matrix and is
    recorded from the current binary instead of being skipped silently.
    """
    recorded = {}
    if GOLDEN.exists():
        recorded = json.loads(GOLDEN.read_text(encoding="utf-8"))
    missing = {
        _label(*cell): _scenario(*cell) for cell in CELLS if _label(*cell) not in recorded
    }
    if missing:
        recorded.update(missing)
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(
            json.dumps(recorded, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return recorded


# -- 1. The pins -------------------------------------------------------------

@pytest.mark.parametrize("cell", CELLS, ids=lambda c: _label(*c))
def test_cell_did_not_change(pins, cell):
    label = _label(*cell)
    assert _scenario(*cell) == pins[label], (
        f"the pixels of {label} changed. If the change is deliberate, say what it "
        f"is and record the pin again; if not, the edit leaked into an engine "
        f"that should have stayed intact."
    )


# -- 2. Guards: without them every hash above could be noise or a no-op ------

@pytest.mark.parametrize("engine", list(ENGINES))
def test_scenario_is_deterministic(engine):
    assert _scenario(engine, "plain") == _scenario(engine, "plain"), (
        f"the same scripted stroke produced different pixels for {engine}"
    )


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("engine", list(ENGINES))
def test_every_engine_changes_the_canvas(engine, variant):
    """A characterization of a stroke that did nothing would characterize nothing."""
    changed = _scenario(engine, variant) != _scenario(None, variant)
    if (engine, variant) in NO_OP_BY_DESIGN:
        assert not changed, f"{engine} was expected to leave the {variant} canvas intact"
    else:
        assert changed, f"{engine} left the {variant} canvas exactly as the control"


def test_engines_are_distinguishable():
    """If two engines gave the same pixels, `set_engine_type` would not be
    reaching the engine, and the pins would not tell them apart."""
    digests = {engine: _scenario(engine, "plain") for engine in ENGINES}
    assert len(set(digests.values())) == len(ENGINES), (
        "two engines produced identical pixels: "
        + ", ".join(sorted(engine for engine in digests
                           if list(digests.values()).count(digests[engine]) > 1))
    )


@pytest.mark.parametrize("variant", BRUSH_VARIANTS)
@pytest.mark.parametrize("engine", list(ENGINES))
def test_brush_variants_reach_the_engines_that_read_them(engine, variant):
    """Each brush variant changes the pixels of the engines that read that setting, and only those."""
    changed = _scenario(engine, variant) != _scenario(engine, "plain")
    ignored = engine in IGNORED_BY_DESIGN.get(variant, set())
    assert changed != ignored, (
        f"{engine} {'ignored' if not changed else 'reacted to'} '{variant}'; "
        f"update IGNORED_BY_DESIGN if that is the new, intended behaviour"
    )
