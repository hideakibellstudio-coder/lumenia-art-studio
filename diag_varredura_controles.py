"""Varredura: a interface e o motor concordam sobre os parametros de pincel?

Nao altera nada. Escreve pelo caminho real da interface, le de volta direto da
struct nativa e compara.

Os casos vem de `ui/engine_backends/brush_param_table.TABELA` — a mesma tabela
que o programa usa. Um diagnostico com lista propria seria a quinta lista
paralela, e foi justamente isso que criou os bugs que ele procura.

Tres perguntas:

  A. Todo parametro DECLARADO aterrissa no BrushProfile em C++?
  B. Todo par que a interface ja usou e que NAO existe e recusado alto?
  C. O estabilizador esta desligado por baixa latencia?

    cd "Z:\\DESENVOLVIMENTO\\+ LUMENIA CLEAN\\Lumenia"
    python diag_varredura_controles.py
"""
from __future__ import annotations

import aladyn_engine_native as native
from ui.engine_backends.aladyn import AladynBackend
from ui.engine_backends.brush_param_table import TABELA, alvo_nativo

LARG = 78

# Valor de teste por conversor, escolhido para diferir de qualquer padrao.
VALORES = {
    "para_float": 0.4271,
    "para_int": 7,
    "para_bool": True,
    "para_blend_mode": 2,
}

# Pares que a interface ou os presets ja usaram e que o motor nao tem.
# Depois da tabela unica, cada um destes deve levantar KeyError em vez de
# ser descartado em silencio. Estao aqui como regressao: se um deles voltar
# a ser aceito, alguem reabriu o buraco.
REMOVIDOS = [
    ("root", "scatter_radius", "o motor so tem scatterCount"),
    ("dynamics", "jitter_size", "o campo mora em BrushTip, nao em 'dynamics'"),
    ("dynamics", "jitter_angle", "idem"),
    ("dynamics", "jitter_position", "idem"),
    ("dynamics", "jitter_opacity", "nao existe em lugar nenhum do motor"),
]


def parte_a(backend) -> list[str]:
    print("A. Todo parametro declarado aterrissa no motor?")
    print("-" * LARG)
    perfil = backend._facade.get_brush_profile()
    problemas: list[str] = []

    for linha in TABELA:
        rotulo = f"{linha.grupo or 'root'}.{linha.atributo}"
        bruto = VALORES[linha.para_motor.__name__]
        try:
            backend.set_brush_param(linha.grupo or "root", linha.atributo, bruto)
        except Exception as exc:
            msg = f"{type(exc).__name__}: {str(exc).splitlines()[0]}"
            print(f">> {rotulo:<38} EXCECAO  {msg}")
            problemas.append(f"{linha.chave}: {msg}")
            continue

        esperado = linha.para_preset(linha.para_motor(bruto, native))
        lido = linha.para_preset(getattr(alvo_nativo(perfil, linha.grupo), linha.atributo))
        igual = lido == esperado or (
            isinstance(esperado, float) and abs(float(lido) - esperado) < 1e-6
        )
        if igual:
            print(f"   {rotulo:<38} ok       (preset: {linha.chave})")
        else:
            print(f">> {rotulo:<38} DIVERGE  escrito {esperado!r}, lido {lido!r}")
            problemas.append(f"{linha.chave}: escrito {esperado!r}, lido {lido!r}")
    return problemas


def parte_b(backend) -> list[str]:
    print()
    print("B. Os pares que o motor nao tem sao recusados alto?")
    print("-" * LARG)
    problemas: list[str] = []
    for grupo, param, motivo in REMOVIDOS:
        rotulo = f"{grupo}.{param}"
        try:
            backend.set_brush_param(grupo, param, 0.5)
        except KeyError:
            print(f"   {rotulo:<38} recusado ({motivo})")
        except Exception as exc:
            print(f">> {rotulo:<38} ERRO ERRADO  {type(exc).__name__}")
            problemas.append(f"{rotulo}: levantou {type(exc).__name__}, esperado KeyError")
        else:
            print(f">> {rotulo:<38} ACEITO EM SILENCIO — o buraco voltou")
            problemas.append(f"{rotulo}: aceito sem erro")
    return problemas


def _evento(tipo, x: float, y: float, t: float):
    return native.PointerEvent(tipo, native.Point2D(x, y), 1.0, t)


def _tracar(percentual: float, baixa_latencia: bool) -> bytes:
    eng = native.PaintEngineFacade(96, 96)
    eng.set_render_options(
        low_latency=baixa_latencia, linear_gamma=False, deep_color=False
    )
    eng.get_stabilizer().set_stabilization_percentage(percentual)
    prof = eng.get_brush_profile()
    prof.brush_size = 10.0
    prof.opacity = 1.0
    t = 0.0
    eng.begin_stroke(_evento(native.PointerEventType.Press, 8.0, 48.0, t))
    for i in range(40):
        t += 8.0
        eng.update_stroke(
            _evento(
                native.PointerEventType.Move,
                8.0 + i * 2.0,
                48.0 + (14.0 if i % 2 else -14.0),
                t,
            )
        )
    eng.end_stroke(_evento(native.PointerEventType.Release, 88.0, 48.0, t + 8.0))
    return eng.get_pixel_buffer()


def parte_c(backend) -> bool:
    print()
    print("C. O estabilizador sobrevive a baixa latencia?")
    print("-" * LARG)
    medidas = {}
    for baixa in (False, True):
        a, b = _tracar(0.0, baixa), _tracar(98.0, baixa)
        medidas[baixa] = sum(1 for x, y in zip(a, b) if x != y)
        rotulo = "baixa latencia LIGADA " if baixa else "baixa latencia DESLIGADA"
        estado = (
            "traco IDENTICO — estabilizador ignorado"
            if medidas[baixa] == 0
            else f"{medidas[baixa]} bytes diferentes — estabilizador atua"
        )
        print(f"{'>>' if medidas[baixa] == 0 else '  '} {rotulo}  0% vs 98%:  {estado}")

    print()
    print("   Opcoes de render com que o backend nasce:")
    for chave, valor in backend.get_render_options().items():
        print(f"{'>>' if chave == 'low_latency' and valor else '  '} {chave:<16} = {valor}")
    return medidas[True] == 0 and medidas[False] > 0


print("=" * LARG)
backend = AladynBackend()
if not backend.available:
    raise SystemExit("modulo nativo indisponivel")

problemas = parte_a(backend) + parte_b(backend)
estabilizador_inerte = parte_c(backend)

print()
print("=" * LARG)
print("RESUMO")
print("-" * LARG)
if problemas:
    print(f"  {len(problemas)} problemas de contrato:")
    for p in problemas:
        print(f"    - {p}")
else:
    print(f"  {len(TABELA)} parametros declarados: todos aterrissam no motor.")
    print(f"  {len(REMOVIDOS)} pares obsoletos: todos recusados alto.")
print()
if estabilizador_inerte:
    print("  PENDENTE: o estabilizador so tem efeito com baixa latencia")
    print("  DESLIGADA, e o padrao do AladynBackend e low_latency=True.")
    print("  Nao e bug de ligacao — e escolha de projeto do StrokeOrchestrator.")
    print("  Decisao em aberto: esconder o controle nesse modo, aplicar o")
    print("  estabilizador mesmo em baixa latencia, ou mudar o padrao.")
else:
    print("  O estabilizador nao depende da baixa latencia neste build.")
print("=" * LARG)
