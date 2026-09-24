"""Contrato da telemetria com o motor nativo e o "Limpar Undo" de verdade.

- todo campo do `TelemetrySnapshot` existe na struct nativa
  `RealTimeStrokeMetrics` (renomear no C++ quebra aqui, não vira zero na tela);
- `simd_active` diz se o motor foi compilado com AVX2 (a tela afirmava
  "AVX2 / SSE2 Ativo" até no build escalar, que é o padrão);
- o "Limpar Undo" das telas de telemetria descarta o histórico do motor e do
  documento (até 2026-09-24 esvaziava listas privadas do backend e dizia
  "limpa com sucesso" com a RAM do histórico intacta);
- o benchmark do diagnóstico não pinta no documento do usuário.
"""
from dataclasses import fields

import pytest
from PySide6.QtWidgets import QApplication

import aladyn_engine_native as aen
from ui.core.dialogs.telemetry_benchmark import run_stroke_benchmark
from ui.core.dialogs.telemetry_common import clear_active_history
from ui.core.document.document import Document
from ui.core.document.manager import DocumentManager
from ui.core.engine.registry import EngineRegistry
from ui.core.engine.telemetry_dto import TelemetrySnapshot
from ui.core.i18n import tr
from ui.engine_backends.aladyn import AladynBackend

app = QApplication.instance() or QApplication(["--platform", "offscreen"])


def stroke(backend_or_facade, x0=10.0):
    backend_or_facade.begin_stroke_raw(x0, 10.0, 1.0)
    for i in range(1, 12):
        backend_or_facade.update_stroke_raw(x0 + i * 3, 10.0 + i * 3, 0.9)
    backend_or_facade.end_stroke_raw()


def test_todo_campo_do_dto_existe_na_struct_nativa():
    native = aen.RealTimeStrokeMetrics()
    missing = [f.name for f in fields(TelemetrySnapshot) if not hasattr(native, f.name)]
    assert not missing, f"campos do TelemetrySnapshot sem par nativo: {missing}"
    snap = TelemetrySnapshot.from_native(native)
    assert isinstance(snap.active_engine_id, int) and isinstance(snap.simd_active, bool)


def test_from_native_nao_esconde_campo_sumido():
    class Renamed:  # struct nativa com um campo a menos
        pass

    with pytest.raises(AttributeError):
        TelemetrySnapshot.from_native(Renamed())


def test_snapshot_traz_o_motor_ativo_do_traco():
    facade = aen.PaintEngineFacade(64, 64)
    facade.add_layer("Camada")
    facade.select_layer(0)
    facade.set_telemetry_enabled(True)
    facade.set_engine_type(int(aen.EngineType.Inker))
    stroke(facade)
    snap = TelemetrySnapshot.from_native(facade.get_telemetry_snapshot())
    assert snap.active_engine_id == int(aen.EngineType.Inker)


def test_clear_history_nativo_libera_desfazer_e_refazer():
    facade = aen.PaintEngineFacade(64, 64)
    facade.add_layer("Camada")
    facade.select_layer(0)
    facade.set_telemetry_enabled(True)
    for x0 in (5.0, 20.0, 35.0):
        stroke(facade, x0)
    facade.undo()
    assert facade.can_undo() and facade.can_redo()
    assert facade.get_telemetry_snapshot().undo_stack_memory_mb > 0.0

    assert facade.clear_history() is True
    assert not facade.can_undo() and not facade.can_redo()
    assert facade.get_telemetry_snapshot().undo_stack_memory_mb == 0.0
    stroke(facade, 40.0)  # o histórico continua funcionando depois de limpo
    assert facade.can_undo()


@pytest.fixture
def session(monkeypatch):
    backend = AladynBackend()
    document = Document("telemetry-clear", "Telemetria", 32, 32)
    document.layer_manager.add_layer("Camada 1")
    backend.set_active_document_context(document.uid, 32, 32)
    monkeypatch.setattr(EngineRegistry.instance(), "get_backend", lambda: backend)
    monkeypatch.setattr(DocumentManager.instance(), "active_document", lambda: document)
    yield document, backend
    backend.close_document_context(document.uid)


def test_limpar_undo_descarta_o_historico_do_documento(session):
    document, backend = session
    stroke(backend)
    with document.history.transaction(backend):
        assert backend.duplicate_layer(0) >= 0
        document.layer_manager.duplicate_layer(document.layer_manager.get_active_layer().uid)
    assert backend.can_undo() and document.history.entries
    cleared = []
    document.history_cleared.connect(lambda: cleared.append(True))

    ok, message = clear_active_history()

    assert ok, message
    assert "Telemetria" in message
    assert not backend.can_undo() and not backend.can_redo()
    assert not document.history.entries
    assert cleared == [True]  # Desfazer/Refazer da janela principal se atualizam


def test_limpar_undo_sem_documento_diz_a_verdade(monkeypatch):
    monkeypatch.setattr(DocumentManager.instance(), "active_document", lambda: None)
    assert clear_active_history() == (False, tr("status.no_document"))


def test_benchmark_roda_fora_do_documento_do_usuario(session):
    document, backend = session
    before = bytes(backend.get_layer_pixel_buffer(0) or b"")
    undo_before = backend.can_undo()

    result = run_stroke_benchmark(backend, (document.width, document.height), steps=50)

    assert result.steps == 50 and result.elapsed_ms > 0
    assert backend.get_active_document_context() == document.uid
    assert bytes(backend.get_layer_pixel_buffer(0) or b"") == before
    assert backend.can_undo() == undo_before
