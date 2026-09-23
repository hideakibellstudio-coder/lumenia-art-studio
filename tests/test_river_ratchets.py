"""
test_river_ratchets.py
======================
Catracas das Leis do Leito do Rio: a contagem pode cair, nunca subir sem que
alguém decida conscientemente (editando a lista abaixo, com motivo).

1. Guardas `hasattr(<motor nativo>, "metodo")` no adaptador.
   Cada guarda existe para um único cenário: rodar a UI contra um `.pyd`
   compilado ANTES do método existir. Fora disso ela só esconde erro -- foi
   assim que `render_stroke_preview` sumiu do motor em 2026-08-25 e o painel
   de pincel passou 4 semanas mostrando uma aproximação vetorial sem ninguém
   notar. Guarda nova só entra nesta lista com decisão explícita.
2. Varredura cega da árvore de widgets (`topLevelWidgets`,
   `parent().parent()`) em ui/ e plugins/ -- use ui/core/plugins/canvas_access.
3. Caminhos absolutos de máquina (ex.: `Z:\\...`) em código ou testes.
"""

from __future__ import annotations

import ast
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (arquivo, metodo) -> motivo. Revisado em 2026-09-22 (ver
# claude/analise-completa-projeto-2026-09-22.md no Project, seção hasattr).
NATIVE_GUARDS_PERMITIDOS: dict[tuple[str, str], str] = {
    ("aladyn_stroke_mixin.py", "begin_stroke_raw"): "fast-path raw vs facade legado (test_stroke_characterization)",
    ("aladyn_stroke_mixin.py", "update_stroke_raw"): "idem",
    ("aladyn_stroke_mixin.py", "end_stroke_raw"): "idem",
    ("aladyn_stroke_mixin.py", "is_telemetry_enabled"): "telemetria opcional em builds antigos",
    ("aladyn_stroke_mixin.py", "flood_fill"): "balde de tinta em builds antigos",
    ("aladyn_geometry_mixin.py", "set_curvilinear_guide_config"): "snap curvilinear nativo (recente)",
    ("aladyn_geometry_mixin.py", "get_curvilinear_candidates"): "idem",
    ("aladyn_geometry_mixin.py", "snap_curvilinear"): "idem",
    ("aladyn_geometry_mixin.py", "snap_perspective"): "idem",
    ("aladyn.py", "get_display_pixel_buffer"): "buffer de exibição (LOD) em builds antigos",
    ("aladyn.py", "get_best_lod_level"): "LOD em builds antigos",
    ("aladyn.py", "refresh_display"): "PENDENTE DE DECISÃO (2026-09-22)",
    ("aladyn_mdi_mixin.py", "set_render_options"): "PENDENTE DE DECISÃO (2026-09-22) -- único ponto, _push_render_options",
    ("aladyn_brush_mixin.py", "render_stroke_preview"): "preview nativo do pincel (restaurado 2026-09-22)",
    ("aladyn_capabilities_mixin.py", "<dinâmico>"): "detector de capacidades: pergunta ao binário o que ele tem",
}

_NATIVE_RECEIVERS = {"self._facade", "facade", "self._native", "native", "f"}


def _guardas_nativas() -> Counter:
    achados: Counter = Counter()
    for path in (ROOT / "ui" / "engine_backends").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "hasattr"):
                continue
            if len(node.args) != 2 or ast.unparse(node.args[0]) not in _NATIVE_RECEIVERS:
                continue
            alvo = node.args[1]
            nome = alvo.value if isinstance(alvo, ast.Constant) else "<dinâmico>"
            if nome == "ColorRGBA":
                continue
            achados[(path.name, nome)] += 1
    return achados


def test_guardas_hasattr_no_motor_so_da_lista_aprovada():
    achados = _guardas_nativas()
    novos = sorted(set(achados) - set(NATIVE_GUARDS_PERMITIDOS))
    assert not novos, (
        "Guarda hasattr nova sobre o motor nativo: "
        f"{novos}. Se o método está no .pyi, chame direto (o teste .pyi x binário "
        "garante que ele existe). Se é mesmo fallback para .pyd antigo, adicione "
        "em NATIVE_GUARDS_PERMITIDOS com o motivo."
    )


def test_lista_de_guardas_nao_tem_entradas_mortas():
    mortas = sorted(set(NATIVE_GUARDS_PERMITIDOS) - set(_guardas_nativas()))
    assert not mortas, f"Remova da lista (a guarda já não existe no código): {mortas}"


# findChild/findChildren DENTRO do próprio widget (ex.: um diálogo instalando
# eventFilter nos seus filhos) é introspecção local e continua permitido; o que
# a lei proíbe é sair do próprio componente para achar outro.
_VARREDURA_CEGA = re.compile(r"\.topLevelWidgets\(|parent\(\)\.parent\(\)")


def test_sem_varredura_cega_da_arvore_de_widgets():
    ofensores = []
    for base in ("ui", "plugins"):
        for path in (ROOT / base).rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and _VARREDURA_CEGA.search(ast.unparse(node.func) + "("):
                    ofensores.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert not ofensores, (
        "Varredura cega da árvore de widgets (Lei do Rio nº 3). Use "
        f"ui/core/plugins/canvas_access.py ou o WorkspaceService: {ofensores}"
    )


# Diretórios de sistema do Windows (perfis ICC em C:\Windows\...) são exceção.
_CAMINHO_DE_MAQUINA = re.compile(r"[A-Za-z]:[\\/](?!Windows)[A-Za-z+ ]", re.IGNORECASE)


def test_sem_caminhos_absolutos_de_maquina():
    ofensores = []
    for base in ("ui", "plugins", "tests", "scripts"):
        for path in (ROOT / base).rglob("*.py"):
            if "__pycache__" in path.parts or path.name == Path(__file__).name:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if _CAMINHO_DE_MAQUINA.match(node.value):
                        ofensores.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert not ofensores, f"Caminho absoluto de máquina em código versionado: {ofensores}"


_SINGLETONS = (
    "ThemeManager", "I18nManager", "EngineRegistry", "ConfigManager", "ShortcutRegistry",
    "PluginManager", "DocumentManager",
)


def test_sinais_de_singleton_nao_ligam_lambda():
    """Lambda num sinal de singleton sobrevive ao widget que ele captura.

    O PySide desconecta automaticamente um MÉTODO ligado quando o QObject dono
    é destruído, mas não um lambda. Resultado: o singleton segura o widget morto
    (vazamento) e, no próximo sinal, chama nele e levanta "Internal C++ object
    already deleted" -- achado em 2026-09-22 no RenderWidget (troca de idioma
    após fechar um documento). Use `.connect(self.metodo)`.
    """
    ofensores = []
    for base in ("ui", "plugins"):
        for path in (ROOT / base).rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            aliases = set()
            for node in ast.walk(tree):
                if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                        and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "instance"
                        and ast.unparse(node.value.func.value).split(".")[-1] in _SINGLETONS):
                    aliases.update(ast.unparse(t) for t in node.targets)
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "connect" and node.args and isinstance(node.args[0], ast.Lambda)
                        and isinstance(node.func.value, ast.Attribute)):
                    dono = ast.unparse(node.func.value.value)
                    if dono in aliases or any(s in dono for s in _SINGLETONS):
                        ofensores.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert not ofensores, f"Lambda ligado a sinal de singleton: {ofensores}"
