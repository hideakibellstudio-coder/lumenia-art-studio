"""Plugins embutidos do Lumenia: `system/` (workspace) e `panels/` (painéis).

O carregador fica em `ui/core/plugins`; um plugin nunca importa outro (Lei nº 1).
As pastas de agrupamento `system/` e `panels/` não têm `__init__.py` de
propósito: o `PluginManager` trata pasta com `__init__.py` como plugin.
"""
