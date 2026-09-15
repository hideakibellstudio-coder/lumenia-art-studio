"""O preset guardado sobrescreve o slider ao trocar de contexto de documento?

Hipotese, vinda da leitura de aladyn_mdi_mixin.py::set_active_document_context:

    self._facade = self._doc_facades[uid]
    ...
    if hasattr(self, "_last_brush_preset") and self._last_brush_preset:
        self.apply_brush_preset_dict(self._last_brush_preset)

`apply_brush_preset_dict` reescreve o estabilizador. Mas `_last_brush_preset` so
e atualizado por ele proprio — o slider grava direto no facade via
`set_stabilizer_weight` e NAO atualiza o preset guardado. Entao todo toque no
contexto de documento restaura o valor antigo por cima do que o usuario escolheu.

    cd "Z:\\DESENVOLVIMENTO\\+ LUMENIA CLEAN\\Lumenia"
    python diag_estabilizador2.py
"""
from ui.engine_backends.aladyn import AladynBackend

PRESET = 40.0     # o que o preset carregado traz
SLIDER = 95.0     # o que o usuario escolhe no slider


def ler(backend) -> float:
    return float(backend._facade.get_stabilizer().get_stabilization_percentage())


print("=" * 66)
b = AladynBackend()
if not b.available:
    raise SystemExit("backend nativo indisponivel")

b.set_active_document_context("doc-A", 64, 64)
print(f"  contexto 'doc-A' criado            estabilizador = {ler(b)}")

# 1. simula o carregamento de um preset de pincel (o que popula _last_brush_preset)
b.apply_brush_preset_dict({"stabilizer_weight": PRESET / 100.0, "brush_size": 12.0})
print(f"  preset aplicado ({PRESET}%)             estabilizador = {ler(b)}")
print(f"     _last_brush_preset guardado     = {getattr(b, '_last_brush_preset', None)}")

# 2. simula o usuario movendo o slider
b.set_stabilizer_weight(SLIDER / 100.0)
apos_slider = ler(b)
print(f"\n  slider movido para {SLIDER}%          estabilizador = {apos_slider}")
print(f"     _last_brush_preset AINDA        = "
      f"{getattr(b, '_last_brush_preset', {}).get('stabilizer_weight')}")
if abs(apos_slider - SLIDER) > 0.01:
    print("     >>> o slider nem chegou ao motor — outra causa <<<")
    raise SystemExit(0)
print("     o slider chegou ao motor. Ate aqui, tudo certo.")

# 3. qualquer toque no contexto de documento
b.set_active_document_context("doc-A", 64, 64)          # mesmo doc: re-ativacao
mesmo_doc = ler(b)
print(f"\n  re-ativando o MESMO doc            estabilizador = {mesmo_doc}")

b.set_active_document_context("doc-B", 64, 64)          # novo doc / nova aba
b.set_active_document_context("doc-A", 64, 64)          # e de volta
troca_ida_volta = ler(b)
print(f"  troca doc-B e volta para doc-A     estabilizador = {troca_ida_volta}")

print("\n" + "-" * 66)
stomp_mesmo = abs(mesmo_doc - PRESET) < 0.01
stomp_troca = abs(troca_ida_volta - PRESET) < 0.01
if stomp_mesmo or stomp_troca:
    onde = []
    if stomp_mesmo:
        onde.append("re-ativar o mesmo documento")
    if stomp_troca:
        onde.append("trocar de documento")
    print("  CONFIRMADO: o preset guardado sobrescreve a escolha do usuario.")
    print(f"  Basta {' ou '.join(onde)} para o valor voltar a {PRESET}%.")
    print("\n  Causa: `set_stabilizer_weight` grava no facade mas nao atualiza")
    print("  `_last_brush_preset`, que e reaplicado por")
    print("  aladyn_mdi_mixin.py::set_active_document_context.")
else:
    print("  A hipotese NAO se confirma: o valor sobreviveu as trocas.")
    print("  A causa esta em outro lugar — provavelmente na UI (o slider nao")
    print("  chama o handler) ou noutro ponto que reaplica preset.")
print("=" * 66)
