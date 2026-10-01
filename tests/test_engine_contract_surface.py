"""O contrato do motor só tem o que a interface chama (ARCcC 4.4.9, S2.3).

O `EngineBackend` espelha a facade do motor, e a facade tem uma capacidade para cada coisa que o motor
sabe fazer. Um método do contrato que nenhum código de produção chama é um mecanismo sem entrega: custa
uma declaração no contrato, outra no `Protocol` do papel e uma implementação na ponte, para uma
possibilidade que não aconteceu. Em 2026-10-01 eram 19 de 178 (os apelidos `*_raw` do traço, os
leitores de contagem do histórico, `flip_active_layer`, `flood_fill` que só o `fill_area` usava...);
saíram, e este teste barra a volta. Precisa de um deles? Chame-o de onde for usado, junto da feature.
"""

from __future__ import annotations

from tests.arccc_engine_roles import contract_methods, production_texts, unused_methods


def test_every_contract_method_has_a_caller_in_production():
    methods = contract_methods()
    unused = unused_methods(methods, production_texts())
    assert unused == [], (
        f"{len(unused)} método(s) do EngineBackend que nenhum código de ui/ chama: {unused}. "
        "Remova do contrato, do Protocol do papel e da ponte; ou ligue a quem os usa."
    )


def test_the_detector_sees_a_dotted_call_and_a_name_in_a_table_and_misses_neither():
    texts = {
        "ui/a.py": "backend.paint(1)\n",
        "ui/b.py": 'ENGINE_SETTERS = ("set_x", \'set_y\')\n',
    }
    assert unused_methods(["paint", "set_x", "set_y", "forgotten"], texts) == ["forgotten"]


def test_a_name_that_only_prefixes_another_does_not_count_as_a_caller():
    texts = {"ui/a.py": "backend.paint_stroke(1)\nbackend.undo_all()\n"}
    assert unused_methods(["paint", "undo"], texts) == ["paint", "undo"]


def test_the_bridge_and_the_contract_files_do_not_count_as_callers():
    texts = production_texts()
    assert not [rel for rel in texts if rel.startswith("ui/infrastructure/bridge_client/")]
    assert "ui/core/engine/backend.py" not in texts
    assert "ui/core/engine/backend_protocols.py" not in texts
    assert "ui/core/engine/backend_protocols_selection.py" not in texts
