from pathlib import Path

from tests import run_all_tests


def test_document_coverage_writer_targets_the_document_boundary(tmp_path, monkeypatch):
    monkeypatch.setattr(run_all_tests, "PROJECT_ROOT", str(tmp_path))
    session, output = run_all_tests.write_document_coverage()
    assert Path(output) == tmp_path / "build" / "coverage" / "document.json"
    assert session.config.source == [str(tmp_path / "ui" / "core" / "document")]
