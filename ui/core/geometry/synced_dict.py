"""SyncedDict -- dict que sincroniza automaticamente com o motor nativo a
cada mutacao.

Contexto (panorama pos-C5, item P1 #2): `GeometryToolController.guide_state`
e `sym_state` sao dicts simples mutados de fora da classe controladora --
principalmente por `plugins/ui/geometry_plugin/panel.py` (~30 atribuicoes em
`_sync_to_render_widget`) -- cada mutacao exigindo uma chamada manual e
subsequente a `sync_guides_to_engine`/`sync_symmetry_to_engine`. Esse padrao
e fragil: nada impede uma nova mutacao esquecer o sync correspondente.

`SyncedDict` fecha esse buraco: qualquer escrita (`__setitem__`,
`__delitem__`, `update`) dispara automaticamente o callback `on_change`
passado no construtor, entao o sync deixa de ser responsabilidade de quem
muta o dict. Casos de mutacao em lote (ex.: `_sync_to_render_widget`, que
escreve ~15 chaves seguidas) usam o context manager `batch()` para suprimir
o callback durante o bloco e disparar uma unica vez ao sair.

Duas armadilhas foram verificadas antes desta implementacao:

  - `load_document_state` substitui o conteudo inteiro do dict (vindo de um
    controller descartavel usado so por seus valores-padrao). Reatribuir
    `self.guide_state = defaults.guide_state` trocaria a instancia por um
    SyncedDict cujo `on_change` aponta para o `sync_*` do controller ERRADO
    (`defaults`, nao `self`). `reset()` evita isso: substitui o conteudo
    interno mantendo a identidade do wrapper e o callback ja vinculado.

  - `_store_document_state` faz `copy.deepcopy(state)`. Sem tratamento,
    `deepcopy` tentaria copiar recursivamente o metodo vinculado `on_change`
    (e portanto o `GeometryToolController` inteiro, QWidget incluso).
    `__deepcopy__` evita isso devolvendo uma copia profunda so de `_data`,
    como um dict comum.
"""

from __future__ import annotations

import copy
from collections.abc import MutableMapping
from contextlib import contextmanager
from typing import Any, Callable, Iterator


class SyncedDict(MutableMapping):
    """Dict que chama `on_change()` a cada mutacao, com suporte a lote."""

    def __init__(self, initial: dict[str, Any], on_change: Callable[[], None]):
        self._data: dict[str, Any] = dict(initial)
        self._on_change = on_change
        self._suspended = 0

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._notify()

    def __delitem__(self, key: str) -> None:
        del self._data[key]
        self._notify()

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return f"SyncedDict({self._data!r})"

    def _notify(self) -> None:
        if self._suspended == 0:
            self._on_change()

    def update(self, other=(), sync: bool = True, **kwargs) -> None:
        """Como `dict.update`, mas com um unico `on_change` no final (em vez
        de um por chave, que o mixin de MutableMapping faria por delegar a
        `__setitem__`). `sync=False` suprime o callback -- usado por quem
        ja vai chamar o sync explicitamente depois (ex.: durante o load de
        documento, onde o sync final e feito uma vez so, fora do update)."""
        with self.batch(sync=sync):
            self._data.update(other, **kwargs)

    def reset(self, other: dict[str, Any], sync: bool = True) -> None:
        """Substitui todo o conteudo preservando a identidade do wrapper e o
        `on_change` ja vinculado -- ver nota de `load_document_state` no
        docstring do modulo. `sync=False` suprime o callback."""
        self._data = dict(other)
        if sync and self._suspended == 0:
            self._on_change()

    @contextmanager
    def batch(self, sync: bool = True):
        """Suspende `on_change` por chave durante o bloco; dispara uma unica
        vez ao sair (a menos que `sync=False`, ou que o batch esteja
        aninhado dentro de outro -- so o batch mais externo dispara)."""
        self._suspended += 1
        try:
            yield self
        finally:
            self._suspended -= 1
            if sync and self._suspended == 0:
                self._on_change()

    def __deepcopy__(self, memo: dict) -> dict:
        """`deepcopy(synced_dict)` devolve um dict comum com copia profunda
        de `_data` -- nunca tenta copiar `on_change` (metodo vinculado ao
        controller inteiro). Ver nota no docstring do modulo."""
        return copy.deepcopy(self._data, memo)
