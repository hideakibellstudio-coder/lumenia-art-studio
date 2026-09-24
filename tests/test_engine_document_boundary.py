"""Fronteira motor ↔ documento: um caminho só, sem o motor conhecer o modelo.

- o backend avisa `EngineRegistry.notify_document_modified(uid, motivo)` e o
  `DocumentManager` suja o documento (até 2026-09-24 o backend importava o
  `DocumentManager`);
- o contexto nativo provisório do boot é liberado quando um documento real
  fica ativo (antes ficava alocado a sessão inteira);
- não existe mais a fachada paralela `BridgeClient` nem os comandos em
  dataclass com `dispatch` (sem chamadores em produção).
"""
import ast
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ui.core.document.manager import DocumentManager
from ui.core.engine.registry import EngineRegistry
from ui.engine_backends.aladyn import AladynBackend
from ui.engine_backends.aladyn_mdi_mixin import PLACEHOLDER_CONTEXT

app = QApplication.instance() or QApplication(["--platform", "offscreen"])
ROOT = Path(__file__).resolve().parent.parent


def test_motor_suja_o_documento_pelo_registro():
    dm = DocumentManager.instance()
    doc = dm.new_document(16, 16, name="Fronteira", activate=False)
    try:
        doc.is_dirty = False
        EngineRegistry.instance().notify_document_modified(doc.uid, "stroke")
        assert doc.is_dirty and doc.dirty_reason == "stroke"
        EngineRegistry.instance().notify_document_modified("nao-existe", "stroke")  # ignorado
        EngineRegistry.instance().notify_document_modified(None, "stroke")  # sem contexto
    finally:
        dm.close_document(doc.uid)


def test_backend_pinta_e_o_documento_fica_sujo():
    dm = DocumentManager.instance()
    doc = dm.new_document(16, 16, name="Pintado", activate=False)
    backend = AladynBackend()
    try:
        backend.set_active_document_context(doc.uid, 16, 16)
        backend.add_layer("Camada")
        doc.is_dirty = False
        assert backend.paste_rgba_buffer_on_active_layer(0, 0, 2, 2, bytes([255, 0, 0, 255]) * 4)
        assert doc.is_dirty
    finally:
        backend.close_document_context(doc.uid)
        dm.close_document(doc.uid)


def test_contexto_provisorio_sai_quando_um_documento_abre():
    backend = AladynBackend()
    assert backend.get_active_document_context() == PLACEHOLDER_CONTEXT
    backend.set_active_document_context("doc-real", 32, 32)
    try:
        backend.set_active_document_context(PLACEHOLDER_CONTEXT, 32, 32)  # recriado só se pedido
        backend.set_active_document_context("doc-real", 32, 32)
        backend.close_document_context("doc-real")
        assert backend.get_active_document_context() is None  # nada vivo sobrou
    finally:
        backend.close_document_context("doc-real")


def test_backend_nao_importa_o_modelo_de_documentos_para_sujar():
    for path in (ROOT / "ui" / "engine_backends").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        modules = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
        assert "ui.core.document.manager" not in modules, path.name


def test_um_caminho_so_ate_o_motor():
    assert not (ROOT / "ui" / "infrastructure" / "bridge_client").exists()
    assert not (ROOT / "ui" / "core" / "engine" / "commands.py").exists()
    assert "dispatch" not in vars(EngineRegistry)
