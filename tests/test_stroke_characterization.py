"""
Caracterização do traço — fixa o comportamento ANTES de mexer no motor.
========================================================================
Estes testes não descrevem o comportamento correto. Descrevem o comportamento
ATUAL, para que uma mudança no motor prove que alterou só o que pretendia.
Mesmo papel que `test_compositing_characterization.py` fez na decomposição do
`FilterApplier`.

DOIS CAMINHOS DE TRAÇO
----------------------
O motor tem dois, e eles não compartilham a lógica do estabilizador:

  "raw"     begin_stroke_raw / update_stroke_raw / end_stroke_raw
            → StrokeOrchestrator, com realinhamento de pouso, catch-up de
              pen-up e afunilamento. `aladyn_stroke_mixin` usa ESTE sempre que
              o facade o expõe, e ele expõe. É por aqui que o artista desenha.

  "facade"  begin_stroke / update_stroke / end_stroke
            → PaintEngineFacade.cpp:281, um único desvio e nada mais.
              Fallback para builds nativas antigas.

Os dois desviam o estabilizador quando `lowLatency` está ligado, em lugares
diferentes: StrokeOrchestrator.cpp (updateStrokeRaw) e StrokeOrchestratorEnd.cpp
(endStrokeRaw) -- um arquivo só até a divisão de 2026-09-22 --, e
PaintEngineFacade.cpp. A regra agora mora num lugar só:
StrokeLatencyPolicy.hpp (usarAtalhoDeLatencia). Uma correção que toque só um dos arquivos
conserta só metade, e é por isso que os dois caminhos são medidos aqui.

O QUE A CORREÇÃO DEVE PRODUZIR
------------------------------
`DynamicStabilizer::update` já devolve o ponto bruto quando a estabilização é
~0 — "baixa latência" e "estabilizador em 0" são o mesmo botão escrito duas
vezes, e quando discordam o desvio vence. Trocando `ctx.lowLatency` por
`ctx.lowLatency && estabilização <= 0.5`:

    (latência ON,  estabilização 0)   → idêntico a hoje  (o atalho vale)
    (latência OFF, qualquer)          → idêntico a hoje  (nunca desviava)
    (latência ON,  estabilização > 0) → passa a ser igual a OFF

ORDEM DE USO
------------
  1. ANTES de mexer no C++, rode uma vez. Os pinos são gravados a partir do
     binário atual e os testes de `_respeita_o_estabilizador` e
     `_muda_o_traco_em_baixa_latencia` FALHAM — a falha é o bug escrito como
     teste.
  2. Depois de recompilar, rode de novo. Os pinos têm que continuar batendo
     (nada mais se moveu) e as falhas viram sucesso.

Apagar tests/golden/stroke_golden.json regrava tudo. Só faça isso quando a
mudança de comportamento for deliberada e você souber qual é.
"""

from __future__ import annotations

import hashlib
import json
import pathlib

import pytest

native = pytest.importorskip(
    "aladyn_engine_native", reason="módulo nativo não compilado neste ambiente"
)

GOLDEN = pathlib.Path(__file__).parent / "golden" / "stroke_golden.json"
W = H = 96

# "raw" primeiro: é o caminho que o aplicativo usa.
CAMINHOS = ("raw", "facade")

# Células cujo comportamento NÃO pode mudar com a correção.
CELULAS_FIXAS = [
    (caminho, baixa, estab)
    for caminho in CAMINHOS
    for baixa, estab in ((False, 0.0), (False, 50.0), (False, 98.0), (True, 0.0))
]

# Células hoje quebradas: a correção faz cada uma igualar sua correspondente
# com baixa latência desligada.
CELULAS_QUEBRADAS = [
    (caminho, estab) for caminho in CAMINHOS for estab in (50.0, 98.0)
]

# Amostras do traço: zigue-zague de amplitude fixa, onde o estabilizador atua
# com mais força. Timestamp explícito em toda amostra — sem isso o motor cai
# no relógio e o traço deixa de ser reproduzível.
AMOSTRAS = [
    (8.0 + i * 2.0, 48.0 + (14.0 if i % 2 else -14.0), 8.0 * (i + 1))
    for i in range(40)
]


def _evento(tipo, x: float, y: float, t: float):
    return native.PointerEvent(tipo, native.Point2D(x, y), 1.0, t)


def _tracar(caminho: str, baixa_latencia: bool, estabilizacao: float) -> bytes:
    eng = native.PaintEngineFacade(W, H)
    eng.set_render_options(
        low_latency=baixa_latencia, linear_gamma=False, deep_color=False
    )
    eng.get_stabilizer().set_stabilization_percentage(estabilizacao)

    perfil = eng.get_brush_profile()
    perfil.brush_size = 10.0
    perfil.opacity = 1.0

    if caminho == "raw":
        eng.begin_stroke_raw(8.0, 48.0, 1.0, 1.0)
        for x, y, t in AMOSTRAS:
            eng.update_stroke_raw(x, y, 1.0, t)
        eng.end_stroke_raw()
    elif caminho == "facade":
        eng.begin_stroke(_evento(native.PointerEventType.Press, 8.0, 48.0, 1.0))
        for x, y, t in AMOSTRAS:
            eng.update_stroke(_evento(native.PointerEventType.Move, x, y, t))
        ultimo_t = AMOSTRAS[-1][2]
        eng.end_stroke(_evento(native.PointerEventType.Release, 88.0, 48.0, ultimo_t + 8.0))
    else:
        raise ValueError(f"caminho desconhecido: {caminho!r}")

    return eng.get_pixel_buffer()


def _hash(buffer: bytes) -> str:
    return hashlib.sha256(bytes(buffer)).hexdigest()


def _rotulo(caminho: str, baixa_latencia: bool, estabilizacao: float) -> str:
    return f"{caminho}__latencia_{'on' if baixa_latencia else 'off'}__estab_{int(estabilizacao)}"


@pytest.fixture(scope="module")
def pinos() -> dict:
    """Carrega os pinos, completando os que faltarem.

    Completar em vez de só criar importa: quando uma célula nova entra na
    matriz, ela é gravada a partir do binário atual em vez de ser pulada em
    silêncio — um pino ausente que vira `skip` é um teste que não testa nada.
    """
    registrados = {}
    if GOLDEN.exists():
        registrados = json.loads(GOLDEN.read_text(encoding="utf-8"))

    faltando = {
        _rotulo(*celula): _hash(_tracar(*celula))
        for celula in CELULAS_FIXAS
        if _rotulo(*celula) not in registrados
    }
    if faltando:
        registrados.update(faltando)
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(
            json.dumps(registrados, indent=2, sort_keys=True), encoding="utf-8"
        )
    return registrados


# ── 1. Os pinos ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("celula", CELULAS_FIXAS, ids=lambda c: _rotulo(*c))
def test_celula_fixa_nao_mudou(pinos, celula):
    rotulo = _rotulo(*celula)
    assert _hash(_tracar(*celula)) == pinos[rotulo], (
        f"o traço em {rotulo} mudou. Se a mudança foi deliberada, diga qual é "
        f"e regrave o pino; se não, a alteração vazou para uma célula que "
        f"deveria ter ficado intacta."
    )


# ── 2. O comportamento que a correção tem que produzir ──────────────────────

@pytest.mark.parametrize(
    "caminho,estabilizacao", CELULAS_QUEBRADAS, ids=lambda v: str(v)
)
def test_baixa_latencia_respeita_o_estabilizador(caminho, estabilizacao):
    """Com estabilização pedida, os dois modos têm que traçar igual.

    FALHA antes da correção: o desvio por baixa latência ignora o
    estabilizador, então o traço com latência ligada sai idêntico ao de
    estabilização zero.
    """
    com_latencia = _hash(_tracar(caminho, True, estabilizacao))
    sem_latencia = _hash(_tracar(caminho, False, estabilizacao))
    assert com_latencia == sem_latencia, (
        f"no caminho '{caminho}', com estabilização {estabilizacao}%, a baixa "
        f"latência produz um traço diferente — ela ainda desvia o estabilizador"
    )


@pytest.mark.parametrize("caminho", CAMINHOS)
def test_estabilizador_muda_o_traco_em_baixa_latencia(caminho):
    """O sintoma que o usuário relata: mover o slider não muda nada."""
    inerte = _hash(_tracar(caminho, True, 0.0))
    ativo = _hash(_tracar(caminho, True, 98.0))
    assert inerte != ativo, (
        f"no caminho '{caminho}', com baixa latência ligada, 0% e 98% de "
        f"estabilização produzem o mesmo traço — o slider não tem efeito nenhum"
    )


# ── 3. Invariantes que valem nos dois lados da mudança ──────────────────────

@pytest.mark.parametrize("caminho", CAMINHOS)
@pytest.mark.parametrize("baixa_latencia", [False, True])
def test_traco_e_deterministico(caminho, baixa_latencia):
    """Sem isto, todo hash acima seria ruído."""
    primeiro = _hash(_tracar(caminho, baixa_latencia, 60.0))
    segundo = _hash(_tracar(caminho, baixa_latencia, 60.0))
    assert primeiro == segundo, "o mesmo traço produziu buffers diferentes"


def test_com_estabilizacao_zero_o_facade_coincide():
    """No caminho 'facade' há um único desvio, e `DynamicStabilizer::update` já
    devolve o ponto bruto quando a estabilização é ~0. Logo os dois modos
    coincidem — é a prova de que, ali, "baixa latência" e "estabilizador em 0"
    são mesmo o mesmo botão."""
    assert _hash(_tracar("facade", True, 0.0)) == _hash(_tracar("facade", False, 0.0))


def test_no_raw_a_baixa_latencia_desliga_mais_que_o_estabilizador():
    """O 'raw' NÃO coincide com estabilização zero, e isso não é bug.

    Escrevi este teste ao contrário na primeira versão, afirmando que os dois
    modos deveriam coincidir. A medição mostrou que não coincidem: além do
    estabilizador, `lowLatency` gateia o catch-up e o afunilamento do pen-up
    (StrokeOrchestratorEnd.cpp, endStrokeRaw), e esses disparam mesmo com estabilização
    zero, porque `getLastMovementDelta()` continua não-nulo.

    "Baixa latência" são duas features empacotadas numa flag: pular o
    estabilizador e pular o afunilamento. A correção desempacota só a primeira.
    Quem liga a suavização recebe o pipeline estabilizado inteiro, catch-up
    incluído — sem ele o traço pára atrás de onde a caneta levantou. O
    afunilamento continua tendo seu próprio checkbox para quem não o quiser.

    Este teste passa nos dois lados da mudança: a célula (latência ON, estab 0)
    está pinada para não se mover.
    """
    assert _hash(_tracar("raw", True, 0.0)) != _hash(_tracar("raw", False, 0.0)), (
        "os dois modos coincidiram com estabilização zero no caminho 'raw' — "
        "o afunilamento do pen-up deixou de ser gateado pela baixa latência, "
        "o que é uma mudança de comportamento não pedida"
    )


@pytest.mark.parametrize("celula", CELULAS_FIXAS, ids=lambda c: _rotulo(*c))
def test_buffer_tem_o_tamanho_declarado(celula):
    """Falha de propósito quando o RGBA16 chegar — aí os pinos precisam ser revistos."""
    assert len(_tracar(*celula)) == W * H * 4


@pytest.mark.parametrize("caminho", CAMINHOS)
def test_o_traco_deixa_tinta(caminho):
    """Uma caracterização de um traço vazio não caracterizaria nada."""
    buffer = _tracar(caminho, False, 40.0)
    assert sum(1 for alfa in buffer[3::4] if alfa > 0) > 100


def test_os_dois_caminhos_produzem_tracos_distintos():
    """Guarda contra um erro meu: se 'raw' e 'facade' dessem o mesmo resultado,
    seria sinal de que o teste não está exercitando os dois de fato."""
    assert _hash(_tracar("raw", False, 98.0)) != _hash(_tracar("facade", False, 98.0)), (
        "os dois caminhos produziram o mesmo traço — provavelmente o "
        "'raw' não está sendo exercitado como se pensa"
    )
