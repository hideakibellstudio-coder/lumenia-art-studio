"""Calibração global da pressão da caneta: o que a mesa entrega vira o que o motor lê.

A sessão gravada com a caneta do dono (tests/fixtures/pen_session_real.jsonl.gz, Windows Ink,
59,94 Hz) tem pressão de desenho livre com mediana 0,12 e p95 0,28. Sem curva global, o Lápis
HB deixava 74% do trajeto sem tinta, o Nanquim G-Pen 53% e o Pincel Redondo 9%.

Quatro coisas são medidas aqui:
  1. a conta da curva (zona morta, pressão total, gama) e que valor malformado nunca vira NaN;
  2. o motor a aplica nos DOIS caminhos de traço (raw e PointerEvent): uma mesa que só chega a
     0,35 calibrada em 0,35 desenha igual a uma mesa que chega a 1,0 sem calibração;
  3. a configuração é lida com defesa (texto, NaN, faixa) e o assistente sugere o p95;
  4. a sonda de produto: com a sugestão do assistente, o desenho livre real deixa no máximo 10%
     do trajeto sem tinta nos três pincéis de arte (tolerância de 3 px: a linha pintada anda
     alguns pixels fora do caminho bruto nas curvas rápidas).
"""

from __future__ import annotations

import gzip
import json
import math
import pathlib
from collections import defaultdict

import numpy as np
import pytest

from ui.core.state.pen_calibration import PenCalibration, suggest_from_pressures

native = pytest.importorskip(
    "aladyn_engine_native", reason="módulo nativo não compilado neste ambiente"
)

SESSION = pathlib.Path(__file__).parent / "fixtures" / "pen_session_real.jsonl.gz"
FREE_DRAWING_STEP = 8
MAX_PATH_WITHOUT_INK = 0.10


# ── 1. A conta ──────────────────────────────────────────────────────────────

def test_default_calibration_is_the_identity():
    curve = native.PaintEngineFacade(16, 16).get_pressure_calibration()
    assert curve.is_identity()
    assert [curve.apply(p) for p in (0.0, 0.3, 1.0)] == [0.0, 0.3, 1.0]


@pytest.mark.parametrize(
    "floor,ceiling,gamma,raw,expected",
    [
        (0.0, 0.35, 1.0, 0.35, 1.0),    # a pressão que ele alcança conta como total
        (0.0, 0.35, 1.0, 0.175, 0.5),
        (0.0, 0.35, 1.0, 0.9, 1.0),     # acima do teto prende em 1
        (0.1, 1.0, 1.0, 0.1, 0.0),      # zona morta
        (0.1, 1.0, 1.0, 0.55, 0.5),
        (0.0, 1.0, 0.5, 0.25, 0.5),     # gama < 1 levanta o leve
        (0.0, 1.0, 2.0, 0.5, 0.25),     # gama > 1 achata
    ],
)
def test_the_curve_maps_raw_pressure(floor, ceiling, gamma, raw, expected):
    curve = native.PressureCalibration()
    curve.floor, curve.ceiling, curve.gamma = floor, ceiling, gamma
    assert curve.apply(raw) == pytest.approx(expected, abs=1e-9)


@pytest.mark.parametrize("floor,ceiling,gamma", [(0.9, 0.2, 1.0), (0.5, 0.5, 1.0), (-1.0, 5.0, 0.0), (0.0, 1.0, 99.0)])
def test_a_malformed_curve_never_produces_nan(floor, ceiling, gamma):
    curve = native.PressureCalibration()
    curve.floor, curve.ceiling, curve.gamma = floor, ceiling, gamma
    values = [curve.apply(p / 10.0) for p in range(11)]
    assert all(0.0 <= v <= 1.0 and not math.isnan(v) for v in values)
    assert values == sorted(values), "a curva tem que ser monótona"


# ── 2. O motor aplica nos dois caminhos ─────────────────────────────────────

WAVE = [(12.0 + i * 3.0, 30.0 + 10.0 * math.sin(i / 5.0), 0.15 + 0.85 * abs(math.sin(i / 7.0))) for i in range(40)]


def _paint(path: str, ceiling: float, scale: float) -> np.ndarray:
    """O mesmo desenho; a pressão entregue pela mesa é `scale` vezes a pretendida."""
    engine = native.PaintEngineFacade(140, 60)
    engine.set_render_options(low_latency=False, linear_gamma=False, deep_color=False)
    engine.get_stabilizer().set_stabilization_percentage(0.0)
    engine.get_brush_profile().brush_size = 8.0
    engine.get_pressure_calibration().ceiling = ceiling
    x0, y0, p0 = WAVE[0]
    if path == "raw":
        engine.begin_stroke_raw(x0, y0, p0 * scale, 1.0)
        for i, (x, y, p) in enumerate(WAVE[1:], 1):
            engine.update_stroke_raw(x, y, p * scale, 1.0 + 0.008 * i)
        engine.end_stroke_raw()
    else:
        event = lambda kind, x, y, p, t: native.PointerEvent(kind, native.Point2D(x, y), p, t)
        engine.begin_stroke(event(native.PointerEventType.Press, x0, y0, p0 * scale, 1.0))
        for i, (x, y, p) in enumerate(WAVE[1:], 1):
            engine.update_stroke(event(native.PointerEventType.Move, x, y, p * scale, 1.0 + 0.008 * i))
        engine.end_stroke(event(native.PointerEventType.Release, WAVE[-1][0], WAVE[-1][1], 0.0, 1.4))
    return np.frombuffer(bytes(engine.get_pixel_buffer()), dtype=np.uint8).astype(int)


@pytest.mark.parametrize("path", ["raw", "facade"])
def test_a_calibrated_weak_pen_draws_like_a_full_range_pen(path):
    reference = _paint(path, ceiling=1.0, scale=1.0)
    calibrated = _paint(path, ceiling=0.35, scale=0.35)
    uncalibrated = _paint(path, ceiling=1.0, scale=0.35)
    assert np.abs(reference - calibrated).max() <= 1, "a calibração não devolveu o desenho da mesa de faixa cheia"
    assert np.abs(reference - uncalibrated).max() > 10, "sem calibração a mesa fraca deveria desenhar diferente (teste sem força)"


# ── 3. Configuração e assistente ────────────────────────────────────────────

def test_the_stored_setting_survives_garbage():
    assert PenCalibration.from_config(None).is_identity
    assert PenCalibration.from_config({"ceiling": "abc"}).is_identity
    assert PenCalibration.from_config({"ceiling": float("nan")}).is_identity
    kept = PenCalibration.from_config({"floor": 0.9, "ceiling": 0.2, "gamma": 50})
    assert kept.floor <= 0.5 and kept.ceiling >= kept.floor + 0.05 and kept.gamma <= 3.0
    assert PenCalibration.from_config(PenCalibration(0.05, 0.4, 0.8).to_config()) == PenCalibration(0.05, 0.4, 0.8)


def test_the_assistant_needs_enough_strokes_and_leaves_a_full_range_pen_alone():
    assert suggest_from_pressures([0.2] * 10) is None
    assert suggest_from_pressures([0.95] * 200).is_identity
    suggestion = suggest_from_pressures([0.05 + 0.25 * i / 199 for i in range(200)])
    assert suggestion.ceiling == pytest.approx(0.29, abs=0.01) and suggestion.floor == 0.0 and suggestion.gamma == 1.0


# ── 4. A sonda de produto: a sessão real ────────────────────────────────────

@pytest.fixture(scope="module")
def session():
    lines = [json.loads(line) for line in gzip.open(SESSION, "rt", encoding="utf-8")]
    events = [e for e in lines[1:] if e.get("tipo") == "evento" and e["ponta"] == "caneta"]
    strokes = defaultdict(list)
    for e in events:
        strokes[(e["passo"], e["traco"])].append(e)
    return strokes


class _PresetTarget:
    """O que `apply_brush_preset_dict` pede ao backend, aplicado direto na facade."""

    def __init__(self, facade):
        self._facade = facade

    def set_engine_type(self, value): self._facade.set_engine_type(value)
    def set_shape_preset(self, value): self._facade.set_shape_preset(value)
    def set_brush_height_preset(self, value): self._facade.set_brush_height_preset(value)
    def set_stabilizer_weight(self, value): self._facade.get_stabilizer().set_stabilization_percentage(100.0 * value)


def _preset(category_id: str, label_fragment: str) -> dict:
    from ui.plugins.panels.brush_plugin.presets_data import BRUSH_CATEGORIES

    category = next(c for c in BRUSH_CATEGORIES if c["id"] == category_id)
    preset = next(p for p in category["presets"] if label_fragment.lower() in p["label"].lower())
    return {**preset, "engine_type": int(category["engine_type"])}


def _path_without_ink(session, category_id, label_fragment, color, calibration) -> float:
    from ui.infrastructure.bridge_client.aladyn_brush_profiles import apply_brush_preset_dict

    strokes = {k: v for k, v in session.items() if k[0] == FREE_DRAWING_STEP and len(v) >= 3}
    xs = [e["x"] for s in strokes.values() for e in s]
    ys = [e["y"] for s in strokes.values() for e in s]
    x0, y0 = min(xs) - 40, min(ys) - 40
    width, height = int(max(xs) + 40 - x0), int(max(ys) + 40 - y0)

    engine = native.PaintEngineFacade(width, height)
    engine.set_render_options(low_latency=False, linear_gamma=False, deep_color=False)
    engine.set_background_color(255, 255, 255, 255)
    data = _preset(category_id, label_fragment)
    apply_brush_preset_dict(_PresetTarget(engine), engine, native, {k: v for k, v in data.items() if k != "label"})
    engine.get_brush_profile().base_color = native.ColorRGBA(*color, 255)
    curve = engine.get_pressure_calibration()
    curve.floor, curve.ceiling, curve.gamma = calibration.floor, calibration.ceiling, calibration.gamma

    path = []
    for key in sorted(strokes):
        stroke = strokes[key]
        first = stroke[0]
        engine.begin_stroke_raw(first["x"] - x0, first["y"] - y0, max(0.02, first["p"]), first["ts"] / 1000.0, first["tx"], first["ty"], 0.0)
        for e in stroke[1:]:
            engine.update_stroke_raw(e["x"] - x0, e["y"] - y0, max(0.02, e["p"]), e["ts"] / 1000.0, e["tx"], e["ty"], 0.0)
        engine.end_stroke_raw()
        path += [(e["x"] - x0, e["y"] - y0) for e in stroke]

    rgb = np.frombuffer(bytes(engine.get_pixel_buffer()), dtype=np.uint8).reshape(height, width, 4)[:, :, :3]
    dark = 1.0 - rgb.astype(float).mean(axis=2) / 255.0
    padded = np.pad(dark, 3)
    near = np.max([padded[dy:dy + height, dx:dx + width] for dy in range(7) for dx in range(7)], axis=0)
    along = np.array([near[int(min(height - 1, max(0, y))), int(min(width - 1, max(0, x)))] for x, y in path])
    return float((along < 0.05).mean())


ART_BRUSHES = [
    ("pencil", "hb", (25, 25, 35), "pencil_hb"),
    ("brush", "redondo", (25, 25, 35), "round_brush"),
    ("inker", "g-pen", (15, 15, 20), "g_pen"),
]


@pytest.mark.parametrize("category,label,color", [b[:3] for b in ART_BRUSHES], ids=[b[3] for b in ART_BRUSHES])
def test_free_drawing_with_the_suggested_calibration_leaves_the_path_inked(session, category, label, color):
    pressures = [e["p"] for s in session.values() if s[0]["passo"] == FREE_DRAWING_STEP for e in s if e["k"] == "move"]
    suggestion = suggest_from_pressures(pressures)
    assert suggestion is not None and not suggestion.is_identity

    bare = _path_without_ink(session, category, label, color, PenCalibration())
    calibrated = _path_without_ink(session, category, label, color, suggestion)
    assert calibrated <= MAX_PATH_WITHOUT_INK, (
        f"{category}/{label}: {calibrated:.0%} do trajeto sem tinta com a calibração sugerida "
        f"(ceiling {suggestion.ceiling}); sem calibração eram {bare:.0%}. Limite {MAX_PATH_WITHOUT_INK:.0%}."
    )
    assert calibrated <= bare
