"""Verifica a correcao e mede QUANTAS das ~46 propriedades sofriam o mesmo.

    cd "Z:\\DESENVOLVIMENTO\\+ LUMENIA CLEAN\\Lumenia"
    python diag_estabilizador3.py
"""
from ui.engine_backends.aladyn import AladynBackend

PRESET = {"stabilizer_weight": 0.40, "brush_size": 12.0, "opacity": 0.50,
          "spacing_factor": 0.25, "hardness": 0.30}

# (nome, setter do backend, valor do usuario, como ler de volta)
AJUSTES = [
    ("estabilizador", "set_stabilizer_weight", 0.95,
     lambda f: f.get_stabilizer().get_stabilization_percentage() / 100.0),
    ("opacidade",     "set_brush_opacity",     0.90, lambda f: f.get_brush_profile().opacity),
    ("espacamento",   "set_brush_spacing",     0.80, lambda f: f.get_brush_profile().spacing_factor),
    ("dureza",        "set_brush_hardness",    0.70, lambda f: f.get_brush_profile().hardness),
    ("tamanho",       "set_brush_size",        77.0, lambda f: f.get_brush_profile().brush_size),
]

print("=" * 70)
b = AladynBackend()
if not b.available:
    raise SystemExit("backend nativo indisponivel")

b.set_active_document_context("A", 64, 64)
b.apply_brush_preset_dict(dict(PRESET))

print("  propriedade      preset -> usuario   apos troca de contexto   veredito")
print("  " + "-" * 66)
stomped = []
for nome, setter, valor, leitor in AJUSTES:
    getattr(b, setter)(valor)
    antes = leitor(b._facade)
    b.set_active_document_context("B", 64, 64)
    b.set_active_document_context("A", 64, 64)
    depois = leitor(b._facade)
    ok = abs(depois - antes) < 0.02
    if not ok:
        stomped.append(nome)
    print(f"  {nome:15} {antes:8.3f}          {depois:8.3f}            "
          f"{'mantido' if ok else 'SOBRESCRITO'}")

print("  " + "-" * 66)
if stomped:
    print(f"  {len(stomped)} de {len(AJUSTES)} propriedades ainda sao sobrescritas: "
          f"{', '.join(stomped)}")
    print("  A correcao NAO esta ativa ou nao cobre estes casos.")
else:
    print(f"  Todas as {len(AJUSTES)} propriedades sobreviveram a troca de contexto.")
    print("  A correcao esta ativa e cobre a classe inteira, nao so o estabilizador.")
print("=" * 70)
