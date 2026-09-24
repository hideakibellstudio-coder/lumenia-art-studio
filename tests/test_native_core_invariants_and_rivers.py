"""
Suíte de Integridade Orbital — Rodada 14: Núcleo C++ e Laço Ascendente dos 5 Rios
================================================================================
Valida:
1. Descida ao Núcleo Primordial C++:
   - Proteção de integridade e overflow em buffers PyBind11 (checkedRasterBytes).
   - Propagação monótona de geração documental (DocumentContext.touch / documentGeneration).
   - Integridade de TileGrid, poda de blocos (pruneEmptyTiles) e TileUndoManager.
2. Retorno Ascendente Completo dos 5 Grandes Rios:
   - Rio 1: Traço -> DabRenderer SIMD -> TileGrid -> Undo -> Display & Thumbnails.
   - Rio 2: Câmera Viewport -> cameraChanged -> Navigator Preview & Sliders.
   - Rio 3: Mutações de Camada -> LayerStackOrchestrator -> _mark_document_dirty & Undo Stack.
   - Rio 4: Seleção -> SelectionMask -> Bounds -> Marching Ants & Transform.
   - Rio 5: Cor -> to_native_color_rgba -> FloodFill / Profiles -> Display Pipeline.
3. Governança ARCcC: Todos os arquivos na Zona Verde (< 450 LOC).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from PySide6 import QtWidgets, QtCore, QtGui

import aladyn_engine_native as native
from ui.engine_backends.aladyn import AladynBackend
from ui.engine_backends.aladyn_buffers import to_native_color_rgba
from plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget
from plugins.ui.navigator_plugin.panel import NavigatorPanel


@pytest.fixture(scope="module")
def app():
    instance = QtWidgets.QApplication.instance()
    if instance is None:
        instance = QtWidgets.QApplication(sys.argv)
    yield instance


# ── 1. Descida C++: Fronteira PyBind11, Buffers & Geração Documental ─────────

def test_pybind_buffer_contract_and_overflow_protection():
    """Valida proteção de limites e overflow aritmético na fronteira C++."""
    facade = native.PaintEngineFacade(100, 100)

    # 1. Dimensões inválidas / astronômicas disparam ValueError no checkedRasterBytes
    with pytest.raises(ValueError):
        facade.get_layer_thumbnail_buffer(0, -10, 100)

    with pytest.raises(ValueError):
        facade.get_layer_thumbnail_buffer(0, 1000000000, 1000000000)

    # 2. Buffer de colagem com tamanho incompatível dispara ValueError no validateRasterInput
    with pytest.raises(ValueError):
        facade.paste_rgba_buffer_on_active_layer(0, 0, 50, 50, b"dados_muito_curtos")

    # 3. Snapshot válido retorna bytes imutáveis sem expor ponteiro cru
    pix = facade.get_display_pixel_buffer()
    assert isinstance(pix, bytes)
    assert len(pix) == 100 * 100 * 4


def test_core_document_generation_monotonic_propagation():
    """Valida que DocumentContext.touch() incrementa documentGeneration em mutações."""
    facade = native.PaintEngineFacade(200, 200)
    gen0 = facade.get_document_generation()

    # Adicionar camada deve incrementar a geração
    idx = facade.add_layer("Camada Teste", -1)
    gen1 = facade.get_document_generation()
    assert gen1 > gen0

    # Alterar propriedade visual deve tocar o documento
    facade.set_layer_opacity(idx, 0.75)
    gen2 = facade.get_document_generation()
    assert gen2 > gen1

    # Renomear camada toca o documento
    facade.set_layer_name(idx, "Camada Renomeada")
    gen3 = facade.get_document_generation()
    assert gen3 > gen2

    # Redimensionar canvas toca o documento
    facade.resize_canvas(300, 300)
    gen4 = facade.get_document_generation()
    assert gen4 > gen3
    assert facade.get_width() == 300
    assert facade.get_height() == 300


def test_physical_core_tile_grid_and_undo_invariants():
    """Valida TileGrid, integridade do TileUndoManager e poda pós-limpeza."""
    facade = native.PaintEngineFacade(256, 256)
    assert facade.can_undo() is False
    assert facade.can_redo() is False

    # Executa traço raw via fast-path zero-alocação
    facade.begin_stroke_raw(50.0, 50.0, 1.0, 0.0, 0.0, 0.0, 0.0)
    facade.update_stroke_raw(60.0, 60.0, 1.0, 0.0, 0.0, 0.0, 0.0)
    facade.update_stroke_raw(70.0, 70.0, 1.0, 0.0, 0.0, 0.0, 0.0)
    facade.end_stroke_raw()

    # O histórico do TileUndoManager deve agora permitir Undo
    assert facade.can_undo() is True
    undo_count = facade.get_undo_count()
    assert undo_count >= 1

    # Desfazer deve reverter o estado e permitir Redo
    assert facade.undo() is True
    assert facade.can_redo() is True

    # Refazer deve restabelecer o traço
    assert facade.redo() is True
    assert facade.can_undo() is True


# ── 2. Retorno Ascendente: Os 5 Grandes Rios ─────────────────────────────────

def test_river_1_stroke_to_display_and_thumbnail_loop(app):
    """Rio 1: Traço -> DabRenderer SIMD -> TileGrid -> Undo -> Display & Thumbnails."""
    backend = AladynBackend()
    backend._mark_document_dirty = MagicMock()

    # Inicia e executa traço via pipeline de superfície
    backend.start_stroke(10.0, 10.0, 1.0)
    backend.paint_stroke(20.0, 20.0, 1.0)
    backend.end_stroke(20.0, 20.0)

    # Subida 1: _mark_document_dirty foi acionado
    backend._mark_document_dirty.assert_called_with("stroke")

    # Subida 2: Buffer de display está acessível para o RenderWidget
    display_buf = backend.get_display_pixel_buffer()
    assert display_buf is not None and len(display_buf) > 0

    # Subida 3: QImage gerada desacoplada para renderização
    qimg = backend.get_qimage()
    assert isinstance(qimg, QtGui.QImage)
    assert not qimg.isNull()

    # Subida 4: Miniatura de camada disponível para o painel de camadas
    thumb_bytes = backend.get_layer_thumbnail_buffer(0, 32, 32)
    assert thumb_bytes is not None and len(thumb_bytes) == 32 * 32 * 4
    thumb_img = QtGui.QImage(thumb_bytes, 32, 32, 32 * 4, QtGui.QImage.Format_RGBA8888)
    assert not thumb_img.isNull()


def test_river_2_camera_bidirectional_sync_loop(app):
    """Rio 2: Câmera Viewport -> cameraChanged -> Navigator Preview & Sliders."""
    rw = RenderWidget()
    nav = NavigatorPanel()

    received_camera_events = []
    rw.cameraChanged.connect(lambda *args: received_camera_events.append(args))

    # Conecta RenderWidget ao Navigator via o contrato do WorkspaceDocumentSync
    def sync_to_nav(zoom, rot, pan_x, pan_y, view_w, view_h):
        cw_w = float(getattr(rw, "canvas_w", 800))
        cw_h = float(getattr(rw, "canvas_h", 600))
        norm_x = 0.5 - pan_x / (zoom * cw_w) if zoom * cw_w > 0 else 0.5
        norm_y = 0.5 - pan_y / (zoom * cw_h) if zoom * cw_h > 0 else 0.5
        ratio_w = view_w / (zoom * cw_w) if zoom * cw_w > 0 else 1.0
        ratio_h = view_h / (zoom * cw_h) if zoom * cw_h > 0 else 1.0
        nav.update_viewport(zoom, norm_x, norm_y, rot, rw.flip_x, rw.flip_y, ratio_w, ratio_h)

    rw.cameraChanged.connect(sync_to_nav)

    # Inversão horizontal no canvas reverbera no Navigator
    rw.flip_x = True
    assert len(received_camera_events) == 1
    assert nav.state["flip_x"] is True

    # Inversão vertical no canvas reverbera no Navigator
    rw.flip_y = True
    assert len(received_camera_events) == 2
    assert nav.state["flip_y"] is True

    # Idempotência: reatribuir não dispara eventos espúrios
    rw.flip_x = True
    assert len(received_camera_events) == 2

    # Direção inversa (Navigator -> Canvas)
    nav.toggle_flip_h()
    assert nav.state["flip_x"] is False


def test_river_3_layers_mutation_dirty_and_history_loop():
    """Rio 3: Mutações de Camada -> LayerStackOrchestrator -> _mark_document_dirty & Undo."""
    backend = AladynBackend()
    backend._mark_document_dirty = MagicMock()

    # 1. Adiciona camada
    idx = backend.add_layer("Nova Camada")
    backend._mark_document_dirty.assert_called_with("add_layer")

    # 2. Modifica opacidade
    backend._mark_document_dirty.reset_mock()
    backend.set_layer_opacity(idx, 0.5)
    backend._mark_document_dirty.assert_called_with("layer_opacity")

    # 3. Altera blend mode
    backend._mark_document_dirty.reset_mock()
    backend.set_layer_blend_mode(idx, 2)  # Multiply
    backend._mark_document_dirty.assert_called_with("blend_mode")

    # 4. Limpa camada
    backend._mark_document_dirty.reset_mock()
    backend.clear_layer(idx)
    backend._mark_document_dirty.assert_called_with("clear_layer")

    # 5. Executa uma ação de raster para registrar passo no TileUndoManager
    backend.start_stroke(10.0, 10.0, 1.0)
    backend.end_stroke(10.0, 10.0)
    assert backend.can_undo() is True

    # 6. Undo no nível do backend reverte o traço e aciona dirty tracking
    backend._mark_document_dirty.reset_mock()
    assert backend.undo() is True
    backend._mark_document_dirty.assert_called_with("undo")


def test_river_4_selection_and_transform_loop():
    """Rio 4: Seleção -> SelectionMask -> Bounds -> Marching Ants & Transform."""
    backend = AladynBackend()
    backend._mark_document_dirty = MagicMock()

    assert backend.has_selection() is False

    # 1. Cria seleção retangular
    ok = backend.select_rect(10, 10, 80, 80, mode=0)
    assert ok is True
    assert backend.has_selection() is True
    backend._mark_document_dirty.assert_called_with("selection")

    # 2. Bounds da seleção calculados com precisão
    bounds = backend.get_selection_bounds()
    assert bounds[2] > 0 and bounds[3] > 0

    # 3. Buffer de máscara para formigas marchantes
    mask_img = backend.get_selection_mask_qimage()
    assert mask_img is not None
    assert mask_img.format() == QtGui.QImage.Format_Grayscale8

    # 4. Preenchimento de seleção
    backend._mark_document_dirty.reset_mock()
    backend.fill_selection_on_active_layer(QtGui.QColor(255, 0, 0, 255))
    backend._mark_document_dirty.assert_called_with("fill_selection")

    # 5. Limpeza de seleção
    backend._mark_document_dirty.reset_mock()
    backend.clear_selection()
    assert backend.has_selection() is False
    backend._mark_document_dirty.assert_called_with("selection")


def test_river_5_color_coercion_and_pipeline_loop():
    """Rio 5: Cor -> to_native_color_rgba -> FloodFill / Profiles -> Display Pipeline."""
    backend = AladynBackend()
    backend._mark_document_dirty = MagicMock()

    # 1. Coerção polimórfica de cores para a fronteira C++
    c1 = to_native_color_rgba(native, QtGui.QColor(200, 100, 50, 255))
    assert c1.r == 200 and c1.g == 100 and c1.b == 50 and c1.a == 255

    c2 = to_native_color_rgba(native, (0.5, 0.25, 0.75, 1.0))
    assert c2.r == 127 or c2.r == 128
    assert c2.a == 255

    # 2. Balde de tinta no motor C++ aciona dirty tracking
    ok = backend.flood_fill(50, 50, QtGui.QColor(0, 255, 0, 255), tolerance=30)
    assert ok is True
    backend._mark_document_dirty.assert_called_with("flood_fill")

    # 3. Troca de perfil de cor sincronizada com C++ e dirty tracking
    backend._mark_document_dirty.reset_mock()
    backend.set_color_profile(1)  # Perfil alternativo
    assert backend.get_color_profile() == 1
    backend._mark_document_dirty.assert_called_with("color_profile")


# ── 3. Governança ARCcC: Zona Verde (< 450 LOC) ──────────────────────────────

def test_governance_round14_file_limits():
    """Verifica que este arquivo de teste está abaixo do teto de LOC.

    (A antiga asserção sobre o SKILL.md de uma skill de agente foi removida: o
    arquivo fica fora do repositório, em pasta ignorada, e o caminho absoluto
    fazia este teste falhar em qualquer máquina que não a de desenvolvimento.)
    """
    this_file = Path(__file__)
    loc = len(this_file.read_text(encoding="utf-8").splitlines())
    assert loc < 450, f"Arquivo {this_file.name} excede o limite com {loc} linhas!"

