"""A suíte roda com o mesmo ambiente na máquina do dono e nos agentes.

Em 2026-09-25 `test_recording_plugin_activation` passava no Linux do agente e
falhava no Windows do dono: lá o pytest-qt estava instalado e reprova exceção
levantada dentro de um slot do Qt; aqui não estava, e a exceção só era
impressa. Consertar o teste revelou uma queda de verdade (a barra flutuante da
gravação deixava o filtro de eventos no canvas). O pytest-qt entrou no
`requirements-dev`; sem ele a suíte volta a esconder esse tipo de erro.
"""
from __future__ import annotations


def test_pytest_qt_reports_exceptions_raised_inside_qt_slots(pytestconfig):
    assert pytestconfig.pluginmanager.has_plugin("pytest-qt"), (
        "pytest-qt ausente: exceção dentro de slot do Qt passaria em silêncio. "
        "Instale: python -m pip install -r requirements-dev.txt"
    )
