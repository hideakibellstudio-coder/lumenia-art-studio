"""
tests/test_geometry_c35_native_anchor.py
=========================================
Regressao Fase C3.5 (refinamento) -- ver claude/fase-c3-consolidacao-snap-nativo.md
no projeto Lumenia (Projects tool) para o diagnostico completo.

Arquivo dedicado (em vez de crescer test_geometry_symmetry.py) para nao
estourar o teto de LOC da Zona Vermelha (MAX_LINES_ERROR=450,
tests/arccc_governance_rules.py) -- excecoes de teto so podem ser
autorizadas por humano, entao a solucao correta e' um arquivo novo, nao uma
excecao auto-declarada.

Os dois testes aqui validam, no nivel do GeometryToolController (onde o
`anchor` de re-travamento foi introduzido), que a referencia de direcao
usada para RE-travar apos um break-away (fix v1, C3.5) e' o ultimo ponto
travado com sucesso -- nao o ponto de pressao original do traco, que fica
cada vez mais desatualizado num traco longo e rapido (o bug que o usuario
reportou continuar ocorrendo mesmo depois do fix v1, pior com mouse do que
com stylus). Usam um backend nativo falso porque a extensao compilada
(aladyn_engine_native, .pyd win_amd64) nao esta disponivel neste ambiente de
teste -- os testes de motor de verdade (test_12/test_13 em
test_geometry_symmetry.py) ja cobrem o break-away contra o facade nativo
real; o que falta cobertura aqui e' especificamente a fiacao Python do
anchor, que nao muda nenhuma assinatura nativa.
"""

import math
import os as _os
import sys
import unittest

sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..")))

from ui.core.engine.registry import EngineRegistry
from ui.plugins.system.workspace_core.workspace.canvas.tools.geometry_tool_controller import (
    GeometryToolController,
)


class GeometryConfigSink:
    """Parte do contrato EngineBackend que o controlador sempre chama (guias e
    simetria vão ao motor a cada mudança); os dublês abaixo só precisam do snap."""

    def set_symmetry_config(self, *args):
        pass

    def set_guide_config(self, *args):
        pass

    def set_curvilinear_guide_config(self, *args):
        pass


class DummyWidget:
    canvas_w = 4000
    canvas_h = 4000


class TestGeometryC35NativeAnchor(unittest.TestCase):
    def test_01_curvilinear_controller_relock_uses_recent_anchor_not_stale_press_point(self):
        """O fix de break-away (test_12 em test_geometry_symmetry.py) solta
        uma trava obsoleta, mas o RE-travamento que acontece em seguida ainda
        tinha um bug proprio -- ele reavaliava a direcao do gesto a partir do
        ponto de PRESSAO ORIGINAL do traco, nao de onde o cursor esteve mais
        recentemente. Num traco longo e rapido (o cenario reportado pelo
        usuario, pior com mouse por causa de eventos mais espacados), esse
        deslocamento acumulado desde o inicio do traco domina a conta e pode
        escolher a curva errada de novo mesmo depois do break-away funcionar
        corretamente.

        Este teste simula esse cenario com um backend nativo falso cuja
        logica de snap_curvilinear espelha CurvilinearSnapEngine::snap():
        traco longo horizontal (trava a curva A, ponto de pressao fica muito
        longe) seguido de uma guinada curta e brusca para baixo. A guinada
        em si e pequena (10, 50) -- so aponta claramente para a curva
        vertical B quando medida a partir de onde o cursor estava ha pouco
        (o anchor), nao a partir do ponto de pressao (0,0), que fica a mais
        de 2000px de distancia e cuja direcao continua "quase horizontal"
        mesmo apos a guinada."""

        class FakeNativeBackend(GeometryConfigSink):
            """Reimplementa em Python puro a mesma estrutura de
            CurvilinearSnapEngine::snap() (trava/stray/lockThresh/pontuacao
            por produto escalar, incluindo a penalizacao por distancia ate a
            candidata -- score = dot / max(1, distancia*0.05) --, sem a qual
            o teste seria invalido: uma reta so e' uma candidata plausivel
            se passar perto de onde o cursor esta agora), o suficiente para
            exercitar a fiacao de `anchor` no controller sem depender da
            extensao nativa compilada (indisponivel neste ambiente de
            teste)."""

            SNAP_RADIUS = 32.0

            def __init__(self, candidates):
                self._candidates = candidates  # [{"point": (px,py), "dir": (dx,dy)}, ...]

            def get_curvilinear_candidates(self, sx, sy):
                return self._candidates

            @staticmethod
            def _closest(cand, raw_x, raw_y):
                px, py = cand["point"]
                dx_, dy_ = cand["dir"]
                dot = (raw_x - px) * dx_ + (raw_y - py) * dy_
                return px + dot * dx_, py + dot * dy_

            def snap_curvilinear(self, raw_x, raw_y, start_x, start_y, candidates, locked_idx, is_stroking, zoom):
                if 0 <= locked_idx < len(candidates):
                    cx, cy = self._closest(candidates[locked_idx], raw_x, raw_y)
                    stray = math.hypot(raw_x - cx, raw_y - cy)
                    if stray <= self.SNAP_RADIUS:
                        return (cx, cy, locked_idx)

                dx, dy = raw_x - start_x, raw_y - start_y
                dist = math.hypot(dx, dy)
                lock_thresh = max(2.0, 7.5 - 3.0 * 1.2) / max(0.01, zoom)
                if dist < lock_thresh:
                    best_pt, best_d = None, float("inf")
                    for c in candidates:
                        cx, cy = self._closest(c, raw_x, raw_y)
                        d = math.hypot(raw_x - cx, raw_y - cy)
                        if d < best_d:
                            best_d, best_pt = d, (cx, cy)
                    return (best_pt[0], best_pt[1], -1)

                ux, uy = dx / dist, dy / dist
                best_i, best_score, best_pt = 0, -1.0, None
                for i, c in enumerate(candidates):
                    cx, cy = self._closest(c, raw_x, raw_y)
                    ddist = math.hypot(raw_x - cx, raw_y - cy)
                    score = abs(ux * c["dir"][0] + uy * c["dir"][1]) / max(1.0, ddist * 0.05)
                    if score > best_score:
                        best_score, best_i, best_pt = score, i, (cx, cy)
                new_idx = best_i if is_stroking else -1
                return (best_pt[0], best_pt[1], new_idx)

        # A: horizontal passando pela origem. B: vertical passando por
        # (2000, 0) -- onde o traço estará quando a guinada acontecer, para
        # que as duas candidatas sejam igualmente plausíveis em distância
        # naquele momento (isola a pergunta em teste: qual referência de
        # DIREÇÃO decide o desempate -- o ponto de pressão obsoleto ou o
        # anchor recente).
        candidates = [
            {"point": (0.0, 0.0), "dir": (1.0, 0.0)},
            {"point": (2000.0, 0.0), "dir": (0.0, 1.0)},
        ]
        registry = EngineRegistry.instance()
        prev_backend = registry.get_backend()
        prev_env = _os.environ.get("LUMENIA_SNAP_NATIVE_CURVILINEAR")
        try:
            _os.environ["LUMENIA_SNAP_NATIVE_CURVILINEAR"] = "1"
            registry.set_backend(FakeNativeBackend(candidates))

            ctrl: GeometryToolController = GeometryToolController(DummyWidget())
            self.assertTrue(ctrl.native_snap.use_curvilinear)
            ctrl.guide_state["type"] = "curvilinear"
            ctrl.start_stroke_snap((0.0, 0.0))
            self.assertIsNone(ctrl.native_snap.curv_anchor)

            # 1) Traço longo e rápido ao longo da curva A (horizontal): trava
            #    nela e o anchor acompanha até bem longe do ponto de pressão.
            ctrl.snap_point(500.0, 5.0, 1.0)
            self.assertEqual(ctrl.native_snap.curv_locked_index, 0, "deveria travar na curva A (horizontal)")
            ctrl.snap_point(2000.0, 0.0, 1.0)
            self.assertEqual(ctrl.native_snap.curv_locked_index, 0)
            self.assertAlmostEqual(ctrl.native_snap.curv_anchor.x(), 2000.0, delta=1e-6)
            self.assertAlmostEqual(ctrl.native_snap.curv_anchor.y(), 0.0, delta=1e-6)

            # 2) Guinada brusca e curta para baixo: (10, 50) a partir de onde
            #    o cursor estava (2000, 0) -- claramente vertical -- mas a
            #    partir do ponto de pressão original (0, 0) o deslocamento
            #    total (2010, 50) ainda "vota" esmagadoramente em horizontal.
            #    Com a referência correta (anchor), deve soltar A e travar
            #    em B; com o ponto de pressão original (comportamento antigo)
            #    ficaria preso em A.
            res3 = ctrl.snap_point(2010.0, 50.0, 1.0)
            self.assertEqual(
                ctrl.native_snap.curv_locked_index, 1,
                "com o anchor (2000,0), a guinada curta (10,50) e' claramente vertical e deveria "
                "vencer a votacao; com o ponto de pressao original (0,0) o deslocamento acumulado "
                "(2010,50) ainda vota esmagadoramente em horizontal -- se voltar a travar na curva A "
                "(indice 0), a regressao do C3.5 (refinamento) retornou"
            )
            self.assertAlmostEqual(res3[0], 2000.0, delta=1e-6)
            self.assertAlmostEqual(res3[1], 50.0, delta=1e-6)
            self.assertAlmostEqual(ctrl.native_snap.curv_anchor.x(), res3[0], delta=1e-6)
            self.assertAlmostEqual(ctrl.native_snap.curv_anchor.y(), res3[1], delta=1e-6)

            # 3) mouse_release / start_stroke_snap devem limpar o anchor.
            ctrl.mouse_release()
            self.assertIsNone(ctrl.native_snap.curv_anchor)
        finally:
            registry.set_backend(prev_backend)
            if prev_env is None:
                _os.environ.pop("LUMENIA_SNAP_NATIVE_CURVILINEAR", None)
            else:
                _os.environ["LUMENIA_SNAP_NATIVE_CURVILINEAR"] = prev_env

    def test_02_perspective_controller_tracks_anchor_across_relock(self):
        """Mesma fiacao de `anchor` do test_01, para o caminho
        snap_perspective. Nao reimplementa a geometria de vpA/vpB (isso ja e
        coberto por test_11/test_13 em test_geometry_symmetry.py contra o
        motor nativo de verdade); aqui o alvo e so confirmar que o
        controller passa o anchor (nao o ponto de pressao original) como
        referencia para o backend, e que ele e atualizado/limpo
        corretamente pelo ciclo de vida do traço."""

        class RecordingFakeBackend(GeometryConfigSink):
            """Trava sempre na direcao vertical (0,1) e apenas registra qual
            ponto foi usado como referencia (start_x, start_y) em cada
            chamada, para provar que o controller esta repassando o anchor."""

            def __init__(self):
                self.seen_starts = []

            def snap_perspective(self, raw_x, raw_y, start_x, start_y, has_locked_dir, ldx, ldy, zoom):
                self.seen_starts.append((start_x, start_y))
                t = (raw_x - start_x) * 0.0 + (raw_y - start_y) * 1.0
                return (start_x, start_y + t, True, 0.0, 1.0)

        registry = EngineRegistry.instance()
        prev_backend = registry.get_backend()
        prev_env = _os.environ.get("LUMENIA_SNAP_NATIVE_PERSPECTIVE")
        try:
            _os.environ["LUMENIA_SNAP_NATIVE_PERSPECTIVE"] = "1"
            backend = RecordingFakeBackend()
            registry.set_backend(backend)

            ctrl = GeometryToolController(DummyWidget())
            self.assertTrue(ctrl.native_snap.use_perspective)
            ctrl.guide_state["type"] = "one_point"
            ctrl.start_stroke_snap((0.0, 0.0))
            self.assertIsNone(ctrl.native_snap.persp_anchor)

            ctrl.snap_point(0.0, 100.0, 1.0)
            self.assertEqual(backend.seen_starts[-1], (0.0, 0.0), "1a chamada deve usar o ponto de pressao (sem anchor ainda)")
            self.assertAlmostEqual(ctrl.native_snap.persp_anchor.x(), 0.0, delta=1e-6)
            self.assertAlmostEqual(ctrl.native_snap.persp_anchor.y(), 100.0, delta=1e-6)

            ctrl.snap_point(0.0, 250.0, 1.0)
            self.assertEqual(
                backend.seen_starts[-1], (0.0, 100.0),
                "2a chamada deve usar o anchor (ultimo ponto travado), nao o ponto de pressao original"
            )

            ctrl.mouse_release()
            self.assertIsNone(ctrl.native_snap.persp_anchor)
        finally:
            registry.set_backend(prev_backend)
            if prev_env is None:
                _os.environ.pop("LUMENIA_SNAP_NATIVE_PERSPECTIVE", None)
            else:
                _os.environ["LUMENIA_SNAP_NATIVE_PERSPECTIVE"] = prev_env


if __name__ == "__main__":
    unittest.main()
