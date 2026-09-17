"""
tests/test_geometry_d0_snap_foundation.py
===========================================
Regressao Fase D0 (redesign do motor de snap) -- ver
claude/proposta-redesign-motor-snap-guias.md no projeto Lumenia (Projects
tool) para o diagnostico e desenho completos.

Testa os tres componentes novos e genericos (SnapCandidate/
TrajectoryEstimator/SnapLockStateMachine, engine/core/math/) isoladamente
via facade -- ainda NAO estao ligados a nenhum tipo de guia real, isso e'
D1-D3. O objetivo aqui e' provar que a peca central do redesign (estimar
direcao a partir de uma janela de pontos recentes, nao de um unico chord
entre dois pontos) e' de fato robusta a amostragem esparsa/ruidosa e resolve
o cenario que as duas rodadas de fix pontual do C3.5 nao resolveram.

Estas checagens espelham (e reforcam) um harness standalone em C++ escrito
durante o desenvolvimento, com os mesmos casos e os mesmos limiares --
aqui e' a versao que roda de verdade contra o modulo compilado.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import aladyn_engine_native as aen


class TestGeometryD0SnapFoundation(unittest.TestCase):
    def setUp(self):
        self.facade = aen.PaintEngineFacade(800, 600)

    @staticmethod
    def _flat(points):
        out = []
        for x, y in points:
            out.append(float(x))
            out.append(float(y))
        return out

    def test_01_trajectory_smooth_has_higher_confidence_than_erratic(self):
        smooth = self._flat([(0, 0), (10, 1), (20, -1), (30, 0), (40, 2), (50, 0)])
        dir_x, dir_y, conf_smooth = self.facade.estimate_trajectory(smooth, 1.0)
        self.assertGreater(conf_smooth, 0.85, "traco quase reto deveria ter confianca alta")
        self.assertGreater(abs(dir_x), 0.95, "traco quase reto deveria apontar quase puramente em x")

        # Mesmo numero de pontos, deslocamento liquido comparavel, mas o
        # traco fica indo e voltando -- confianca deve ser claramente menor.
        erratic = self._flat([(0, 0), (20, 0), (5, 0), (15, 0), (8, 0), (18, 0)])
        _, _, conf_erratic = self.facade.estimate_trajectory(erratic, 1.0)
        self.assertLess(conf_erratic, conf_smooth, "traco erratico deveria ter confianca menor que o suave")

    def test_02_trajectory_sparse_but_consistent_keeps_high_confidence(self):
        # So 2 pontos, salto grande (tipico de mouse) -- mas consistente.
        # Amostragem esparsa sozinha NAO deveria penalizar a confianca; so
        # inconsistencia de direcao deveria.
        sparse = self._flat([(0, 0), (50, 1)])
        _, _, conf = self.facade.estimate_trajectory(sparse, 1.0)
        self.assertGreater(conf, 0.9, "amostragem esparsa mas consistente deveria manter confianca alta")

    def test_03_trajectory_tiny_net_movement_has_near_zero_confidence(self):
        tiny = self._flat([(0, 0), (1, 0), (2, 0)])
        _, _, conf = self.facade.estimate_trajectory(tiny, 1.0)
        self.assertLess(conf, 0.1, "deslocamento liquido minusculo deveria ter confianca proxima de zero")

    def test_04_trajectory_single_point_has_zero_confidence(self):
        _, _, conf = self.facade.estimate_trajectory([5.0, 5.0], 1.0)
        self.assertEqual(conf, 0.0, "com 1 ponto so nao ha segmento algum -- confianca deve ser exatamente 0")

    def test_05_lock_state_machine_commits_after_commit_frames_with_hysteresis(self):
        cand_a = [0, 0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]        # Line horizontal, origem
        cand_b = [0, 0, 2000.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]     # Line vertical, (2000,0)
        candidates = cand_a + cand_b
        traj_horiz = (1.0, 0.0, 1.0)  # confianca plena, direcao horizontal

        state, idx, streak = 0, -1, 0  # Searching

        _, _, state, idx, streak = self.facade.step_snap_lock(10.0, 0.0, *traj_horiz, candidates, state, idx, streak)
        self.assertEqual(int(state), 1, "frame 1 deveria ser Tentative")
        self.assertEqual(int(idx), 0, "frame 1 deveria apontar para a candidata A (indice 0)")

        _, _, state, idx, streak = self.facade.step_snap_lock(15.0, 0.0, *traj_horiz, candidates, int(state), int(idx), int(streak))
        self.assertEqual(int(state), 1, "frame 2 ainda deveria ser Tentative (streak=2 < commit_frames=3)")

        _, _, state, idx, streak = self.facade.step_snap_lock(20.0, 0.0, *traj_horiz, candidates, int(state), int(idx), int(streak))
        self.assertEqual(int(state), 2, "frame 3 deveria comprometer (streak=3 >= commit_frames=3)")
        self.assertEqual(int(idx), 0, "deveria continuar comprometido na candidata A")

        # Histerese: um unico frame ruidoso, mas DENTRO do raio de afastamento,
        # nao deve soltar a trava mesmo que a trajetoria (ruidosa) aponte pra
        # outro lado por um instante -- Committed so olha afastamento espacial.
        _, _, state2, idx2, _streak2 = self.facade.step_snap_lock(
            25.0, 5.0, 0.0, 1.0, 0.9, candidates, int(state), int(idx), int(streak)
        )
        self.assertEqual(int(state2), 2, "um frame ruidoso dentro do raio de afastamento nao deveria soltar a trava")
        self.assertEqual(int(idx2), 0, "deveria continuar na candidata A apos o blip de ruido")

    def test_06_end_to_end_breakaway_then_smart_relock_via_real_trajectory(self):
        """Pipeline completo (estimate_trajectory -> step_snap_lock) contra o
        motor real, mesmo cenario de fundo do C3.5 (traco longo horizontal
        seguido de guinada curta e brusca): prova que com uma estimativa de
        trajetoria de verdade (janela de pontos recentes, nao um unico chord
        fixo) o re-travamento pos break-away acerta a candidata vertical --
        o cenario que as duas rodadas de fix pontual do C3.5 nao resolviam
        de forma robusta."""
        cand_a = [0, 0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]
        cand_b = [0, 0, 2000.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]
        candidates = cand_a + cand_b

        # Comprometido em A (equivalente a ja ter percorrido varios frames horizontais).
        state, idx, streak = 2, 0, 5

        window = [1990.0, 0.0, 1995.0, 0.0, 2000.0, 0.0]
        dx, dy, conf = self.facade.estimate_trajectory(window, 1.0)
        _, _, state, idx, streak = self.facade.step_snap_lock(2000.0, 0.0, dx, dy, conf, candidates, state, idx, streak)
        self.assertEqual(int(state), 2, "antes da guinada deveria continuar comprometido em A")

        window += [2005.0, 20.0, 2010.0, 50.0]
        dx2, dy2, conf2 = self.facade.estimate_trajectory(window, 1.0)
        self.assertGreater(dy2, 0.5, "trajetoria deveria detectar a componente vertical da guinada")

        _, _, state2, idx2, _streak2 = self.facade.step_snap_lock(
            2010.0, 50.0, dx2, dy2, conf2, candidates, int(state), int(idx), int(streak)
        )
        self.assertIn(int(state2), (0, 1), "afastamento de 50px (> breakaway_radius=32) deveria soltar o Committed em A")
        self.assertEqual(int(idx2), 1, "com trajetoria real deveria favorecer a candidata B (vertical), nao repetir A")


if __name__ == "__main__":
    unittest.main()
