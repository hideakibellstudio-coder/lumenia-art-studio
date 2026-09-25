"""Relatório de testes com números medidos (JUnit XML), não fixos.

Até 2026-09-24 o diálogo mostrava "110 testes", "100%", "SIMD AVX2 Ativo" e
"APROVADO" em todas as seções, sem relação com a execução.
"""
from tests.run_all_tests import build_pytest_args
from ui.core.dialogs.test_report_dialog import TestReportDialog
from ui.core.dialogs.test_report_model import SECTIONS, parse_junit, section_of
from ui.infrastructure.i18n import tr

JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" tests="5">
  <testcase classname="tests.test_lowlevel_blend_modes.TestBlend" name="test_a"/>
  <testcase classname="tests.test_lowlevel_blend_modes.TestBlend" name="test_b"><failure message="x"/></testcase>
  <testcase classname="tests.test_arccc_package_docs" name="test_c"/>
  <testcase classname="tests.test_theme_tweaks" name="test_d"><skipped message="s"/></testcase>
  <testcase classname="tests.test_something_else" name="test_e"><error message="e"/></testcase>
</testsuite></testsuites>
"""


def test_secoes_por_arquivo_de_teste():
    assert section_of("test_lowlevel_blend_modes") == "section_native"
    assert section_of("test_arccc_coupling_ratchet") == "section_arccc"
    assert section_of("test_dialogs_i18n") == "section_i18n"
    assert section_of("test_qualquer_outro") == SECTIONS[-1][0]


def test_junit_vira_contagens_por_secao(tmp_path):
    path = tmp_path / "junit.xml"
    path.write_text(JUNIT, encoding="utf-8")
    report = parse_junit(str(path))
    assert (report.total.passed, report.total.failed, report.total.skipped) == (2, 2, 1)
    assert report.pass_rate == 50.0
    native = report.sections["section_native"]
    assert (native.passed, native.failed) == (1, 1)
    assert report.sections["section_ui"].failed == 1  # erro conta como falha
    assert report.sections["section_themes"].skipped == 1


def test_dialogo_mostra_so_o_que_foi_medido(qapp, tmp_path):
    dialog = TestReportDialog()
    try:
        values = [value.text() for _card, _title, value, _key, _default in dialog.kpi_cards]
        assert values == ["—"] * 4  # antes de executar, nada inventado
        assert {dialog.table.item(row, 1).text() for row in range(dialog.table.rowCount())} == {"—"}

        path = tmp_path / "junit.xml"
        path.write_text(JUNIT, encoding="utf-8")
        dialog.show_report(parse_junit(str(path)))
        values = [value.text() for _card, _title, value, _key, _default in dialog.kpi_cards]
        assert values == ["5", "50.0%", "2", "1"]
        statuses = {key: dialog.table.item(row, 1).text() for row, (key, _t, _p) in enumerate(SECTIONS)}
        assert statuses["section_native"] == tr("test_report.failed", "FALHOU")
        assert statuses["section_arccc"] == tr("test_report.passed", "APROVADO")
        assert statuses["section_layers"] == "—"  # sem testes nesta execução
    finally:
        dialog.deleteLater()


def test_runner_grava_junit_quando_pedido(tmp_path):
    assert build_pytest_args(str(tmp_path), "full", "r.xml") == [str(tmp_path), "-q", "--junitxml=r.xml"]
    assert build_pytest_args(str(tmp_path), "full") == [str(tmp_path), "-q"]
