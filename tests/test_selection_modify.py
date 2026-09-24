"""Seleção -> Modificar (Expandir, Contrair, Suavizar Borda) -- 2026-09-23.

Antes, o diálogo abria, mostrava "Seleção modificada" e nada mudava. Agora a
morfologia roda no motor (engine/core/raster/SelectionMorphology.cpp): a borda
é a linha de 50% da máscara e o raio é medido em pixels inteiros nos lados
retos (retângulo 10x10 expandido 5 vira 20x20).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from ui.boundary.orchestrator.main_window import MainWindow

native = pytest.importorskip("aladyn_engine_native")

L = 40


def _mascara(f) -> bytes:
    return f.get_selection_mask_buffer() or bytes(L * L)


def _px(m: bytes, x: int, y: int) -> int:
    return m[y * L + x]


def _facade_com_retangulo(x, y, w, h):
    f = native.PaintEngineFacade(L, L)
    assert f.select_rect(x, y, w, h)
    return f


def test_expandir_cresce_o_raio_exato_nos_lados_e_arredonda_os_cantos():
    f = _facade_com_retangulo(10, 10, 10, 10)
    assert f.expand_selection(5)
    assert list(f.get_selection_bounds()) == [5, 5, 20, 20]
    m = _mascara(f)
    for x in range(5, 25):
        assert _px(m, x, 15) == 255, x
    assert _px(m, 4, 15) == 0 and _px(m, 25, 15) == 0
    assert _px(m, 5, 5) < 128, "canto deveria ser arredondado (distância euclidiana)"


def test_contrair_encolhe_o_raio_exato():
    f = _facade_com_retangulo(10, 10, 20, 20)
    assert f.contract_selection(5)
    assert list(f.get_selection_bounds()) == [15, 15, 10, 10]
    m = _mascara(f)
    assert all(_px(m, x, 20) == 255 for x in range(15, 25))


def test_contrair_mais_que_a_metade_remove_a_selecao():
    f = _facade_com_retangulo(10, 10, 6, 6)
    assert f.contract_selection(5)
    assert not f.has_selection()


def test_borda_da_tela_nao_contrai_nem_esmaece():
    for operacao in ("contract_selection", "feather_selection"):
        f = native.PaintEngineFacade(L, L)
        f.select_all()
        assert getattr(f, operacao)(6)
        assert set(_mascara(f)) == {255}, operacao


def test_suavizar_cria_gradiente_simetrico_e_preserva_a_massa():
    f = _facade_com_retangulo(10, 10, 20, 20)
    antes = sum(_mascara(f))
    assert f.feather_selection(6)
    m = _mascara(f)
    assert _px(m, 20, 20) == 255
    assert 90 <= _px(m, 10, 20) <= 165, "a borda deveria ficar perto de 50%"
    assert 0 < _px(m, 7, 20) < _px(m, 10, 20) < _px(m, 13, 20) < 255
    linha = [_px(m, x, 20) for x in range(0, 20)]
    assert linha == sorted(linha), "gradiente deveria subir de fora para dentro"
    assert abs(sum(m) - antes) / antes < 0.02


def test_expandir_preserva_o_esmaecido_que_ja_existia():
    f = native.PaintEngineFacade(L, L)
    assert f.select_rect(10, 10, 20, 20, feather_px=4)
    antes = _mascara(f)
    assert f.expand_selection(2)
    depois = _mascara(f)
    assert all(b >= a for a, b in zip(antes, depois))


@pytest.mark.parametrize("operacao", ["expand_selection", "contract_selection", "feather_selection"])
def test_sem_selecao_ou_raio_invalido_nao_faz_nada(operacao):
    f = native.PaintEngineFacade(L, L)
    assert getattr(f, operacao)(5) is False
    f.select_rect(10, 10, 10, 10)
    antes = _mascara(f)
    assert getattr(f, operacao)(0) is False
    assert _mascara(f) == antes


def test_modificar_muda_a_geracao_do_documento():
    """Sem isso a transação de documento descartava o passo (sem Desfazer)."""
    f = _facade_com_retangulo(10, 10, 10, 10)
    g = f.get_document_generation()
    assert f.expand_selection(0) is False
    assert f.get_document_generation() == g
    assert f.feather_selection(2)
    assert f.get_document_generation() > g


def test_backend_marca_documento_sujo_so_quando_muda(monkeypatch):
    from PySide6.QtWidgets import QApplication
    from ui.engine_backends.aladyn import AladynBackend

    QApplication.instance() or QApplication(["--platform", "offscreen"])
    backend = AladynBackend()
    backend.set_active_document_context("modificar-selecao", L, L)
    try:
        motivos: list[str] = []
        monkeypatch.setattr(backend, "_mark_document_dirty", motivos.append)
        assert backend.expand_selection(3) is False
        assert motivos == []
        backend.select_rect(10, 10, 10, 10)
        motivos.clear()
        assert backend.expand_selection(3) is True
        assert backend.feather_selection(2) is True
        assert backend.contract_selection(1) is True
        assert motivos == ["selection"] * 3
    finally:
        backend.close_document_context("modificar-selecao")


# ── Caminho completo pela interface (menu -> diálogo -> canvas -> motor) ──

class _DialogoFalso:
    """Substitui o diálogo modal: exec() bloquearia a suíte."""

    px = 4

    def __init__(self, mode: str, parent=None):
        self.mode = mode

    def exec(self):
        from PySide6 import QtWidgets
        return QtWidgets.QDialog.Accepted

    def get_pixels(self) -> int:
        return self.px


@pytest.fixture
def janela_com_documento():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication(["--platform", "offscreen"])
    from tests.main_window_fixture import main_window_com_workspace
    from ui.core.document.document import Document
    from ui.core.document.manager import DocumentManager

    win = main_window_com_workspace()
    dm = DocumentManager.instance()
    doc: Document = dm.new_document(200, 200, "Modificar seleção")
    try:
        yield win
    finally:
        dm.close_document(doc.uid)


def test_menu_expandir_aplica_no_motor(janela_com_documento, monkeypatch):
    import ui.boundary.orchestrator.edit_actions as acoes
    from ui.core.engine.registry import EngineRegistry

    win = janela_com_documento
    backend = EngineRegistry.instance().get_backend()
    backend.select_rect(50, 50, 20, 20)
    monkeypatch.setattr(acoes, "ModifySelectionDialog", _DialogoFalso)
    win.edit_actions.modify_selection("expand")
    assert list(backend.get_selection_bounds()) == [46, 46, 28, 28]
    assert "4 px" in win.status_bar.currentMessage()


def test_menu_sem_selecao_avisa_e_nao_abre_dialogo(janela_com_documento, monkeypatch):
    import ui.boundary.orchestrator.edit_actions as acoes
    from ui.core.engine.registry import EngineRegistry

    EngineRegistry.instance().get_backend().clear_selection()

    def _nao_abrir(*_a, **_k):
        raise AssertionError("o diálogo não deveria abrir sem seleção")

    monkeypatch.setattr(acoes, "ModifySelectionDialog", _nao_abrir)
    janela_com_documento.edit_actions.modify_selection("contract")
    assert janela_com_documento.status_bar.currentMessage()


def test_modificar_pela_interface_entra_no_desfazer(janela_com_documento: "MainWindow"):
    from plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget
    from ui.core.engine.backend import EngineBackend
    from ui.core.engine.registry import EngineRegistry

    backend: EngineBackend = EngineRegistry.instance().get_backend()
    backend.select_rect(50, 50, 20, 20)
    cw: RenderWidget = janela_com_documento.workspace.canvas_widget
    assert cw.modify_selection("contract", 5)
    assert list(backend.get_selection_bounds()) == [55, 55, 10, 10]
    assert backend.can_undo()
    backend.undo()
    assert list(backend.get_selection_bounds()) == [50, 50, 20, 20]
    backend.redo()
    assert list(backend.get_selection_bounds()) == [55, 55, 10, 10]
