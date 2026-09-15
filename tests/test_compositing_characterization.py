"""Teste de caracterizacao da composicao: fixa o resultado ATUAL em pixels.

Por que existe
--------------
O grafo do ARCcC-Navigator reporta `related_tests: []` tanto para `Compositor`
quanto para `PixelBuffer`: nenhuma aresta estatica liga a suite ao compositor.
A cobertura chega la por PyBind11, que o grafo nao atravessa — mas o efeito
pratico e o mesmo: **nada trava a saida da composicao**.

Isso importa agora porque `docs/COLOR_PIPELINE_ARCHITECTURE.md` secao 4 planeja
trocar o armazenamento de RGBA8 para RGBA16/RGBA32F. Trocar representacao de
pixel sem nada que fixe a saida atual e apostar que ninguem percebe uma borda
meio tom diferente. A ordem segura de um refactor de representacao e sempre:

    1. fixar o comportamento atual  <- este arquivo
    2. trocar a representacao
    3. os mesmos pinos continuam valendo

Este NAO e um teste de correcao. Ele nao afirma que a composicao esta certa —
afirma que ela nao MUDOU. Se um pino quebrar, a pergunta e "a mudanca era
intencional?", nao "quem errou?". Se era intencional, apague o pino e regrave.

Como os pinos sao gravados
--------------------------
Na primeira execucao o arquivo `tests/golden/compositing_golden.json` nao
existe: os hashes sao gravados e o teste e PULADO com um aviso. Rode de novo e
ele passa a comparar. **Confira e versione esse JSON** — ele e o pino.

Para regravar de proposito (mudanca aprovada):
    del tests\\golden\\compositing_golden.json
    python -m pytest tests/test_compositing_characterization.py
    python -m pytest tests/test_compositing_characterization.py
"""

import hashlib
import json
from pathlib import Path

import pytest

import aladyn_engine_native as native

GOLDEN_PATH = Path(__file__).parent / "golden" / "compositing_golden.json"

# engine/core/document/FilterLayer.hpp — mantenha sincronizado com o enum.
FILTER_TYPES = {
    "hue_sat": 0,
    "brightness_contrast": 1,
    "gaussian_blur": 2,
    "color_balance": 3,
    "sharpen_vignette": 4,
    "invert_threshold": 5,
    "pixelate": 6,
}

W = H = 16


def _digest(buffer: bytes) -> str:
    return hashlib.sha256(buffer).hexdigest()[:32]


def _gradient(width: int, height: int, phase: int = 0) -> bytes:
    """Padrao deterministico e sem simetria: expoe troca de canal e de linha."""
    out = bytearray()
    for y in range(height):
        for x in range(width):
            out += bytes((
                (x * 13 + phase) % 256,
                (y * 7 + phase * 3) % 256,
                (x * y + phase * 5) % 256,
                255 if (x + y + phase) % 5 else 128,
            ))
    return bytes(out)


def _scene() -> "native.PaintEngineFacade":
    """Cena fixa: tres camadas, opacidade parcial, blend nao-normal, mascara."""
    engine = native.PaintEngineFacade(W, H)
    engine.paste_rgba_buffer_on_active_layer(0, 0, W, H, _gradient(W, H, 0))

    second = engine.add_layer("segunda")
    engine.select_layer(second)
    engine.paste_rgba_buffer_on_active_layer(0, 0, W, H, _gradient(W, H, 4))
    engine.set_layer_opacity(second, 0.55)
    engine.set_layer_blend_mode(second, 2)

    third = engine.add_layer("terceira")
    engine.select_layer(third)
    engine.paste_rgba_buffer_on_active_layer(2, 3, 8, 6, _gradient(8, 6, 9))
    engine.set_layer_opacity(third, 0.8)
    engine.set_layer_clipping_mask(third, True)
    return engine


def _load_golden() -> dict:
    if GOLDEN_PATH.is_file():
        return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    return {}


def _record(pins: dict) -> None:
    GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN_PATH.write_text(json.dumps(pins, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _collect_pins() -> dict:
    pins = {"base": _digest(_scene().get_pixel_buffer())}
    for name, type_id in sorted(FILTER_TYPES.items()):
        engine = _scene()
        index = engine.add_filter_layer(f"f_{name}", type_id)
        engine.set_filter_params(index, [30.0, -20.0, 1.4, 8.0])
        pins[f"filter_{name}"] = _digest(engine.get_pixel_buffer())
    return pins


@pytest.fixture(scope="module")
def golden() -> dict:
    pins = _load_golden()
    if not pins:
        recorded = _collect_pins()
        _record(recorded)
        pytest.skip(
            f"Linha de base gravada em {GOLDEN_PATH} ({len(recorded)} pinos). "
            "Confira o arquivo, versione-o, e rode a suite de novo para que ele "
            "passe a comparar."
        )
    return pins


# --------------------------------------------------------------------------
# 1. Pinos de pixel: a saida nao pode mudar sem alguem decidir que muda.
# --------------------------------------------------------------------------

def test_composicao_base_nao_mudou(golden):
    assert _digest(_scene().get_pixel_buffer()) == golden["base"], (
        "A composicao da cena base mudou. Se foi intencional, apague "
        f"{GOLDEN_PATH.name} e regrave."
    )


@pytest.mark.parametrize("name,type_id", sorted(FILTER_TYPES.items()))
def test_cada_filtro_nao_mudou(golden, name, type_id):
    chave = f"filter_{name}"
    if chave not in golden:
        pytest.skip(f"Pino ausente para {chave}; regrave a linha de base.")
    engine = _scene()
    index = engine.add_filter_layer(f"f_{name}", type_id)
    engine.set_filter_params(index, [30.0, -20.0, 1.4, 8.0])
    assert _digest(engine.get_pixel_buffer()) == golden[chave], (
        f"O filtro '{name}' produz saida diferente da linha de base."
    )


# --------------------------------------------------------------------------
# 2. Invariantes: valem por construcao, independem da linha de base.
#    Continuam validos depois da migracao para 16 bits.
# --------------------------------------------------------------------------

def test_composicao_e_deterministica():
    """Mesma cena, duas composicoes: byte a byte igual.

    Pega corrida de dado entre threads no caminho paralelo do compositor, que
    e justamente onde SIMD de 16 bits vai mexer.
    """
    primeira = _scene().get_pixel_buffer()
    segunda = _scene().get_pixel_buffer()
    assert primeira == segunda


def test_camada_invisivel_equivale_a_camada_ausente():
    com_oculta = _scene()
    indice = com_oculta.add_layer("oculta")
    com_oculta.select_layer(indice)
    com_oculta.paste_rgba_buffer_on_active_layer(0, 0, W, H, _gradient(W, H, 11))
    com_oculta.set_layer_visibility(indice, False)
    assert com_oculta.get_pixel_buffer() == _scene().get_pixel_buffer()


def test_opacidade_zero_equivale_a_invisivel():
    zerada = _scene()
    i = zerada.add_layer("zerada")
    zerada.select_layer(i)
    zerada.paste_rgba_buffer_on_active_layer(0, 0, W, H, _gradient(W, H, 11))
    zerada.set_layer_opacity(i, 0.0)

    oculta = _scene()
    j = oculta.add_layer("zerada")
    oculta.select_layer(j)
    oculta.paste_rgba_buffer_on_active_layer(0, 0, W, H, _gradient(W, H, 11))
    oculta.set_layer_visibility(j, False)

    assert zerada.get_pixel_buffer() == oculta.get_pixel_buffer()


def test_buffer_tem_o_tamanho_declarado():
    """Pino de FORMATO. Quando RGBA16 entrar, este teste falha de proposito:
    e o lembrete de que o contrato do buffer exposto ao Python mudou, e de que
    `tests/test_buffer_contract.py` precisa ser revisto junto."""
    assert len(_scene().get_pixel_buffer()) == W * H * 4


def test_filtro_com_opacidade_zero_nao_altera_nada():
    """`FilterApplier::apply` retorna cedo quando a opacidade efetiva e <= 0.
    Este e o unico caminho do filtro que da para afirmar sem linha de base."""
    engine = _scene()
    esperado = engine.get_pixel_buffer()
    indice = engine.add_filter_layer("nulo", FILTER_TYPES["brightness_contrast"])
    engine.set_filter_params(indice, [50.0, 50.0, 2.0, 8.0])
    engine.set_layer_opacity(indice, 0.0)
    assert engine.get_pixel_buffer() == esperado
