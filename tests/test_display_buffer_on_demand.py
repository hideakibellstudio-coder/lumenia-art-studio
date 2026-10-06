"""O buffer de exibição só ocupa memória enquanto há um perfil de cor que não é sRGB (S1).

Até 2026-10-02 todo canvas nascia com dois buffers do tamanho dele: o de saída (o que a tela lê no perfil sRGB)
e o de exibição (a cópia convertida para outros perfis). No sRGB o segundo nunca era lido: 1 GiB de RAM sem uso
num canvas de 16384², 256 MiB em 8192². Agora ele nasce vazio, ganha o tamanho do canvas na primeira leitura
com perfil e volta a zero quando o perfil volta ao sRGB. O que a tela mostra não muda: quem garante isso é
test_lod_pyramid_damage.py (pirâmide com perfil, depois de cada operação e depois de trocas de perfil e de
tamanho); aqui só a memória, lida de /proc (só no Linux).
"""

from __future__ import annotations

import os

import numpy as np
import pytest

native = pytest.importorskip("aladyn_engine_native", reason="módulo nativo não compilado neste ambiente")

pytestmark = pytest.mark.skipif(not os.path.exists("/proc/self/status"), reason="lê a memória do processo em /proc")

SIDE = 6144                                  # 144 MiB por buffer de canvas inteiro
BUFFER_MB = SIDE * SIDE * 4 / 2**20


def _rss_mb() -> float:
    with open("/proc/self/status", encoding="utf-8") as status:
        for line in status:
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024.0
    raise AssertionError("VmRSS ausente")


def test_a_new_canvas_holds_one_full_size_buffer_not_two():
    before = _rss_mb()
    engine = native.PaintEngineFacade(SIDE, SIDE)
    grown = _rss_mb() - before
    # saída + máscara de seleção (1 byte por pixel) = 1,25 buffers; antes eram 2,25.
    assert grown < 1.6 * BUFFER_MB, f"{grown:.0f} MB para um canvas de {BUFFER_MB:.0f} MB por buffer"
    assert engine.get_width() == SIDE


def test_the_display_buffer_appears_with_a_colour_profile_and_goes_away_with_srgb():
    engine = native.PaintEngineFacade(SIDE, SIDE)
    plain = _rss_mb()
    engine.set_color_profile(3)
    shown = np.frombuffer(engine.get_display_region(0, 0, 4, 4), dtype=np.uint8)  # região: não aloca o buffer inteiro
    assert _rss_mb() - plain < 0.2 * BUFFER_MB
    engine.get_display_pixel_buffer()                                              # o canvas inteiro com o perfil
    assert _rss_mb() - plain > 0.8 * BUFFER_MB, "o buffer de exibição deveria ter sido alocado"
    engine.set_color_profile(0)
    assert _rss_mb() - plain < 0.2 * BUFFER_MB, "de volta ao sRGB a memória deveria voltar ao sistema"
    assert shown.size == 4 * 4 * 4
