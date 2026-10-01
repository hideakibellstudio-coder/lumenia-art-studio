"""LAYER_PROPERTIES — o que é uma propriedade de camada, numa tabela só (S2.2).

Até 2026-10-01 cada propriedade de camada (visível, travada, opacidade, modo de mesclagem,
trava de alfa, máscara de recorte) estava escrita à mão em oito lugares: o valor padrão da camada,
o instantâneo do histórico, a cópia ao duplicar, a leitura do registro salvo, o registro gravado, a
validação do arquivo, o envio ao motor a cada mudança e a releitura do motor ao confirmar uma
transação de histórico. A trava de alfa, por exemplo, aparecia em 34 arquivos; uma propriedade nova
exigia lembrar de todos e esquecer um deles perdia dado em silêncio (salvar sem a propriedade,
duplicar sem copiá-la).

Agora cada lugar percorre esta tabela. Uma propriedade nova entra aqui, com o seu valor padrão, o
método do motor que a recebe e se vai para o arquivo; o painel e o menu que a mostram continuam
sendo da propriedade. `tests/test_layer_property_registry.py` acrescenta uma propriedade só nesta
tabela e confere que cada lugar a trata.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .layer_blend_mode import LayerBlendMode

_SAME_AS_DEFAULT = object()


def _flag(value: Any) -> bool:
    return bool(value)


def _unit_interval(value: Any) -> float:
    return max(0.0, min(1.0, float(value)))


def _is_bool(value: Any) -> bool:
    return type(value) is bool


@dataclass(frozen=True)
class LayerProperty:
    name: str                                 # atributo da `LocalLayer` e chave do registro salvo
    default: Any
    coerce: Callable[[Any], Any]              # leva qualquer forma conhecida ao valor canônico
    engine_setter: Optional[str] = None       # método `(índice, valor)` do EngineBackend; None: só do documento
    live_key: Optional[str] = None            # chave em `backend.get_layer_info`; o padrão é `name`
    sync_name: Optional[str] = None           # o nome que `sync_backend_property` recebe; o padrão é `name`
    reason: Optional[str] = None              # motivo de `content_changed`; o padrão é `name`
    saved: bool = True                        # vai para o registro do arquivo `.lmn`
    duplicated: bool = True                   # a cópia da camada herda o valor
    in_constructor: bool = False              # nasce com a camada (o nome); a tabela não o inicializa
    group_default: Any = _SAME_AS_DEFAULT     # padrão de um grupo, quando difere
    validate: Callable[[Any], bool] = _is_bool
    is_flag: bool = False                     # booleano do registro: o serializador exige `bool` de verdade

    def default_for(self, is_group: bool) -> Any:
        return self.default if (not is_group or self.group_default is _SAME_AS_DEFAULT) else self.group_default

    def from_record(self, record: dict, is_group: bool) -> Any:
        return self.coerce(record.get(self.name, self.default_for(is_group)))

    @property
    def live(self) -> str:
        return self.live_key or self.name

    @property
    def sync(self) -> str:
        return self.sync_name or self.name

    @property
    def change_reason(self) -> str:
        return self.reason or self.name


LAYER_PROPERTIES: tuple[LayerProperty, ...] = (
    LayerProperty("name", "Camada", str, engine_setter="set_layer_name", duplicated=False, in_constructor=True,
                  validate=lambda value: isinstance(value, str)),
    LayerProperty("visible", True, _flag, engine_setter="set_layer_visibility", sync_name="visibility",
                  reason="visibility", is_flag=True),
    LayerProperty("locked", False, _flag, engine_setter="set_layer_lock", reason="lock", is_flag=True),
    LayerProperty("opacity", 1.0, _unit_interval, engine_setter="set_layer_opacity",
                  validate=lambda value: math.isfinite(float(value)) and 0 <= float(value) <= 1),
    LayerProperty("blend_mode", LayerBlendMode.NORMAL, LayerBlendMode.coerce, engine_setter="set_layer_blend_mode",
                  group_default=LayerBlendMode.PASS_THROUGH, validate=lambda value: True),
    LayerProperty("alpha_locked", False, _flag, engine_setter="set_layer_alpha_lock", reason="alpha_lock", is_flag=True),
    LayerProperty("clipping_mask", False, _flag, engine_setter="set_layer_clipping_mask", is_flag=True),
    LayerProperty("collapsed", False, _flag, saved=False, duplicated=False),
)

class LayerPropertyTable:
    """A tabela e as visões que os consumidores percorrem (montadas uma vez)."""

    def __init__(self, properties: tuple[LayerProperty, ...]) -> None:
        self.all = properties
        self.by_name = {prop.name: prop for prop in properties}
        self.by_sync_name = {prop.sync: prop for prop in properties}
        # As que o motor recebe, na ordem da tabela.
        self.engine = tuple(prop for prop in properties if prop.engine_setter)
        # As que o registro salvo traz além do nome (que a camada recebe ao nascer) e que a leitura reconstrói.
        self.record = tuple(prop for prop in properties if prop.saved and not prop.in_constructor)
        # As chaves booleanas do registro: o serializador recusa um valor que não seja `bool`.
        self.flag_keys = tuple(prop.name for prop in properties if prop.saved and prop.is_flag)


# Os consumidores leem `layer_properties.TABLE` a cada uso (não copiam o nome), o que deixa o teste
# de contrato trocar a tabela por uma com uma propriedade a mais.
TABLE = LayerPropertyTable(LAYER_PROPERTIES)


def apply_to_engine(backend: Any, index: int, prop: LayerProperty, value: Any) -> None:
    """Entrega o valor da propriedade ao motor, pelo método que a tabela nomeia."""
    getattr(backend, prop.engine_setter)(index, prop.coerce(value))
