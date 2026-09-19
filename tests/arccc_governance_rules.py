"""
arccc_governance_rules.py
=========================
FONTE ÚNICA das regras quantitativas ARCcC usadas pelos testes de governança.

Motivo (F-018 da auditoria pre-Fase 3): o mesmo teto de LOC estava escrito em
tres lugares, com tres valores diferentes:

  - `tests/test_arccc_architecture_invariants.py` .... 500 (so Python, sem excecoes)
  - `tests/test_arccc_cpp_and_docs_governance.py` .... 500 (so C++, sem excecoes)
  - perfil `lumenia` do ARCcC-Navigator ............. 450 (Python + C++, com excecoes)

E o `AGENTS.md` — a regra canonica do projeto — define Zona Vermelha como
`>= 450 linhas`, classificada como "VIOLACAO GRAVE DE ENTREGA". Ou seja, os
testes eram mais frouxos que a propria regra documentada, e discordavam entre
si. Um projeto nao pode ter tres definicoes do mesmo invariante: qualquer uma
delas passando da a falsa sensacao de conformidade.

Este modulo passa a ser o unico lugar onde esses numeros existem. Alterar o
teto aqui muda os dois testes de uma vez, e os valores batem com o perfil do
Navigator — entao o teste local e a auditoria do Navigator nunca mais podem
discordar sobre o que e uma violacao.

Nao comeca com `test_`, entao nao e coletado como suite de testes.
"""
from __future__ import annotations

# Zonas quantitativas, identicas a AGENTS.md e ao LUMENIA_PROFILE do Navigator.
MAX_LINES_WARN = 300   # Zona Amarela: >= 300 linhas
MAX_LINES_ERROR = 450  # Zona Vermelha: >= 450 linhas (violacao)

# Excecoes formais, espelhando `declared_exceptions` do perfil `lumenia`.
# Cada entrada precisa de uma razao explicita: uma excecao sem justificativa
# escrita e indistinguivel de um teto simplesmente ignorado.
DECLARED_LOC_EXCEPTIONS: dict[str, str] = {
    "engine/boundary/public-api/internal/StrokeOrchestrator.cpp":
        "Pipeline nativo de orquestracao de traco",
    "engine/core/raster/SelectionEngine.cpp":
        "Algoritmos nativos de mascara de selecao em raster",
    "engine/core/raster/TransformEngine.cpp":
        "Transformadas afins nativas de matriz em raster",
}


def normalize(rel_path: str) -> str:
    """Normaliza separadores para comparacao entre Windows e POSIX."""
    return rel_path.replace("\\", "/")


def is_declared_exception(rel_path: str) -> bool:
    """True se o arquivo tem excecao formal de teto de linhas."""
    return normalize(rel_path) in DECLARED_LOC_EXCEPTIONS


def exception_reason(rel_path: str) -> str:
    return DECLARED_LOC_EXCEPTIONS.get(normalize(rel_path), "")
