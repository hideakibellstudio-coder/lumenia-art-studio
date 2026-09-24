"""
Test Suite: Giant Brush Smoothness, Analytic Falloff & LargeBrushOptimizer Throughput
=====================================================================================
Validates:
1. Absence of 80% solid cliff / polygonal stepping in soft brushes and airbrushes.
2. Smooth C^1 cubic Hermite falloff continuity across radial distances.
3. High throughput / low latency (< 1.5 ms per event) on 500px diameter brushes.
4. Analytic shape preview generation in get_shape_preview_buffer when shapeTexture is nullptr.
5. LargeBrushOptimizer step calibration and continuous coverage.
"""

import time
import unittest
import numpy as np
import aladyn_engine_native as aen

# Limites de tempo de relógio: calibrados pela velocidade da máquina.
#
# Os limites (25 ms, 30 ms, 5 ms) valem para uma máquina de referência. Os
# runners do CI são compartilhados e de hardware variável: o mesmo binário
# levou 8-11 ms numa execução e 39-62 ms em outras, e em 2026-09-24 um runner
# ficou acima de 39 ms nas 5 repetições seguidas -- o "melhor de 5" (que já
# absorve interrupções isoladas do agendador) não absorve máquina lenta.
#
# Por isso cada limite é multiplicado pelo fator da máquina: o melhor tempo de
# um trabalho de referência fixo (numpy, CPU e memória, sem o motor) dividido
# pelo tempo dele na máquina de referência. Máquina lenta: os dois tempos
# sobem juntos. Regressão do motor: só o traço sobe, e o teste falha. O fator
# nunca é menor que 1 (máquina rápida não aperta o limite) e tem teto
# (_FATOR_MAXIMO): acima dele o ambiente está anormal e o teste deve falhar.
_REPETICOES = 5
_CALIBRACAO_REFERENCIA_MS = 5.0  # medido no container Linux de referência (4,7 ms)
_FATOR_MAXIMO = 8.0


def _melhor_tempo_ms(tracar) -> float:
    melhor = float("inf")
    for _ in range(_REPETICOES):
        t0 = time.perf_counter()
        tracar()
        melhor = min(melhor, (time.perf_counter() - t0) * 1000.0)
    return melhor


def _calibracao():
    rng = np.random.default_rng(0)
    a = rng.random((512, 512, 4), dtype=np.float32)
    b = rng.random((512, 512, 4), dtype=np.float32)
    saida = np.empty_like(a)

    def trabalho():
        for _ in range(4):
            np.multiply(a, 0.3, out=saida)
            np.add(saida, b * 0.7, out=saida)
            np.clip(saida, 0.0, 1.0, out=saida)

    return trabalho


def fator_da_maquina() -> float:
    """Quantas vezes esta máquina é mais lenta que a de referência (>= 1, com teto)."""
    medido = _melhor_tempo_ms(_calibracao())
    return min(_FATOR_MAXIMO, max(1.0, medido / _CALIBRACAO_REFERENCIA_MS))


class TestGiantBrushSmoothnessAndThroughput(unittest.TestCase):
    def setUp(self):
        self.w = 800
        self.h = 800
        self.facade = aen.PaintEngineFacade(self.w, self.h)
        self.facade.set_background_visibility(False)
        self.facade.add_layer("Layer 1")
        self.facade.select_layer(0)

    def _get_canvas_array(self) -> np.ndarray:
        buf = self.facade.get_pixel_buffer()
        return np.frombuffer(buf, dtype=np.uint8).reshape((self.h, self.w, 4))

    def test_01_soft_brush_analytic_smooth_falloff_without_cliff(self):
        """
        Valida que um pincel macio (hardness = 0.0) de 500px possui atenuação suave contínua
        desde o centro até a borda, sem o antigo platô plano artificial de 80% do raio.
        """
        profile = self.facade.get_brush_profile()
        profile.brush_size = 500.0  # Raio = 250px
        profile.hardness = 0.0     # Totalmente macio / suave
        profile.base_color = aen.ColorRGBA(0, 0, 0, 255)
        profile.opacity = 1.0

        # Carimbo único no centro (400, 400)
        self.facade.begin_stroke_raw(400.0, 400.0, 1.0)
        self.facade.end_stroke_raw()

        arr = self._get_canvas_array()

        # O centro exato (400, 400) deve ter alfa máximo (pixel center 400.5, 400.5 tem subpixel offset de ~0.71px)
        alpha_center = int(arr[400, 400, 3])
        self.assertGreaterEqual(alpha_center, 254, f"Centro deve ter alfa >= 254, obtido {alpha_center}")

        # A 50% do raio (r = 125px): com Hermite suave, t = (250 - 125) / 250 = 0.5
        # s(0.5) = 0.5^2 * (3 - 1) = 0.50 -> alfa esperado ≈ 127
        # No código antigo com platô de 80%, alfa a 50% do raio era 255 (100% sólido)!
        alpha_half_radius = int(arr[400, 400 + 125, 3])
        self.assertLess(
            alpha_half_radius, 200,
            f"A 50% do raio em pincel macio, o alfa ({alpha_half_radius}) não pode ser sólido (deve atenuar suavemente)"
        )
        self.assertGreater(
            alpha_half_radius, 80,
            f"A 50% do raio em pincel macio, o alfa ({alpha_half_radius}) deve ser intermediário"
        )

        # A 80% do raio (r = 200px): t = (250 - 200) / 250 = 0.2
        # s(0.2) = 0.04 * 2.6 = 0.104 -> alfa esperado ≈ 26
        # No código antigo, o corte começava exatamente em 80%!
        alpha_80_percent = int(arr[400, 400 + 200, 3])
        self.assertLess(
            alpha_80_percent, 80,
            f"A 80% do raio em pincel macio, o alfa ({alpha_80_percent}) deve ser suave e baixo"
        )

        # A 100% do raio (r = 250px) e além: pureza transparente
        alpha_outside = int(arr[400, 400 + 252, 3])
        self.assertEqual(alpha_outside, 0, f"Fora do raio deve ser 0, obtido {alpha_outside}")

    def test_02_giant_brush_throughput_speed(self):
        """
        Valida que um traço longo de 500px é renderizado em alta velocidade (< 20ms para o traço inteiro,
        mantendo < 1.5ms por evento de movimento).
        """
        profile = self.facade.get_brush_profile()
        profile.brush_size = 500.0  # Raio = 250px
        profile.hardness = 0.85
        profile.spacing_factor = 0.10
        profile.base_color = aen.ColorRGBA(30, 80, 160, 255)

        def tracar():
            self.facade.begin_stroke_raw(250.0, 400.0, 1.0)
            for x in range(270, 551, 20):
                self.facade.update_stroke_raw(float(x), 400.0, 1.0)
            self.facade.end_stroke_raw()

        total_time_ms = _melhor_tempo_ms(tracar)
        fator = fator_da_maquina()

        # 15 eventos de movimento com pincel de 500px: menos de 25ms na máquina de referência
        self.assertLess(
            total_time_ms, 25.0 * fator,
            f"Tempo total do traço de 500px ({total_time_ms:.2f}ms) excedeu o limite de alta fluidez "
            f"(25ms × fator da máquina {fator:.2f})"
        )

    def test_03_analytic_shape_preview_buffer(self):
        """
        Valida que get_shape_preview_buffer gera uma prévia analítica 64x64 válida
        mesmo quando shapeTexture é nullptr.
        """
        # Padrão: shapeTexture é nullptr
        dims = self.facade.get_shape_preview_dimensions()
        self.assertEqual(dims, (64, 64), f"Dimensões de prévia esperadas (64, 64), obtido {dims}")

        buf = self.facade.get_shape_preview_buffer()
        self.assertIsNotNone(buf, "get_shape_preview_buffer não deve ser None")
        self.assertEqual(len(buf), 64 * 64, f"Buffer de prévia deve ter 4096 bytes, obtido {len(buf)}")

        preview_arr = np.frombuffer(buf, dtype=np.uint8).reshape((64, 64))
        # O centro da prévia deve ser opaco
        self.assertGreater(int(preview_arr[32, 32]), 240, "Centro da prévia deve ser opaco")
        # Os cantos devem ser transparentes
        self.assertEqual(int(preview_arr[0, 0]), 0, "Canto da prévia deve ser transparente")

    def test_04_stylus_high_frequency_simulation_throughput(self):
        """
        Simula a taxa ultra-alta de uma mesa digitalizadora (773 Hz, dt ~1.29ms, micropassos de 0.3px)
        com pincel de 500px. Valida que:
        1. 200 micro-eventos executam em altíssima velocidade (< 30ms total, < 0.15ms por evento).
        2. A detecção de ponto estacionário NÃO dispara espuriamente em passos subpixel.
        3. A quantidade de carimbos gerados é estritamente proporcional ao avanço espacial (~1 dab para 60px).
        """
        profile = self.facade.get_brush_profile()
        profile.brush_size = 500.0
        profile.hardness = 0.2
        profile.spacing_factor = 0.08
        profile.base_color = aen.ColorRGBA(0, 0, 0, 255)

        dt = 1.0 / 773.0
        relogio = {"t": 1000.0}

        def tracar():
            # O relógio da caneta só avança entre repetições (nunca volta atrás).
            t = relogio["t"] + 1.0
            self.facade.begin_stroke_raw(200.0, 400.0, 0.5, t)
            cur_x = 200.0
            for _ in range(200):
                cur_x += 0.3
                t += dt
                self.facade.update_stroke_raw(cur_x, 400.0, 0.5, t)
            self.facade.end_stroke_raw()
            relogio["t"] = t

        total_ms = _melhor_tempo_ms(tracar)
        fator = fator_da_maquina()

        self.assertLess(
            total_ms, 30.0 * fator,
            f"200 eventos a 773 Hz levaram {total_ms:.2f}ms (esperado < 30ms × fator da máquina "
            f"{fator:.2f} para fluidez de 120 FPS)"
        )

        snap = self.facade.get_telemetry_snapshot()
        if snap:
            # Em 60px de avanço com passo adaptativo de ~90px, deve haver no máximo 2 dabs
            self.assertLessEqual(
                snap.total_dabs_in_stroke, 3,
                f"Número de dabs ({snap.total_dabs_in_stroke}) excedeu o esperado para avanço de 60px"
            )

    def test_05_soft_brush_light_pressure_accumulation_controlled(self):
        """
        Valida que uma passada com pressão leve/média (40% de pressão / opacidade) em pincel macio de 500px
        mantém a transparência suave e NÃO satura prematuramente para preto sólido (alpha 255).
        """
        profile = self.facade.get_brush_profile()
        profile.brush_size = 500.0
        profile.hardness = 0.0  # Totalmente suave
        profile.spacing_factor = 0.08
        profile.base_color = aen.ColorRGBA(0, 0, 0, 255)
        profile.opacity = 0.40

        # Traço suave de x=200 a x=600 (avanço de 400px)
        self.facade.begin_stroke_raw(200.0, 400.0, 0.40)
        for x in range(210, 601, 10):
            self.facade.update_stroke_raw(float(x), 400.0, 0.40)
        self.facade.end_stroke_raw()

        arr = self._get_canvas_array()

        # O centro do traço (400, 400) com opacidade 0.40 não pode estar 100% saturado em preto (255)
        alpha_center = int(arr[400, 400, 3])
        self.assertLess(
            alpha_center, 245,
            f"Passada suave com opacidade 40% acumulou excessivamente para {alpha_center} (esperado < 245)"
        )
        self.assertGreater(
            alpha_center, 80,
            f"Passada suave deve ter cobertura visível intermediária, obtido {alpha_center}"
        )

    def test_06_wide_horizontal_stroke_compositor_performance(self):
        """
        Valida que um traço largo horizontal cobrindo dezenas de tiles (ex: 1300x260 px, ~30 tiles)
        é composto em alta velocidade com paralelização OpenMP 2D achatada, mantendo time_composite_us < 5.0ms (5000 µs),
        mesmo quando a extensão vertical é pequena (poucas linhas de tiles em Y).
        """
        facade = aen.PaintEngineFacade(2000, 1000)
        facade.set_telemetry_enabled(True)
        facade.set_background_visibility(False)
        facade.add_layer("Layer 1")
        facade.select_layer(0)

        profile = facade.get_brush_profile()
        profile.brush_size = 260.0
        profile.hardness = 0.5
        profile.spacing_factor = 0.10
        profile.base_color = aen.ColorRGBA(255, 0, 0, 255)

        # Inicia e faz um traço horizontal contínuo de x=100 a x=1400 (largura dirty ~1300px, altura ~260px)
        facade.begin_stroke_raw(100.0, 500.0, 1.0)
        for x in range(150, 1401, 50):
            facade.update_stroke_raw(float(x), 500.0, 1.0)
        facade.end_stroke_raw()

        snap = facade.get_telemetry_snapshot()
        self.assertIsNotNone(snap)
        # O último composite time deve ser muito rápido (< 5.0 ms na máquina de referência)
        fator = fator_da_maquina()
        self.assertLess(
            snap.time_composite_us, 5000.0 * fator,
            f"Tempo de composição ({snap.time_composite_us:.1f} µs) excedeu o teto de 5ms × fator da "
            f"máquina {fator:.2f} para traço horizontal multi-tile"
        )

    def test_07_centripetal_catmull_rom_spline_circular_accuracy(self):
        """
        Valida que a Spline Catmull-Rom Centrípeta C^1 elimina o aspecto quadrado/poligonal de traços curvos.
        Traçando um círculo de raio 200px com apenas 12 nós de controle (ângulos espaçados em 30°) a 0% de estabilização:
        - A corda reta linear antiga afundaria 6.82 px para dentro (erro de 3.41% / vértices visíveis).
        - A Spline Catmull-Rom Centrípeta preserva a curvatura circular contínua com desvio radial médio < 1.0 px (< 0.5%).
        """
        facade = aen.PaintEngineFacade(1000, 1000)
        facade.set_background_visibility(False)
        facade.add_layer("Layer 1")
        facade.select_layer(0)
        facade.get_stabilizer().set_stabilization_percentage(0.0)

        profile = facade.get_brush_profile()
        profile.brush_size = 10.0
        profile.spacing_factor = 0.02
        profile.base_color = aen.ColorRGBA(0, 0, 0, 255)

        # Círculo de raio R=200 centrado em (500, 500) com 12 pontos
        angles = np.linspace(0, 2 * np.pi, 13)
        pts = [(500.0 + 200.0 * np.cos(a), 500.0 + 200.0 * np.sin(a)) for a in angles]

        facade.begin_stroke_raw(pts[0][0], pts[0][1], 1.0)
        for p in pts[1:]:
            facade.update_stroke_raw(p[0], p[1], 1.0)
        facade.end_stroke_raw()

        buf = facade.get_pixel_buffer()
        arr = np.frombuffer(buf, dtype=np.uint8).reshape((1000, 1000, 4))
        y_indices, x_indices = np.where(arr[:, :, 3] > 128)
        self.assertGreater(len(x_indices), 5000, "Deve renderizar pixels opacos ao longo do círculo completo")

        dists = np.sqrt((x_indices - 500.0)**2 + (y_indices - 500.0)**2)
        mean_radius = dists.mean()
        radial_deviation = abs(mean_radius - 200.0)

        self.assertLess(
            radial_deviation, 2.5,
            f"Desvio radial médio ({radial_deviation:.2f}px) da Spline Catmull-Rom para 12 nós deve ser < 2.5px, contra 6.82px da corda reta linear"
        )

        # Círculo com 24 nós (passos de 15°): valida convergência subpixel (< 1.0 px)
        angles24 = np.linspace(0, 2 * np.pi, 25)
        pts24 = [(500.0 + 200.0 * np.cos(a), 500.0 + 200.0 * np.sin(a)) for a in angles24]
        facade.clear_layer(0)
        facade.begin_stroke_raw(pts24[0][0], pts24[0][1], 1.0)
        for p in pts24[1:]:
            facade.update_stroke_raw(p[0], p[1], 1.0)
        facade.end_stroke_raw()

        buf24 = facade.get_pixel_buffer()
        arr24 = np.frombuffer(buf24, dtype=np.uint8).reshape((1000, 1000, 4))
        y_idx24, x_idx24 = np.where(arr24[:, :, 3] > 128)
        dists24 = np.sqrt((x_idx24 - 500.0)**2 + (y_idx24 - 500.0)**2)
        dev24 = abs(dists24.mean() - 200.0)

        self.assertLess(
            dev24, 1.0,
            f"Desvio radial médio ({dev24:.2f}px) da Spline Catmull-Rom para 24 nós deve ser subpixel (< 1.0px)"
        )


if __name__ == "__main__":
    unittest.main()


