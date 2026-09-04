"""
Algoritmos de Estabilização e Cinemática de Traço para o StabilizerLabPlugin.
=============================================================================
Implementações de alta fidelidade das abordagens:
1. AdaptiveProfileStabilizerEngine: Motor por Perfis Dinâmicos com diluição perceptual
   linear (sem zonas mortas), buffer proporcional e inércia geométrica contínua.
2. SaiStabilizerEngine: Buffer circular clássico com níveis e expoente gamma.
3. InfinitePainterKalmanEngine: Filtro de Kalman 4D com Forma de Joseph e Jerk ^ 8.
4. LumeniaBaselineEngine: Implementação antiga de referência para comparação direta.
"""

from __future__ import annotations
import math
from typing import List, Tuple
from ui.core.engine.stabilizer_hub import StabilizerHub


# ══════════════════════════════════════════════════════════════════════
# 1. ADAPTIVE PROFILE STABILIZER ENGINE (NOVA ARQUITETURA DILUÍDA)
# ══════════════════════════════════════════════════════════════════════

class AdaptiveProfileStabilizerEngine:
    """
    Motor por Perfis Adaptativos (Direto, Fluido, Pintura, Lineart, Contorno Esculpido e Fita de Seda).
    Elimina a zona morta de 0 a 80%: cada incremento do slider de 0% a 100% surte efeito físico perceptível.
    """

    def __init__(self) -> None:
        self.history: list[tuple[float, float, float]] = []
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_p = 1.0
        self.has_started = False

    def reset(self, x: float, y: float, pressure: float) -> None:
        self.current_x = x
        self.current_y = y
        self.current_p = pressure
        self.history = [(x, y, pressure)]
        self.has_started = True

    def update(self, x: float, y: float, pressure: float) -> tuple[float, float, float]:
        if not self.has_started:
            self.reset(x, y, pressure)
            return x, y, pressure

        params = StabilizerHub.instance().get_calculated_params()
        if params["profile_id"] == "off" or params["buffer_capacity"] <= 1:
            self.current_x = x
            self.current_y = y
            self.current_p = pressure
            return x, y, pressure

        cap = params["buffer_capacity"]
        alpha = params["alpha"]
        gamma = params["gamma"]
        smooth_p = params["smooth_pressure"]

        # 1. Acúmulo no buffer linear
        self.history.append((x, y, pressure))
        if len(self.history) > cap:
            self.history.pop(0)

        # 2. Núcleo Ponderado Parabólico com expoente calibrado do perfil
        sum_w = 0.0
        target_x = 0.0
        target_y = 0.0
        target_p = 0.0

        for i, (hx, hy, hp) in enumerate(self.history):
            w = math.pow(float(i + 1), gamma)
            sum_w += w
            target_x += hx * w
            target_y += hy * w
            target_p += hp * w

        if sum_w > 1e-6:
            target_x /= sum_w
            target_y /= sum_w
            target_p /= sum_w

        # 3. Inércia Elástica Trailing Spring Diluída
        self.current_x += alpha * (target_x - self.current_x)
        self.current_y += alpha * (target_y - self.current_y)

        if smooth_p:
            self.current_p += alpha * (target_p - self.current_p)
        else:
            self.current_p = pressure

        return self.current_x, self.current_y, self.current_p

    def flush(self) -> list[tuple[float, float, float]]:
        """Drena assintoticamente o amortecedor elástico no Pen Up até convergir no ponto final (< 0.25px)."""
        if not self.has_started or not self.history:
            return []

        params = StabilizerHub.instance().get_calculated_params()
        if params["profile_id"] == "off" or params["buffer_capacity"] <= 1:
            self.has_started = False
            self.history.clear()
            return []

        target_x, target_y, target_p = self.history[-1]
        alpha = params["alpha"]
        flush_speed = params.get("flush_speed", 1.0)
        smooth_p = params["smooth_pressure"]

        flush_pts: list[tuple[float, float, float]] = []
        MAX_STEPS = min(60, int(params["buffer_capacity"] * 1.2 + 10))

        for _ in range(MAX_STEPS):
            dx = target_x - self.current_x
            dy = target_y - self.current_y
            dist = math.hypot(dx, dy)

            if dist < 0.25:
                flush_pts.append((target_x, target_y, target_p))
                break

            close_alpha = max(0.12, min(0.92, alpha * 2.0 * flush_speed))
            self.current_x += close_alpha * (target_x - self.current_x)
            self.current_y += close_alpha * (target_y - self.current_y)
            if smooth_p:
                self.current_p += close_alpha * (target_p - self.current_p)
            else:
                self.current_p = target_p

            flush_pts.append((self.current_x, self.current_y, self.current_p))

        self.has_started = False
        self.history.clear()
        return flush_pts


# ══════════════════════════════════════════════════════════════════════
# 2. LUMENIA BASELINE ENGINE (REFERÊNCIA ANTIGA)
# ══════════════════════════════════════════════════════════════════════

class LumeniaBaselineEngine:
    """Implementação clássica original com rampa quadrática (para comparação direta)."""

    MAX_WINDOW_SIZE = 32

    def __init__(self, percentage: float = 40.0, weight_exponent: float = 1.25) -> None:
        self.percentage = max(0.0, min(99.0, percentage))
        self.weight_exponent = max(0.5, min(3.0, weight_exponent))
        self.history: list[tuple[float, float]] = []
        self.current_out_x = 0.0
        self.current_out_y = 0.0
        self.has_started = False

    def reset(self, x: float, y: float, pressure: float) -> None:
        self.current_out_x = x
        self.current_out_y = y
        self.history = [(x, y)]
        self.has_started = True

    def update(self, x: float, y: float, pressure: float) -> tuple[float, float, float]:
        if not self.has_started:
            self.reset(x, y, pressure)
            return x, y, pressure

        if self.percentage <= 0.5:
            self.current_out_x = x
            self.current_out_y = y
            return x, y, pressure

        norm = self.percentage / 100.0
        curved = norm * norm  # Rampa quadrática

        max_window = max(2, min(self.MAX_WINDOW_SIZE, int(2 + curved * (self.MAX_WINDOW_SIZE - 2))))
        self.history.append((x, y))
        if len(self.history) > max_window:
            self.history.pop(0)

        n = len(self.history)
        sum_x = 0.0
        sum_y = 0.0
        total_w = 0.0
        for i, (hx, hy) in enumerate(self.history):
            w = math.pow(float(i + 1), self.weight_exponent)
            sum_x += hx * w
            sum_y += hy * w
            total_w += w

        avg_x = (sum_x / total_w) if total_w > 0.0 else x
        avg_y = (sum_y / total_w) if total_w > 0.0 else y

        interp = max(0.035, min(1.0, math.pow(1.0 - norm * 0.92, 1.6)))
        self.current_out_x += (avg_x - self.current_out_x) * interp
        self.current_out_y += (avg_y - self.current_out_y) * interp

        return self.current_out_x, self.current_out_y, pressure

    def flush(self, steps: int = 3) -> list[tuple[float, float, float]]:
        if not self.has_started or not self.history or self.percentage <= 0.5 or steps <= 0:
            return []
        end_x, end_y = self.history[-1]
        pts: list[tuple[float, float, float]] = []
        for i in range(1, steps + 1):
            t = i / float(steps)
            smooth_t = t * t * (3.0 - 2.0 * t)
            px = self.current_out_x + (end_x - self.current_out_x) * smooth_t
            py = self.current_out_y + (end_y - self.current_out_y) * smooth_t
            pts.append((px, py, 0.0))
        self.current_out_x = end_x
        self.current_out_y = end_y
        return pts


# ══════════════════════════════════════════════════════════════════════
# 3. PAINT TOOL SAI VER. 2 (NÍVEIS NUMÉRICOS DIRETOS)
# ══════════════════════════════════════════════════════════════════════

class SaiStabilizerEngine:
    def __init__(self, level: int = 5, gamma: float = 1.4, smooth_pressure: bool = True) -> None:
        self.level = max(0, min(22, level))
        self.gamma = max(1.0, min(2.5, gamma))
        self.smooth_pressure = smooth_pressure
        self.flush_speed = 1.0

        self.history: list[tuple[float, float, float]] = []
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_p = 1.0
        self.has_started = False
        self._update_coefficients()

    def _update_coefficients(self) -> None:
        l = self.level
        if l == 0:
            self.buffer_capacity = 1
            self.alpha = 1.0
        elif l <= 15:
            self.buffer_capacity = int(2 + l * 1.7)
            self.alpha = 1.0 / (1.0 + l * 0.30)
        else:
            s_index = l - 15
            self.buffer_capacity = int(25 + s_index * 16.5)
            self.alpha = 1.0 / (6.0 + s_index * 4.2)

    def set_level(self, level: int) -> None:
        self.level = max(0, min(22, level))
        self._update_coefficients()

    def reset(self, x: float, y: float, pressure: float) -> None:
        self.current_x = x
        self.current_y = y
        self.current_p = pressure
        self.history = [(x, y, pressure)]
        self.has_started = True

    def update(self, x: float, y: float, pressure: float) -> tuple[float, float, float]:
        if not self.has_started:
            self.reset(x, y, pressure)
            return x, y, pressure

        if self.level == 0:
            self.current_x = x
            self.current_y = y
            self.current_p = pressure
            return x, y, pressure

        self.history.append((x, y, pressure))
        if len(self.history) > self.buffer_capacity:
            self.history.pop(0)

        sum_w = 0.0
        target_x = 0.0
        target_y = 0.0
        target_p = 0.0

        for i, (hx, hy, hp) in enumerate(self.history):
            w = math.pow(float(i + 1), self.gamma)
            sum_w += w
            target_x += hx * w
            target_y += hy * w
            target_p += hp * w

        if sum_w > 1e-6:
            target_x /= sum_w
            target_y /= sum_w
            target_p /= sum_w

        self.current_x += self.alpha * (target_x - self.current_x)
        self.current_y += self.alpha * (target_y - self.current_y)

        if self.smooth_pressure:
            self.current_p += self.alpha * (target_p - self.current_p)
        else:
            self.current_p = pressure

        return self.current_x, self.current_y, self.current_p

    def flush(self) -> list[tuple[float, float, float]]:
        if not self.has_started or not self.history or self.level == 0:
            return []

        target_x, target_y, target_p = self.history[-1]
        flush_pts: list[tuple[float, float, float]] = []
        MAX_STEPS = 35

        for _ in range(MAX_STEPS):
            dx = target_x - self.current_x
            dy = target_y - self.current_y
            dist = math.hypot(dx, dy)

            if dist < 0.25:
                flush_pts.append((target_x, target_y, target_p))
                break

            close_alpha = max(0.15, min(0.90, self.alpha * 2.0 * self.flush_speed))
            self.current_x += close_alpha * (target_x - self.current_x)
            self.current_y += close_alpha * (target_y - self.current_y)
            if self.smooth_pressure:
                self.current_p += close_alpha * (target_p - self.current_p)
            else:
                self.current_p = target_p

            flush_pts.append((self.current_x, self.current_y, self.current_p))

        self.has_started = False
        self.history.clear()
        return flush_pts


# ══════════════════════════════════════════════════════════════════════
# 4. INFINITE PAINTER (BRAKEFIELD) KALMAN 4D
# ══════════════════════════════════════════════════════════════════════

class SingleAxisKalman4D:
    def __init__(self, sigma_process: float = 0.01, sigma_measurement: float = 1.0) -> None:
        self.sigma_process = sigma_process
        self.sigma_measurement = sigma_measurement
        self.reset(0.0)

    def reset(self, initial_val: float = 0.0) -> None:
        self.x = [initial_val, 0.0, 0.0, 0.0]
        self.P = [[1.0 if r == c else 0.0 for c in range(4)] for r in range(4)]
        self.F = [
            [1.0, 1.0, 0.5, 0.16],
            [0.0, 1.0, 1.0, 0.5],
            [0.0, 0.0, 1.0, 1.0],
            [0.0, 0.0, 0.0, 1.0]
        ]
        G = [0.16, 0.5, 1.0, 1.0]
        self.Q = [[self.sigma_process * G[r] * G[c] for c in range(4)] for r in range(4)]
        self.R = self.sigma_measurement

    def set_parameters(self, sigma_process: float, sigma_measurement: float) -> None:
        self.sigma_process = sigma_process
        self.sigma_measurement = sigma_measurement
        G = [0.16, 0.5, 1.0, 1.0]
        self.Q = [[self.sigma_process * G[r] * G[c] for c in range(4)] for r in range(4)]
        self.R = self.sigma_measurement

    def update(self, measurement: float) -> float:
        x_pred = [0.0] * 4
        for r in range(4):
            for c in range(4):
                x_pred[r] += self.F[r][c] * self.x[c]

        FP = [[0.0] * 4 for _ in range(4)]
        for r in range(4):
            for c in range(4):
                for k in range(4):
                    FP[r][c] += self.F[r][k] * self.P[k][c]

        P_pred = [[0.0] * 4 for _ in range(4)]
        for r in range(4):
            for c in range(4):
                s = 0.0
                for k in range(4):
                    s += FP[r][k] * self.F[c][k]
                P_pred[r][c] = s + self.Q[r][c]

        y = measurement - x_pred[0]
        S = P_pred[0][0] + self.R
        inv_S = 1.0 / S if abs(S) > 1e-9 else 1.0

        K = [P_pred[r][0] * inv_S for r in range(4)]

        for r in range(4):
            self.x[r] = x_pred[r] + K[r] * y

        I_KH = [[1.0 if r == c else 0.0 for c in range(4)] for r in range(4)]
        for r in range(4):
            I_KH[r][0] -= K[r]

        temp = [[0.0] * 4 for _ in range(4)]
        for r in range(4):
            for c in range(4):
                for k in range(4):
                    temp[r][c] += I_KH[r][k] * P_pred[k][c]

        for r in range(4):
            for c in range(4):
                s = 0.0
                for k in range(4):
                    s += temp[r][k] * I_KH[c][k]
                self.P[r][c] = s + K[r] * self.R * K[c]

        return self.x[0]


class InfinitePainterKalmanEngine:
    def __init__(self, sigma_process: float = 0.01, sigma_measurement: float = 1.0, jerk_exponent: float = 8.0) -> None:
        self.sigma_process = sigma_process
        self.sigma_measurement = sigma_measurement
        self.jerk_exponent = jerk_exponent

        self.kalman_x = SingleAxisKalman4D(sigma_process, sigma_measurement)
        self.kalman_y = SingleAxisKalman4D(sigma_process, sigma_measurement)
        self.pressure_ema = 0.25
        self.current_pressure = 1.0

        self.has_started = False
        self.last_jerk_norm = 0.0
        self.last_vel_norm = 0.0

    def set_parameters(self, sigma_process: float, sigma_measurement: float, jerk_exp: float, p_ema: float) -> None:
        self.sigma_process = sigma_process
        self.sigma_measurement = sigma_measurement
        self.jerk_exponent = max(1.0, min(16.0, jerk_exp))
        self.pressure_ema = max(0.05, min(1.0, p_ema))
        self.kalman_x.set_parameters(sigma_process, sigma_measurement)
        self.kalman_y.set_parameters(sigma_process, sigma_measurement)

    def reset(self, x: float, y: float, pressure: float) -> None:
        self.kalman_x.reset(x)
        self.kalman_y.reset(y)
        self.current_pressure = pressure
        self.has_started = True
        self.last_jerk_norm = 0.0
        self.last_vel_norm = 0.0

    def update(self, x: float, y: float, pressure: float) -> tuple[float, float, float]:
        if not self.has_started:
            self.reset(x, y, pressure)
            return x, y, pressure

        fx = self.kalman_x.update(x)
        fy = self.kalman_y.update(y)

        self.current_pressure += (pressure - self.current_pressure) * self.pressure_ema

        vx = self.kalman_x.x[1]
        vy = self.kalman_y.x[1]
        jx = self.kalman_x.x[3]
        jy = self.kalman_y.x[3]
        self.last_vel_norm = math.hypot(vx, vy)
        self.last_jerk_norm = math.hypot(jx, jy)

        j_norm_clamped = max(0.0, min(1.0, (self.last_jerk_norm - 0.02) / 0.98))
        jerk_damping = math.pow(max(0.0, 1.0 - j_norm_clamped), self.jerk_exponent)

        blend = jerk_damping
        final_x = fx * blend + x * (1.0 - blend)
        final_y = fy * blend + y * (1.0 - blend)

        return final_x, final_y, self.current_pressure

    def flush(self) -> list[tuple[float, float, float]]:
        self.has_started = False
        return []
