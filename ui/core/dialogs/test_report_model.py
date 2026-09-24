"""test_report_model — resultado medido da suíte de testes, para o relatório.

Lê o JUnit XML que o pytest grava (`tests/run_all_tests.py --junit ARQUIVO`)
e agrupa os testes nas seções do relatório pelo nome do arquivo de teste.
Até 2026-09-24 o diálogo mostrava valores fixos ("110 testes", "100%",
"SIMD AVX2 Ativo" e "APROVADO" em todas as linhas), sem relação com a
execução.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

# (chave de tradução, título padrão, prefixos dos arquivos de teste). A
# primeira seção cujo prefixo casa fica com o teste; a última pega o resto.
SECTIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("section_native", "1. Motor Nativo ALADYN C++20",
     ("test_lowlevel_", "test_native_", "test_giant_brush", "test_buffer_contract", "test_stroke_")),
    ("section_arccc", "2. Arquitetura ARCcC & Invariantes AST",
     ("test_arccc_", "test_river_", "test_hardcoded_colors", "test_engine_document_boundary")),
    ("section_layers", "3. Camadas & Grupos Hierárquicos",
     ("test_layer", "test_document_history", "test_history")),
    ("section_mdi", "4. Multi-Documento MDI & Memória",
     ("test_mdi", "test_document", "test_persistence", "test_recovery")),
    ("section_selection", "5. Sistema de Seleção & Transformação",
     ("test_selection", "test_transform", "test_geometry")),
    ("section_themes", "6. Sistema de Temas & Dinamismo QSS", ("test_theme", "test_dialogs_theme")),
    ("section_i18n", "7. Sistema de Internacionalização i18n", ("test_dialogs_i18n", "test_i18n")),
    ("section_ui", "8. Diálogos de UI & MenuBar", ()),
)


@dataclass
class Counts:
    passed: int = 0
    failed: int = 0   # falhas e erros
    skipped: int = 0

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.skipped

    def add(self, outcome: str) -> None:
        if outcome == "passed":
            self.passed += 1
        elif outcome == "failed":
            self.failed += 1
        else:
            self.skipped += 1


@dataclass
class SuiteReport:
    total: Counts = field(default_factory=Counts)
    sections: dict[str, Counts] = field(default_factory=lambda: {key: Counts() for key, _t, _p in SECTIONS})

    @property
    def pass_rate(self) -> float:
        ran = self.total.passed + self.total.failed
        return 100.0 * self.total.passed / ran if ran else 0.0


def section_of(test_file: str) -> str:
    for key, _title, prefixes in SECTIONS:
        if any(test_file.startswith(prefix) for prefix in prefixes):
            return key
    return SECTIONS[-1][0]


def _test_file(classname: str) -> str:
    """'tests.test_x.TestY' ou 'tests.test_x' -> 'test_x'."""
    return next((part for part in classname.split(".") if part.startswith("test_")), classname)


def _outcome(case: ET.Element) -> str:
    if case.find("failure") is not None or case.find("error") is not None:
        return "failed"
    if case.find("skipped") is not None:
        return "skipped"
    return "passed"


def parse_junit(path: str) -> SuiteReport:
    """Resultado por teste do JUnit XML do pytest (levanta erro se o arquivo não existir)."""
    report = SuiteReport()
    for case in ET.parse(path).getroot().iter("testcase"):
        outcome = _outcome(case)
        report.total.add(outcome)
        report.sections[section_of(_test_file(case.get("classname", "")))].add(outcome)
    return report
