"""Transformar -> Distorcer -- 2026-09-23.

Antes, o modo "Distorcer" da ferramenta fazia exatamente o mesmo que "Livre".
Agora cada canto vai para onde o usuário arrasta (mapeamento projetivo). A
prévia usa QTransform.quadToQuad e o commit usa a homografia do motor; os
testes abaixo garantem que os dois concordam e que o caminho livre não mudou.
"""

from __future__ import annotations

import pytest

native = pytest.importorskip("aladyn_engine_native")
from PySide6 import QtCore, QtGui  # noqa: E402

from ui.plugins.system.workspace_core.workspace.canvas.tools import transform_distort as d  # noqa: E402
from ui.plugins.system.workspace_core.workspace.canvas.tools.transform_tool_controller import (  # noqa: E402
    TransformToolController,
)


@pytest.fixture(scope="module", autouse=True)
def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication(["--platform", "offscreen"])

L = 64
VERMELHO = bytes([220, 30, 30, 255])
VERDE = bytes([30, 220, 30, 255])


def _facade_com_bloco():
    """Bloco 16x16 vermelho em (8, 8) com um ponto verde 2x2 no centro."""
    f = native.PaintEngineFacade(L, L)
    bloco = bytearray(VERMELHO * 256)
    for y in (7, 8):
        for x in (7, 8):
            i = (y * 16 + x) * 4
            bloco[i:i + 4] = VERDE
    assert f.paste_rgba_buffer_on_active_layer(8, 8, 16, 16, bytes(bloco))
    f.select_rect(8, 8, 16, 16)
    return f


def _camada(f) -> bytes:
    return f.get_layer_pixel_buffer(f.get_active_layer_index())


def _alfa(buf: bytes, x: int, y: int) -> int:
    return buf[(y * L + x) * 4 + 3]


def _centro_do_verde(buf: bytes) -> tuple[float, float]:
    pts = [(i // 4 % L, i // 4 // L) for i in range(0, len(buf), 4)
           if buf[i + 1] > 150 and buf[i] < 100 and buf[i + 3] > 200]
    assert pts, "o ponto verde sumiu"
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def test_quad_igual_a_translacao_da_o_mesmo_resultado_do_modo_livre():
    livre = _facade_com_bloco()
    assert livre.begin_transform()
    assert livre.commit_transform(10.0, 5.0, 1.0, 1.0, 0.0, 16.0, 16.0, False, False, 0)

    distorcido = _facade_com_bloco()
    assert distorcido.begin_transform()
    x0, y0, x1, y1 = 18.0, 13.0, 34.0, 29.0
    assert distorcido.commit_transform_distort([x0, y0, x1, y0, x1, y1, x0, y1], 0)
    assert _camada(livre) == _camada(distorcido)


def test_trapezio_estreita_o_topo_e_alarga_a_base():
    f = _facade_com_bloco()
    assert f.begin_transform()
    assert f.commit_transform_distort([20.0, 8.0, 28.0, 8.0, 44.0, 40.0, 4.0, 40.0], 2)
    buf = _camada(f)
    assert _alfa(buf, 24, 10) > 0 and _alfa(buf, 12, 10) == 0, "topo deveria ficar estreito"
    assert _alfa(buf, 6, 38) > 0 and _alfa(buf, 42, 38) > 0, "base deveria ficar larga"


def test_previa_e_commit_levam_o_mesmo_ponto_ao_mesmo_lugar():
    quad = [QtCore.QPointF(10, 6), QtCore.QPointF(40, 12), QtCore.QPointF(50, 52), QtCore.QPointF(4, 44)]
    fonte = QtCore.QRectF(8, 8, 16, 16)
    previa: QtGui.QTransform | None = d.matrix_from_quad(fonte, quad)
    assert previa is not None
    esperado = previa.map(QtCore.QPointF(16.0, 16.0))  # centro do ponto verde

    f = _facade_com_bloco()
    assert f.begin_transform()
    assert f.commit_transform_distort(d.flatten(quad), 1)
    cx, cy = _centro_do_verde(_camada(f))
    assert abs(cx - esperado.x()) < 1.5 and abs(cy - esperado.y()) < 1.5, ((cx, cy), esperado)


def test_quad_invalido_cancela_e_devolve_os_pixels():
    f = _facade_com_bloco()
    original = _camada(f)
    assert f.begin_transform()
    gravata = [8.0, 8.0, 24.0, 24.0, 24.0, 8.0, 8.0, 24.0]  # cantos cruzados
    assert f.commit_transform_distort(gravata, 2) is False
    assert not f.is_transform_active()
    assert _camada(f) == original


def test_distorcer_entra_no_desfazer():
    f = _facade_com_bloco()
    original = _camada(f)
    assert f.begin_transform()
    assert f.commit_transform_distort([12.0, 8.0, 30.0, 10.0, 26.0, 30.0, 8.0, 24.0], 2)
    assert _camada(f) != original
    f.undo()
    assert _camada(f) == original


# ── Geometria da UI ─────────────────────────────────────────────────────

def _quad(*coords):
    return [QtCore.QPointF(coords[i], coords[i + 1]) for i in range(0, 8, 2)]


def test_convexidade_bate_com_o_motor():
    assert d.is_convex_quad(_quad(0, 0, 10, 0, 10, 10, 0, 10))
    assert d.is_convex_quad(_quad(0, 0, 10, 2, 8, 9, 1, 12))
    assert not d.is_convex_quad(_quad(0, 0, 10, 10, 10, 0, 0, 10))  # gravata
    assert not d.is_convex_quad(_quad(0, 0, 10, 0, 3, 3, 0, 10))    # côncavo


def test_arrastar_canto_lado_e_tudo():
    q = _quad(0, 0, 10, 0, 10, 10, 0, 10)
    delta = QtCore.QPointF(2, 3)
    assert d.flatten(d.drag(q, "tr", delta)) == [0, 0, 12, 3, 10, 10, 0, 10]
    assert d.flatten(d.drag(q, "mr", delta)) == [0, 0, 12, 3, 12, 13, 0, 10]
    assert d.flatten(d.drag(q, "move", delta)) == [2, 3, 12, 3, 12, 13, 2, 13]
    assert d.flatten(q) == [0, 0, 10, 0, 10, 10, 0, 10], "o original não pode mudar"


def test_espelhar_e_girar_mantem_o_quad_no_lugar():
    q = _quad(0, 0, 10, 0, 10, 10, 0, 10)
    assert d.flatten(d.mirror(q, horizontal=True)) == [10, 0, 0, 0, 0, 10, 10, 10]
    girado = d.flatten(d.rotate_90(q, clockwise=True))
    assert girado == [10, 0, 10, 10, 0, 10, 0, 0]


class _Backend:
    def __init__(self):
        self.chamadas = []

    def commit_transform_distort(self, corners, interp_mode=2):
        self.chamadas.append(("distort", list(corners), interp_mode))
        return True

    def commit_transform(self, **kw):
        self.chamadas.append(("livre", kw))
        return True


def test_controlador_no_modo_distorcer(monkeypatch):
    from ui.plugins.system.workspace_core.workspace.canvas.tools import transform_tool_controller as mod

    backend = _Backend()
    monkeypatch.setattr(mod.EngineRegistry, "instance",
                        classmethod(lambda cls: type("R", (), {"get_backend": lambda self: backend})()))
    widget = type("W", (), {"update": lambda self: None})()
    ctrl: TransformToolController = mod.TransformToolController(widget)
    ctrl.active = True
    ctrl.source_rect = QtCore.QRectF(0, 0, 100, 100)
    ctrl.pivot = QtCore.QPointF(50, 50)
    ctrl.distort = True

    ctrl.begin_drag("br", QtCore.QPointF(100, 100))
    ctrl.apply_drag(QtCore.QPointF(140, 120), QtCore.Qt.NoModifier)
    esperado = [0, 0, 100, 0, 140, 120, 0, 100]
    assert d.flatten(ctrl.quad) == esperado
    assert ctrl.get_transform_matrix().map(QtCore.QPointF(100, 100)) == QtCore.QPointF(140, 120)

    # Arrasto que dobraria o quad é recusado (fica o último válido).
    ctrl.begin_drag("br", QtCore.QPointF(140, 120))
    ctrl.apply_drag(QtCore.QPointF(-200, -200), QtCore.Qt.NoModifier)
    assert d.flatten(ctrl.quad) == esperado

    # Sem pivô nem rotação enquanto distorce: o centro é "mover".
    assert ctrl.hit_test_handle(QtCore.QPointF(50, 50), 1.0) == "move"

    ctrl.commit()
    assert backend.chamadas == [("distort", esperado, ctrl.interp_mode)]
    assert ctrl.quad is None and not ctrl.active
