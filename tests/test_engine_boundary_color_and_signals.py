"""
Test Engine Boundary Round 11 — Validação da Fronteira Nativa C++ / Python.
=============================================================================
Testa o saneamento orbital da Rodada 11:
- Coerção resiliente e canônica de cores em to_native_color_rgba.
- Marcação dirty em mutações de raster (fill, delete, transform, paste, flip, rotate).
- Edições de pixels do menu passam por `canvas.run_as_stroke` (EditActions),
  que emite strokeStarted/strokeFinished em par mesmo com erro.
- Resolução canônica da cor ativa (BrushState) no menu de preenchimento.
- Governança ARCcC: ausência de resíduos 'if True:' e teto < 450 LOC.
"""

from __future__ import annotations
import pathlib
import pytest
from PySide6 import QtCore, QtGui, QtWidgets
from typing import Any

from ui.infrastructure.bridge_client.aladyn_buffers import to_native_color_rgba
from ui.infrastructure.bridge_client.aladyn_selection_mixin import AladynSelectionMixin
from ui.infrastructure.bridge_client.aladyn_transform_mixin import AladynTransformMixin
from ui.boundary.orchestrator.edit_actions import EditActions

# Garante instância de QApplication offscreen para o pytest
app = QtWidgets.QApplication.instance()
if app is None:
    app = QtWidgets.QApplication(["--platform", "offscreen"])


class _MockNativeColorRGBA:
    def __init__(self, r: int, g: int, b: int, a: int = 255):
        self.r = int(r)
        self.g = int(g)
        self.b = int(b)
        self.a = int(a)

    def __eq__(self, other):
        if not isinstance(other, _MockNativeColorRGBA):
            return False
        return (self.r, self.g, self.b, self.a) == (other.r, other.g, other.b, other.a)


class _MockNative:
    ColorRGBA = _MockNativeColorRGBA


class _MockCanvasWidget:
    """Canvas falso: conta as edições feitas "como traço"."""

    def __init__(self):
        self.stroke_runs = 0
        self.updated = False

    def run_as_stroke(self, action):
        self.stroke_runs += 1
        return action()

    def update(self):
        self.updated = True


class _MockLayerCommands:
    def __init__(self):
        self.cleared = 0

    def clear_active_pixels(self):
        self.cleared += 1


class _MockFacade:
    def __init__(self):
        self._has_sel = True
        self.last_fill_color = None
        self.deleted_selection = False
        self.cleared_layer_idx = None
        self.last_pasted = None

    def has_selection(self) -> bool:
        return self._has_sel

    def fill_selection_on_active_layer(self, color):
        self.last_fill_color = color
        return True

    def fill_area(self, x, y, color, tolerance=255, contiguous=False):
        self.last_fill_color = color
        return True

    def delete_selection_on_active_layer(self):
        self.deleted_selection = True
        return True

    def clear_layer(self, idx):
        self.cleared_layer_idx = idx
        return True

    def paste_rgba_buffer_on_active_layer(self, x, y, w, h, buf, mode=0, op=1.0):
        self.last_pasted = (x, y, w, h, buf)
        return True

    def commit_transform(self, *args):
        return True

    def flip_active_layer(self, *args):
        return True

    def rotate_active_layer_90(self, *args):
        return True


class _MockBackend(AladynSelectionMixin, AladynTransformMixin):
    def __init__(self):
        self._facade = _MockFacade()
        self._native = _MockNative()
        self.dirty_reasons: list[str] = []
        self.available = True

    def _mark_document_dirty(self, reason: str):
        self.dirty_reasons.append(reason)

    def has_selection(self) -> bool:
        return self._facade.has_selection()

    def fill_area(self, x, y, color, tolerance=255, contiguous=False):
        return self._facade.fill_area(x, y, color, tolerance, contiguous)

    def clear_layer(self, idx):
        return self._facade.clear_layer(idx)

    def get_qimage(self):
        return QtGui.QImage()


# ── TESTES ───────────────────────────────────────────────────────────────────

def test_to_native_color_rgba_coercion():
    """Valida que to_native_color_rgba trata diversos formatos sem exceção."""
    native = _MockNative()

    # 1. QColor
    qc = QtGui.QColor(10, 20, 30, 40)
    c1 = to_native_color_rgba(native, qc)
    assert c1 == _MockNativeColorRGBA(10, 20, 30, 40)

    # 2. Tupla de inteiros (r, g, b)
    c2 = to_native_color_rgba(native, (100, 150, 200))
    assert c2 == _MockNativeColorRGBA(100, 150, 200, 255)

    # 3. Tupla de inteiros (r, g, b, a)
    c3 = to_native_color_rgba(native, (1, 2, 3, 4))
    assert c3 == _MockNativeColorRGBA(1, 2, 3, 4)

    # 4. Tupla de floats normalizados (0.0 a 1.0)
    c4 = to_native_color_rgba(native, (1.0, 0.0, 0.5, 1.0))
    assert c4 == _MockNativeColorRGBA(255, 0, 127, 255)

    # 5. Instância existente de ColorRGBA
    existing = _MockNativeColorRGBA(50, 60, 70, 80)
    assert to_native_color_rgba(native, existing) is existing

    # 6. Fallback para None / tipos desconhecidos
    assert to_native_color_rgba(native, None) == _MockNativeColorRGBA(0, 0, 0, 255)
    assert to_native_color_rgba(None, qc) is None


def test_selection_and_transform_dirty_tracking():
    """Garante que mutações de seleção e transformação marcam o documento dirty."""
    backend = _MockBackend()

    # Fill selection com tupla defensiva
    res_fill = backend.fill_selection_on_active_layer((255, 0, 0, 255))
    assert res_fill is True
    assert "fill_selection" in backend.dirty_reasons

    # Delete selection
    res_del = backend.delete_selection_on_active_layer()
    assert res_del is True
    assert "delete_selection" in backend.dirty_reasons

    # Transform commit
    backend.commit_transform(0, 0, 1, 1, 0, 0, 0)
    assert "transform" in backend.dirty_reasons

    # Flip & Rotate
    backend.flip_active_layer(True)
    backend.rotate_active_layer_90(True)
    assert "flip" in backend.dirty_reasons
    assert "rotate" in backend.dirty_reasons

    # Paste
    backend.paste_rgba_buffer_on_active_layer(0, 0, 10, 10, b"\x00" * 400)
    assert "paste" in backend.dirty_reasons


def test_menu_actions_signal_symmetry_and_active_color(monkeypatch):
    """Edições do menu rodam como traço e o preenchimento usa a cor do BrushState."""
    cw = _MockCanvasWidget()
    layers = _MockLayerCommands()
    backend = _MockBackend()

    from ui.core.plugins.registry import ServiceRegistry
    from ui.core.state import install_app_state
    app_state = install_app_state(ServiceRegistry(), lambda: None)
    app_state.brush.set_color(QtGui.QColor(12, 34, 56, 255))

    window = QtWidgets.QWidget()
    edit = EditActions(window, lambda: backend, app_state.brush, cw, layers)
    messages = []
    edit.statusMessage.connect(lambda text, _ms: messages.append(text))

    # 1. Fill com seleção ativa: cor do usuário (BrushState), uma edição como traço
    edit.fill()
    assert cw.stroke_runs == 1
    assert backend._facade.last_fill_color == _MockNativeColorRGBA(12, 34, 56, 255)

    # 2. Fill sem seleção ativa
    backend._facade._has_sel = False
    edit.fill()
    assert cw.stroke_runs == 2

    # 3. Cut com seleção ativa apaga a seleção como traço
    backend._facade._has_sel = True
    edit.cut()
    assert cw.stroke_runs == 3
    assert backend._facade.deleted_selection is True
    assert layers.cleared == 0

    # 4. Cut sem seleção limpa a camada pelo comando de camadas (transação)
    backend._facade._has_sel = False
    edit.cut()
    assert layers.cleared == 1

    # 5. Paste da Área de Transferência
    qimg = QtGui.QImage(10, 10, QtGui.QImage.Format_RGBA8888)
    qimg.fill(QtGui.QColor(255, 0, 0, 255))
    QtWidgets.QApplication.clipboard().setImage(qimg)
    edit.paste()
    assert cw.stroke_runs == 4
    assert backend._facade.last_pasted is not None
    assert messages[-1].startswith("Imagem (10×10)")
    window.deleteLater()


def test_render_widget_run_as_stroke_emits_pair_even_on_error():
    """O canvas emite início e fim do traço em par, mesmo se a edição falhar."""
    from ui.plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget

    class _Signal:
        def __init__(self):
            self.count = 0

        def emit(self):
            self.count += 1

    class _Canvas:
        strokeStarted = _Signal()
        strokeFinished = _Signal()

    canvas = _Canvas()
    assert RenderWidget.run_as_stroke(canvas, lambda: 7) == 7
    with pytest.raises(RuntimeError):
        RenderWidget.run_as_stroke(canvas, lambda: (_ for _ in ()).throw(RuntimeError("x")))
    assert canvas.strokeStarted.count == canvas.strokeFinished.count == 2


def test_menu_actions_clean_code_and_arccc_governance():
    """Casca sem resíduos 'if True:' e todo arquivo abaixo do teto de 450 linhas."""
    for path in sorted(pathlib.Path("ui/boundary/orchestrator").glob("*.py")):
        lines = path.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines, start=1):
            assert line.strip() != "if True:", f"{path}:{idx} contém resíduo 'if True:'"
        assert len(lines) < 450, f"{path} excede o teto de 450 linhas: {len(lines)}"
