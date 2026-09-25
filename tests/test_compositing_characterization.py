"""Teste de caracterizacao da composicao: fixa o resultado ATUAL em pixels.

Por que existe
--------------
O grafo do ARCcC-Navigator reporta `related_tests: []` tanto para `Compositor`
quanto para `PixelBuffer`: nenhuma aresta estatica liga a suite ao compositor.
A cobertura chega la por PyBind11, que o grafo nao atravessa — mas o efeito
pratico e o mesmo: **nada trava a saida da composicao**.

Isso importa agora porque `docs/05-visao-e-futuro/02-pipeline-de-cor-16bit.md` secao 4 planeja
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

# engine/core/document/filters/FilterSettings.hpp — mantenha sincronizado com o enum.
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


# --------------------------------------------------------------------------
# 3. Auditoria Rodada 2: R2-1 (Mascara), R2-2 (Grupo Blend), R2-3 (Filtro Area)
# --------------------------------------------------------------------------

def test_mascara_recorte_nao_migra_com_opacidade_zero_da_base():
    """R2-1 / R2-5: Máscara não pode migrar para a camada inferior quando a base vai a opacidade 0."""
    canvas_size = 512
    engine = native.PaintEngineFacade(canvas_size, canvas_size)

    # Camada 0: verde em 150..250
    c0 = engine.get_active_layer_index()
    green_buf = bytes([0, 255, 0, 255] * (100 * 100))
    engine.paste_rgba_buffer_on_active_layer(150, 150, 100, 100, green_buf)

    # Camada base: vermelho em 100..200
    base = engine.add_layer("base")
    engine.select_layer(base)
    red_buf = bytes([255, 0, 0, 255] * (100 * 100))
    engine.paste_rgba_buffer_on_active_layer(100, 100, 100, 100, red_buf)

    # Camada mask: azul cobrindo o canvas, recortada
    mask = engine.add_layer("mask")
    engine.select_layer(mask)
    blue_buf = bytes([0, 0, 255, 255] * (canvas_size * canvas_size))
    engine.paste_rgba_buffer_on_active_layer(0, 0, canvas_size, canvas_size, blue_buf)
    engine.set_layer_clipping_mask(mask, True)

    # Ponto de observacao (220, 220): fora do vermelho, dentro do verde
    idx = (220 * canvas_size + 220) * 4
    buf_before = engine.get_pixel_buffer()
    # Antes: a mascara corta contra o vermelho; em (220, 220) ve-se o verde da camada 0
    assert buf_before[idx] == 0 and buf_before[idx + 1] == 255 and buf_before[idx + 2] == 0

    # Zerar a opacidade da base: a mascara deve ocultar-se junto, NUNCA migrar para camada 0
    engine.set_layer_opacity(base, 0.0)
    buf_after = engine.get_pixel_buffer()
    # Em (220, 220), continua verde (a mascara nao recortou contra a camada 0)
    assert buf_after[idx + 2] != 255, "A máscara migrou indevidamente para a camada 0 ao zerar opacidade da base"
    assert buf_after[idx] == 0 and buf_after[idx + 1] == 255 and buf_after[idx + 2] == 0


@pytest.mark.parametrize("radius", [12, 40, 100])
def test_composicao_parcial_equivale_a_completa_com_blur_raio_grande(radius):
    """R2-3: Composição por região deve ser idêntica à composição completa com filtros de área."""
    canvas_size = 512
    # 1. Parcial (set_layer_opacity dispara compositeRegion)
    e_part = native.PaintEngineFacade(canvas_size, canvas_size)
    sq = e_part.add_layer("square")
    e_part.select_layer(sq)
    black_sq = bytes([0, 0, 0, 255] * (64 * 64))
    e_part.paste_rgba_buffer_on_active_layer(100, 100, 64, 64, black_sq)
    f1 = e_part.add_filter_layer("blur", FILTER_TYPES["gaussian_blur"])
    e_part.set_filter_params(f1, [float(radius)])
    e_part.set_layer_opacity(sq, 0.5)
    buf_part = e_part.get_pixel_buffer()

    # 2. Completa (criada com opacity 0.5 e composta inteira no set_filter_params)
    e_comp = native.PaintEngineFacade(canvas_size, canvas_size)
    sq2 = e_comp.add_layer("square")
    e_comp.select_layer(sq2)
    e_comp.paste_rgba_buffer_on_active_layer(100, 100, 64, 64, black_sq)
    e_comp.set_layer_opacity(sq2, 0.5)
    f2 = e_comp.add_filter_layer("blur", FILTER_TYPES["gaussian_blur"])
    e_comp.set_filter_params(f2, [float(radius)])
    buf_comp = e_comp.get_pixel_buffer()

    assert _digest(buf_part) == _digest(buf_comp), (
        f"Composição parcial e completa divergiram com blur de raio {radius}"
    )


def test_blend_mode_de_grupo_afeta_composicao_em_tempo_real():
    """R2-2: Blend mode de grupo deve afetar o canvas em tempo real (não apenas ao achatar)."""
    canvas_size = 256
    # Camada de baixo: amarelo (255, 255, 0)
    # Grupo: contém uma camada ciano (0, 255, 255)
    # Com Blend Normal / PassThrough: Ciano cobre Amarelo -> Ciano
    # Com Blend Multiply: Ciano (0, 255, 255) * Amarelo (255, 255, 0) -> Verde (0, 255, 0)

    # Cena A: Grupo em PassThrough
    e_pass = native.PaintEngineFacade(canvas_size, canvas_size)
    yellow_buf = bytes([255, 255, 0, 255] * (canvas_size * canvas_size))
    e_pass.paste_rgba_buffer_on_active_layer(0, 0, canvas_size, canvas_size, yellow_buf)

    grp_pass = e_pass.add_group("grupo")
    c_pass = e_pass.add_layer("filho")
    e_pass.set_layer_parents([ -1, -1, grp_pass ]) # c_pass parent is grp_pass
    e_pass.select_layer(c_pass)
    cyan_buf = bytes([0, 255, 255, 255] * (canvas_size * canvas_size))
    e_pass.paste_rgba_buffer_on_active_layer(0, 0, canvas_size, canvas_size, cyan_buf)
    e_pass.set_layer_blend_mode(grp_pass, 7) # PassThrough
    buf_pass = e_pass.get_pixel_buffer()

    # Cena B: Grupo em Multiply (1)
    e_mult = native.PaintEngineFacade(canvas_size, canvas_size)
    e_mult.paste_rgba_buffer_on_active_layer(0, 0, canvas_size, canvas_size, yellow_buf)

    grp_mult = e_mult.add_group("grupo")
    c_mult = e_mult.add_layer("filho")
    e_mult.set_layer_parents([ -1, -1, grp_mult ])
    e_mult.select_layer(c_mult)
    e_mult.paste_rgba_buffer_on_active_layer(0, 0, canvas_size, canvas_size, cyan_buf)
    e_mult.set_layer_blend_mode(grp_mult, 1) # Multiply
    buf_mult = e_mult.get_pixel_buffer()

    # Os hashes devem diferir e o pixel com Multiply deve ser verde
    assert _digest(buf_pass) != _digest(buf_mult), "Blend mode do grupo não alterou o canvas em tempo real"
    idx = (100 * canvas_size + 100) * 4
    assert buf_mult[idx] == 0, f"Canal R esperado 0, obtido {buf_mult[idx]}"
    assert buf_mult[idx + 1] == 255, f"Canal G esperado 255, obtido {buf_mult[idx + 1]}"
    assert buf_mult[idx + 2] == 0, f"Canal B esperado 0, obtido {buf_mult[idx + 2]}"

