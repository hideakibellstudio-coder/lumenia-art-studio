#!/usr/bin/env python3
"""
scripts/soak_full_session.py
============================
Gate de sessão longa com a APLICAÇÃO INTEIRA (cenário "completo").

Por que existe (2026-09-22): `run_soak_test.py` exercita só o caminho do pincel
nativo -- sem janela, sem widgets, um documento, traços de 40 px e desfazer
limitado a 30 passos. Nesse desenho o platô de memória é garantido pelo próprio
anel de desfazer, e GDI = 0 é trivial porque não existe widget nenhum. Útil
como smoke test do motor; insuficiente para afirmar "zero vazamentos".

Este cenário sobe a MainWindow real (offscreen) com os plugins, e a cada ciclo:
  - pinta um traço no documento ativo e força o repaint do canvas (grab);
  - a cada 8 ciclos: desfaz e refaz;
  - a cada 10: cria camada, muda opacidade e visibilidade (pelo LocalLayerManager,
    o mesmo caminho do painel de Camadas); a cada 20: remove as camadas extras;
  - a cada 25: salva o documento em .lmn (pasta temporária);
  - a cada 40: abre um segundo documento, pinta nele, volta ao primeiro e fecha
    o segundo (ciclo MDI completo: facade C++ criada e destruída).
As camadas extras e o segundo documento são sempre desfeitos, então o que é
retido pelo design (anel de desfazer, cache de tiles) estabiliza; o que cresce
depois do aquecimento é vazamento.

Não mexe nas preferências do usuário: config, plugins e recuperação vão para
uma pasta temporária, como na suíte de testes.

Uso:
  python scripts/soak_full_session.py                 # 3000 ciclos (~7 min)
  python scripts/soak_full_session.py --cycles 2000 --output-csv soak_full.csv
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_PERFIL = tempfile.TemporaryDirectory(prefix="lumenia-soak-profile-")
os.environ["LUMENIA_CONFIG_PATH"] = str(Path(_PERFIL.name) / "config.json")
os.environ["LUMENIA_PLUGINS_CONFIG_PATH"] = str(Path(_PERFIL.name) / "plugins_config.json")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from scripts.run_soak_test import analisar_plato, get_process_metrics  # noqa: E402


# As posições se repetem com período fixo: todos os tiles que o teste toca são
# alocados nos primeiros ciclos. Sem isso, cada traço em área nova aloca tiles
# legitimamente (o documento cresceu) e o "drift" mediria conteúdo, não vazamento.
_PERIODO_POSICOES = 24


def _traco(backend, ciclo: int, largura: int, altura: int) -> None:
    fase = ciclo % _PERIODO_POSICOES
    x0 = 80.0 + (fase * 61) % max(1, largura - 400)
    y0 = 80.0 + (fase * 47) % max(1, altura - 400)
    comprimento = 120.0 + (ciclo % 5) * 60.0
    backend.set_brush_size(8.0 + (ciclo % 30) * 3.0)
    backend.set_brush_color((ciclo * 37) % 256, (ciclo * 59) % 256, (ciclo * 83) % 256)
    backend.start_stroke(x0, y0, 0.5)
    for s in range(1, 25):
        t = s / 24.0
        backend.paint_stroke(x0 + comprimento * t, y0 + 60.0 * math.sin(t * math.pi * 2), 0.2 + 0.8 * math.sin(t * math.pi))
    backend.end_stroke()


def run_full_session(total: int, warmup: int, intervalo: int, output_csv: str | None,
                     desligar: frozenset = frozenset()) -> bool:
    from PySide6 import QtWidgets
    from ui.boundary.orchestrator.main_window import MainWindow
    from ui.core.document.document import Document
    from ui.core.document.manager import DocumentManager
    from ui.core.document.serializer import DocumentSerializer
    from ui.core.engine.registry import EngineRegistry

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(["--platform", "offscreen"])
    janela = MainWindow()
    janela.show()
    dm = DocumentManager.instance()
    doc: Document = dm.new_document(1920, 1080, "Soak principal")
    app.processEvents()
    backend = EngineRegistry.instance().get_backend()
    if backend is None or not backend.available:
        print("[-] Motor nativo indisponível.")
        return False
    canvas = janela.workspace.canvas_widget if janela.workspace is not None else None
    pasta_saida = Path(_PERFIL.name) / "saves"
    pasta_saida.mkdir(parents=True, exist_ok=True)
    camadas_extras: list[str] = []

    print("=" * 72)
    print("  LUMENIA — SESSÃO LONGA COM A APLICAÇÃO INTEIRA (cenário completo)")
    print(f"  Ciclos: {total} | aquecimento: {warmup} | amostra a cada {intervalo}")
    print("=" * 72)

    import gc
    gc.collect()
    amostras = [(0, 0.0, *get_process_metrics())]
    inicio = time.perf_counter()
    for ciclo in range(1, total + 1):
        _traco(backend, ciclo, doc.width, doc.height)
        if "grab" not in desligar and canvas is not None and ciclo % 5 == 0:
            canvas.grab()
        if "undo" not in desligar and ciclo % 8 == 0 and backend.can_undo():
            backend.undo()
            if backend.can_redo():
                backend.redo()
        lm = doc.layer_manager
        if "camadas" not in desligar and ciclo % 10 == 0:
            uid = lm.add_layer(f"Soak {ciclo}")  # devolve o UID, não a posição
            idx = lm.active_index
            lm.set_layer_opacity(idx, 0.4 + (ciclo % 6) / 10.0)
            lm.set_layer_visibility(idx, ciclo % 20 != 0)
            camadas_extras.append(uid)
        if ciclo % 20 == 0:
            for uid in camadas_extras:
                lm.remove_layer(uid)
            camadas_extras.clear()
        if "salvar" not in desligar and ciclo % 25 == 0:
            DocumentSerializer.save(doc, backend, pasta_saida / "soak.lmn")
        if "mdi" not in desligar and ciclo % 40 == 0:
            outro = dm.new_document(1280, 720, f"Soak MDI {ciclo}")
            app.processEvents()
            _traco(backend, ciclo, outro.width, outro.height)
            dm.set_active_document(doc.uid)
            app.processEvents()
            dm.close_document(outro.uid)
        app.processEvents()
        if ciclo % intervalo == 0 or ciclo == total:
            gc.collect()
            ws, pv, hnd, gdi = get_process_metrics()
            amostras.append((ciclo, time.perf_counter() - inicio, ws, pv, hnd, gdi))
            print(f"  [Ciclo {ciclo:4d}] WS {ws:7.1f} MB | Priv {pv:7.1f} MB | Handles {hnd:5d} | GDI {gdi:4d}")

    if output_csv:
        with open(output_csv, "w", encoding="utf-8") as fh:
            fh.write("ciclo,tempo_s,working_set_mb,private_mb,handles,gdi\n")
            for a in amostras:
                fh.write(f"{a[0]},{a[1]:.2f},{a[2]:.2f},{a[3]:.2f},{a[4]},{a[5]}\n")
    return analisar_plato(amostras, warmup, titulo="SESSÃO COMPLETA")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gate de sessão longa com a aplicação inteira")
    # Medido em 2026-09-22: com a aplicação inteira, a memória privada ainda sobe
    # devagar até ~1800 ciclos (caches de Qt/Python enchendo, curva que achata) e
    # fica plana depois (1800–2400: +0,05 ± 0,06 MB/100 ciclos). Aquecimento
    # menor que isso mede a saturação, não vazamento.
    parser.add_argument("--cycles", type=int, default=3000)
    parser.add_argument("--warmup", type=int, default=1800)
    parser.add_argument("--interval", type=int, default=50)
    parser.add_argument("--output-csv", type=str, default=None)
    parser.add_argument("--desligar", default="", help="Diagnóstico: lista separada por vírgula entre "
                        "grab,undo,camadas,salvar,mdi para isolar qual etapa faz a memória crescer")
    args = parser.parse_args()
    desligar = frozenset(x.strip() for x in args.desligar.split(",") if x.strip())
    if desligar:
        print(f"  [diagnóstico] etapas desligadas: {sorted(desligar)}")
    ok = run_full_session(args.cycles, args.warmup, args.interval, args.output_csv, desligar)
    sys.exit(0 if ok else 1)
