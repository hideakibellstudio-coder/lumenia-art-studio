"""Nome padrão de camada e grupo no idioma da interface.

Até 2026-09-25 a camada nova se chamava "Camada N" e o grupo "Novo Grupo" em
qualquer idioma (o nome é dado do documento, criado fora do `tr`). Agora vem de
`layers.default_name` e `layers.new_group`, nos 4 idiomas, e o documento sem
nome vem de `dialogs.untitled_name`. O motor cria a camada inicial de cada
contexto com o nome fixo "Camada 1" (C++); a ponte dá a ela o mesmo nome que o
documento usa, sem sujar o documento.
"""
from __future__ import annotations

import pytest

from ui.core.document.document import Document
from ui.core.document.manager import DocumentManager
from ui.infrastructure.i18n import I18nManager


@pytest.fixture
def locale(qapp):
    i18n = I18nManager.instance()
    previous = i18n.get_current_locale()
    yield i18n
    i18n.set_locale(previous, is_auto=False)


@pytest.mark.parametrize("code, layer, group", [
    ("en_US", "Layer 1", "New Group"),
    ("pt_BR", "Camada 1", "Novo Grupo"),
    ("es_ES", "Capa 1", "Nuevo Grupo"),
])
def test_new_layer_and_group_are_named_in_the_interface_language(locale, code, layer, group):
    assert locale.set_locale(code, is_auto=False)
    document = Document(f"names-{code}", "Nomes", 8, 8)
    manager = document.layer_manager
    layer_uid = manager.add_layer()
    group_uid = manager.add_group()
    names = {item.uid: item.name for item in manager.layers}
    assert names[layer_uid] == layer.replace("1", str(layer_uid))
    assert names[group_uid] == group


def test_new_document_and_engine_agree_on_the_initial_layer_name(locale):
    pytest.importorskip("aladyn_engine_native")
    from ui.core.engine.registry import EngineRegistry
    from ui.infrastructure.bridge_client.aladyn import AladynBackend

    if EngineRegistry.instance().get_backend() is None:
        EngineRegistry.instance().setup([AladynBackend()])
    backend = EngineRegistry.instance().get_backend()
    previous = backend.get_active_document_context()
    assert locale.set_locale("en_US", is_auto=False)
    manager = DocumentManager.instance()
    document = manager.new_document(16, 16, activate=False)
    try:
        assert document.name.startswith("Untitled ")
        assert [layer.name for layer in document.layer_manager.layers] == ["Layer 1"]
        backend.set_active_document_context(document.uid, 16, 16)
        assert backend.get_layer_info(0)["name"] == "Layer 1"
        assert not document.is_dirty, "batizar a camada inicial do motor não é edição"
    finally:
        if previous:
            backend.set_active_document_context(previous, 16, 16)
        backend.close_document_context(document.uid)
        manager.close_document(document.uid)
