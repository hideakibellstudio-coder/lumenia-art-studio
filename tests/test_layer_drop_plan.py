"""Arrastar e soltar na árvore de camadas: onde as camadas movidas ficam.

`plan_layer_drop` foi extraído de `LayerModel.dropMimeData` (2026-09-24).
Lista de camadas: índice 0 é a de baixo; linha 0 da árvore é o filho de cima.
"""
from types import SimpleNamespace

from plugins.ui.layers_plugin.drop_plan import plan_layer_drop


def _layer(uid, parent=None, group=False):
    return SimpleNamespace(uid=uid, parent_uid=parent, is_group=group)


class _Manager:
    def __init__(self, layers):
        self.layers = layers

    def get_layer_by_uid(self, uid):
        return next((layer for layer in self.layers if layer.uid == uid), None)


def _stack():
    # de baixo para cima: 1, grupo 2 (filhos 3 e 4), 5
    return _Manager([_layer(1), _layer(2, group=True), _layer(3, 2), _layer(4, 2), _layer(5)])


def test_drop_on_group_end_goes_above_group_header_as_child():
    order, parents = plan_layer_drop(_stack(), [5], 2, -1)
    assert order == ["1", "2", "5", "3", "4"]
    assert parents["5"] == "2"
    assert parents["3"] == "2" and parents["1"] is None


def test_drop_on_plain_layer_goes_right_above_it_in_same_parent():
    order, parents = plan_layer_drop(_stack(), [1], 3, 0)
    assert order == ["2", "3", "1", "4", "5"]
    assert parents["1"] == "2"


def test_drop_at_root_row_uses_inverted_rows():
    # Sem a camada movida, a raiz (de cima para baixo na árvore) é: 2, 1.
    # Soltar na linha 1 põe a 5 entre o grupo 2 e a camada 1.
    order, parents = plan_layer_drop(_stack(), [5], None, 1)
    assert order == ["1", "5", "2", "3", "4"]
    assert parents["5"] is None


def test_drop_into_itself_is_rejected():
    assert plan_layer_drop(_stack(), [2], 2, 0) is None
