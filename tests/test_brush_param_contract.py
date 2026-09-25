"""
Contrato dos parâmetros de pincel — o motor define, a interface exibe.
=======================================================================
Estes testes existem porque seis controles da interface passaram meses
escrevendo num destino que o motor não tem, sem um único erro visível:

  - `dynamics.jitter_size` e `dynamics.jitter_angle` (dois sliders do painel
    avançado) apontavam para um grupo `dynamics` que nunca existiu nas bindings;
    os campos reais moram em `BrushTip`.
  - `dynamics.jitter_opacity` e `root.scatter_radius` apontavam para campos que
    o motor não tem em lugar nenhum.
  - `root.blend_mode` mandava `int` onde a binding exige o enum `DabBlendMode`,
    lançando `TypeError` dentro de um slot Qt a cada troca de modo.

A causa não foi nenhum desses erros em particular; foi não haver nada que
comparasse a tabela da interface com o módulo compilado. Isto é esse algo.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from ui.infrastructure.bridge_client.brush_param_table import (
    GROUP_ATTRIBUTES,
    METHOD_PARAMS,
    BY_GROUP_AND_ATTRIBUTE,
    BRUSH_PARAMS,
    native_target,
    resolve_param,
)

native = pytest.importorskip(
    "aladyn_engine_native", reason="módulo nativo não compilado neste ambiente"
)

RAIZ = pathlib.Path(__file__).resolve().parents[1]

# Valor de teste por tipo de conversor, escolhido para diferir de qualquer padrão.
TEST_VALUES = {
    "to_float": 0.4271,
    "to_int": 7,
    "to_bool": True,
    "to_blend_mode": 1,
}


@pytest.fixture(scope="module")
def profile():
    return native.PaintEngineFacade(32, 32).get_brush_profile()


# ── 1. Toda linha da tabela existe no módulo compilado ──────────────────────

@pytest.mark.parametrize("spec", BRUSH_PARAMS, ids=lambda p: p.key)
def test_campo_declarado_existe_no_motor(spec, profile):
    target = native_target(profile, spec.group)
    assert target is not None, (
        f"o grupo '{spec.group}' não existe no módulo nativo"
    )
    assert hasattr(target, spec.attribute), (
        f"'{spec.key}' aponta para {spec.group or 'raiz'}.{spec.attribute}, "
        f"que o motor não expõe"
    )


@pytest.mark.parametrize("spec", BRUSH_PARAMS, ids=lambda p: p.key)
def test_escrita_aterrissa_no_motor(spec, profile):
    """Escreve pelo conversor declarado e confere que o motor guardou o valor."""
    value = TEST_VALUES[spec.to_engine.__name__]
    converted = spec.to_engine(value, native)
    target = native_target(profile, spec.group)
    setattr(target, spec.attribute, converted)
    read_back = getattr(target, spec.attribute)
    assert spec.to_preset(read_back) == spec.to_preset(converted), (
        f"'{spec.key}' foi escrito como {converted!r} e lido como {read_back!r}"
    )


# ── 2. Os grupos declarados existem, e só eles ──────────────────────────────

def test_todo_grupo_declarado_existe_no_perfil(profile):
    for group, attribute in GROUP_ATTRIBUTES.items():
        if attribute is None:
            continue
        assert hasattr(profile, attribute), (
            f"o grupo '{group}' mapeia para BrushProfile.{attribute}, "
            f"que não existe no módulo nativo"
        )


def test_metodos_por_metodo_existem_no_backend():
    from ui.infrastructure.bridge_client.aladyn import AladynBackend

    for method_spec in METHOD_PARAMS:
        assert hasattr(AladynBackend, method_spec.method), (
            f"'{method_spec.key}' declara o método '{method_spec.method}', "
            f"ausente do AladynBackend"
        )


# ── 3. Nenhuma chamada da interface usa um par não declarado ────────────────

def _chamadas_literais_a_set_brush_param() -> list[tuple[pathlib.Path, int, str, str]]:
    """Varre o repositório por set_brush_param("grupo", "param", ...) literais."""
    found: list[tuple[pathlib.Path, int, str, str]] = []
    for caminho in list(RAIZ.glob("ui/**/*.py")) + list(RAIZ.glob("plugins/**/*.py")):
        try:
            arvore = ast.parse(caminho.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for no in ast.walk(arvore):
            if not isinstance(no, ast.Call):
                continue
            target = no.func
            nome = target.attr if isinstance(target, ast.Attribute) else getattr(target, "id", None)
            if nome != "set_brush_param" or len(no.args) < 2:
                continue
            group, param = no.args[0], no.args[1]
            if isinstance(group, ast.Constant) and isinstance(param, ast.Constant):
                found.append((caminho, no.lineno, group.value, param.value))
    return found


def test_toda_chamada_da_interface_resolve():
    chamadas = _chamadas_literais_a_set_brush_param()
    assert chamadas, "nenhuma chamada literal encontrada — a varredura quebrou"

    quebradas = []
    for caminho, spec, group, param in chamadas:
        try:
            resolve_param(group, param)
        except KeyError as exc:
            rel = caminho.relative_to(RAIZ)
            quebradas.append(f"{rel}:{spec}  set_brush_param({group!r}, {param!r})\n      {exc.args[0]}")

    assert not quebradas, (
        "chamadas da interface apontam para parâmetros não declarados:\n  "
        + "\n  ".join(quebradas)
    )


# ── 4. O par leitura/escrita é coerente ─────────────────────────────────────

def test_ida_e_volta_preserva_o_estado():
    """get → apply → get deve ser estável: um preset salvo tem que voltar igual."""
    from ui.infrastructure.bridge_client.aladyn import AladynBackend

    backend = AladynBackend()
    if not backend.available:
        pytest.skip("backend nativo indisponível")

    partida = backend.get_brush_profile_dict()
    assert partida, "get_brush_profile_dict devolveu vazio"

    backend.apply_brush_preset_dict(partida)
    chegada = backend.get_brush_profile_dict()

    divergentes = {
        key: (partida[key], chegada.get(key))
        for key in partida
        if key not in chegada or partida[key] != chegada[key]
    }
    assert not divergentes, f"a ida e volta perdeu ou alterou: {divergentes}"


def test_toda_chave_legivel_aparece_na_leitura():
    from ui.infrastructure.bridge_client.aladyn import AladynBackend

    backend = AladynBackend()
    if not backend.available:
        pytest.skip("backend nativo indisponível")

    read_back = backend.get_brush_profile_dict()
    missing = [p.key for p in BRUSH_PARAMS if p.readable and p.key not in read_back]
    assert not missing, (
        f"declarados como legíveis mas ausentes de get_brush_profile_dict: {missing}"
    )


def test_parametro_nao_declarado_falha_alto():
    """A regressão que originou tudo isto: silêncio onde devia haver erro."""
    from ui.infrastructure.bridge_client.aladyn import AladynBackend

    backend = AladynBackend()
    with pytest.raises(KeyError):
        backend.set_brush_param("dynamics", "jitter_size", 0.5)
    with pytest.raises(KeyError):
        backend.set_brush_param("root", "scatter_radius", 3.0)


def test_blend_mode_aceita_indice_da_combo():
    """A combo do painel manda o índice; o motor exige o enum."""
    from ui.infrastructure.bridge_client.aladyn import AladynBackend

    backend = AladynBackend()
    if not backend.available:
        pytest.skip("backend nativo indisponível")

    quantidade = len(native.DabBlendMode.__members__)
    for index in range(quantidade):
        backend.set_brush_param("root", "blend_mode", index)
        assert int(backend._facade.get_brush_profile().blend_mode) == index

    with pytest.raises(ValueError):
        backend.set_brush_param("root", "blend_mode", quantidade + 5)


# ── 5. A tabela é internamente consistente ──────────────────────────────────

def test_chaves_sem_duplicata():
    keys = [p.key for p in BRUSH_PARAMS]
    duplicadas = {c for c in keys if keys.count(c) > 1}
    assert not duplicadas, f"chaves repetidas na tabela: {duplicadas}"


def test_indice_cobre_a_tabela_inteira():
    for spec in BRUSH_PARAMS:
        assert BY_GROUP_AND_ATTRIBUTE[(spec.group, spec.attribute)] is spec
