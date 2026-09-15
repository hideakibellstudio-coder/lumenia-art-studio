"""O motor de fato USA o estabilizador? Nao altera nada.

Itens 1 e 2 (persistencia do valor) ja passaram: `set_stabilization_percentage`
grava no motor e `get_stabilizer()` devolve referencia, nao copia. Falta a
pergunta que importa: com o valor gravado, o TRACO sai diferente?

    cd "Z:\\DESENVOLVIMENTO\\+ LUMENIA CLEAN\\Lumenia"
    python diag_estabilizador.py
"""
import aladyn_engine_native as native

W = H = 96
PRESS = native.PointerEventType.Press
MOVE = native.PointerEventType.Move
RELEASE = native.PointerEventType.Release


def _evento(tipo, x: float, y: float, t: float) -> "native.PointerEvent":
    # A assinatura real aceita ainda tilt_x, tilt_y e twist — ausentes do .pyi.
    # Deixados no padrao: o alvo aqui e o estabilizador, nao a dinamica da caneta.
    return native.PointerEvent(tipo, native.Point2D(x, y), 1.0, t)


def _tracar(percentual: float) -> bytes:
    """Zigue-zague agressivo: e onde o estabilizador atua com mais forca."""
    eng = native.PaintEngineFacade(W, H)
    eng.get_stabilizer().set_stabilization_percentage(percentual)

    prof = eng.get_brush_profile()
    prof.brush_size = 10.0
    prof.opacity = 1.0

    t = 0.0
    eng.begin_stroke(_evento(PRESS, 8.0, 48.0, t))
    for i in range(40):
        t += 8.0                                  # ms entre amostras
        x = 8.0 + i * 2.0
        y = 48.0 + (14.0 if i % 2 else -14.0)     # serrilha de amplitude fixa
        eng.update_stroke(_evento(MOVE, x, y, t))
    eng.end_stroke(_evento(RELEASE, 8.0 + 40 * 2.0, 48.0, t + 8.0))
    return eng.get_pixel_buffer()


print("=" * 62)
print("O traco desenhado muda com o estabilizador?\n")

amostras = {}
for pct in (0.0, 50.0, 95.0):
    try:
        amostras[pct] = _tracar(pct)
        tinta = sum(1 for a in amostras[pct][3::4] if a > 0)
        print(f"  estabilizador {pct:5.1f}%  ->  {tinta} pixels com tinta")
    except Exception as exc:
        print(f"  estabilizador {pct:5.1f}%  ->  ERRO {type(exc).__name__}: {exc}")

print()
if len(amostras) == 3:
    a, b, c = amostras[0.0], amostras[50.0], amostras[95.0]
    d_0_95 = sum(1 for x, y in zip(a, c) if x != y)
    d_0_50 = sum(1 for x, y in zip(a, b) if x != y)
    print(f"  bytes diferentes entre  0% e 95% : {d_0_95}")
    print(f"  bytes diferentes entre  0% e 50% : {d_0_50}")
    print()
    if d_0_95 == 0:
        print("  >>> TRACO IDENTICO com 0% e 95%.")
        print("  >>> O motor IGNORA o estabilizador. A ruptura esta no")
        print("  >>> pipeline do traco (StrokeOrchestrator / DynamicStabilizer),")
        print("  >>> NAO na ligacao UI->motor, que ja provamos intacta.")
    elif d_0_50 == 0 and d_0_95 > 0:
        print("  >>> So o extremo alto muda: o parametro chega, mas a curva de")
        print("  >>> resposta esta achatada. Comportamento degradado, nao morto.")
    else:
        print("  >>> O motor RESPONDE ao estabilizador nos tres niveis.")
        print("  >>> A cadeia C++ esta viva. O problema esta na UI:")
        print("  >>> o slider nao chama o handler, ou chama com valor errado.")
        print("  >>> Proximo passo: instrumentar panel_engine_bridge.py:54.")
print("=" * 62)
