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

from ui.engine_backends.brush_param_table import (
    ATRIBUTO_DO_GRUPO,
    PARAMS_POR_METODO,
    POR_GRUPO_E_ATRIBUTO,
    TABELA,
    alvo_nativo,
    resolver,
)

native = pytest.importorskip(
    "aladyn_engine_native", reason="módulo nativo não compilado neste ambiente"
)

RAIZ = pathlib.Path(__file__).resolve().parents[1]

# Valor de teste por tipo de conversor, escolhido para diferir de qualquer padrão.
VALORES_DE_TESTE = {
    "para_float": 0.4271,
    "para_int": 7,
    "para_bool": True,
    "para_blend_mode": 1,
}


@pytest.fixture(scope="module")
def perfil():
    return native.PaintEngineFacade(32, 32).get_brush_profile()


# ── 1. Toda linha da tabela existe no módulo compilado ──────────────────────

@pytest.mark.parametrize("linha", TABELA, ids=lambda p: p.chave)
def test_campo_declarado_existe_no_motor(linha, perfil):
    destino = alvo_nativo(perfil, linha.grupo)
    assert destino is not None, (
        f"o grupo '{linha.grupo}' não existe no módulo nativo"
    )
    assert hasattr(destino, linha.atributo), (
        f"'{linha.chave}' aponta para {linha.grupo or 'raiz'}.{linha.atributo}, "
        f"que o motor não expõe"
    )


@pytest.mark.parametrize("linha", TABELA, ids=lambda p: p.chave)
def test_escrita_aterrissa_no_motor(linha, perfil):
    """Escreve pelo conversor declarado e confere que o motor guardou o valor."""
    valor = VALORES_DE_TESTE[linha.para_motor.__name__]
    convertido = linha.para_motor(valor, native)
    destino = alvo_nativo(perfil, linha.grupo)
    setattr(destino, linha.atributo, convertido)
    lido = getattr(destino, linha.atributo)
    assert linha.para_preset(lido) == linha.para_preset(convertido), (
        f"'{linha.chave}' foi escrito como {convertido!r} e lido como {lido!r}"
    )


# ── 2. Os grupos declarados existem, e só eles ──────────────────────────────

def test_todo_grupo_declarado_existe_no_perfil(perfil):
    for grupo, atributo in ATRIBUTO_DO_GRUPO.items():
        if atributo is None:
            continue
        assert hasattr(perfil, atributo), (
            f"o grupo '{grupo}' mapeia para BrushProfile.{atributo}, "
            f"que não existe no módulo nativo"
        )


def test_metodos_por_metodo_existem_no_backend():
    from ui.engine_backends.aladyn import AladynBackend

    for entrada in PARAMS_POR_METODO:
        assert hasattr(AladynBackend, entrada.metodo), (
            f"'{entrada.chave}' declara o método '{entrada.metodo}', "
            f"ausente do AladynBackend"
        )


# ── 3. Nenhuma chamada da interface usa um par não declarado ────────────────

def _chamadas_literais_a_set_brush_param() -> list[tuple[pathlib.Path, int, str, str]]:
    """Varre o repositório por set_brush_param("grupo", "param", ...) literais."""
    achados: list[tuple[pathlib.Path, int, str, str]] = []
    for caminho in list(RAIZ.glob("ui/**/*.py")) + list(RAIZ.glob("plugins/**/*.py")):
        try:
            arvore = ast.parse(caminho.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for no in ast.walk(arvore):
            if not isinstance(no, ast.Call):
                continue
            alvo = no.func
            nome = alvo.attr if isinstance(alvo, ast.Attribute) else getattr(alvo, "id", None)
            if nome != "set_brush_param" or len(no.args) < 2:
                continue
            grupo, param = no.args[0], no.args[1]
            if isinstance(grupo, ast.Constant) and isinstance(param, ast.Constant):
                achados.append((caminho, no.lineno, grupo.value, param.value))
    return achados


def test_toda_chamada_da_interface_resolve():
    chamadas = _chamadas_literais_a_set_brush_param()
    assert chamadas, "nenhuma chamada literal encontrada — a varredura quebrou"

    quebradas = []
    for caminho, linha, grupo, param in chamadas:
        try:
            resolver(grupo, param)
        except KeyError as exc:
            rel = caminho.relative_to(RAIZ)
            quebradas.append(f"{rel}:{linha}  set_brush_param({grupo!r}, {param!r})\n      {exc.args[0]}")

    assert not quebradas, (
        "chamadas da interface apontam para parâmetros não declarados:\n  "
        + "\n  ".join(quebradas)
    )


# ── 4. O par leitura/escrita é coerente ─────────────────────────────────────

def test_ida_e_volta_preserva_o_estado():
    """get → apply → get deve ser estável: um preset salvo tem que voltar igual."""
    from ui.engine_backends.aladyn import AladynBackend

    backend = AladynBackend()
    if not backend.available:
        pytest.skip("backend nativo indisponível")

    partida = backend.get_brush_profile_dict()
    assert partida, "get_brush_profile_dict devolveu vazio"

    backend.apply_brush_preset_dict(partida)
    chegada = backend.get_brush_profile_dict()

    divergentes = {
        chave: (partida[chave], chegada.get(chave))
        for chave in partida
        if chave not in chegada or partida[chave] != chegada[chave]
    }
    assert not divergentes, f"a ida e volta perdeu ou alterou: {divergentes}"


def test_toda_chave_legivel_aparece_na_leitura():
    from ui.engine_backends.aladyn import AladynBackend

    backend = AladynBackend()
    if not backend.available:
        pytest.skip("backend nativo indisponível")

    lido = backend.get_brush_profile_dict()
    faltando = [p.chave for p in TABELA if p.legivel and p.chave not in lido]
    assert not faltando, (
        f"declarados como legíveis mas ausentes de get_brush_profile_dict: {faltando}"
    )


def test_parametro_nao_declarado_falha_alto():
    """A regressão que originou tudo isto: silêncio onde devia haver erro."""
    from ui.engine_backends.aladyn import AladynBackend

    backend = AladynBackend()
    with pytest.raises(KeyError):
        backend.set_brush_param("dynamics", "jitter_size", 0.5)
    with pytest.raises(KeyError):
        backend.set_brush_param("root", "scatter_radius", 3.0)


def test_blend_mode_aceita_indice_da_combo():
    """A combo do painel manda o índice; o motor exige o enum."""
    from ui.engine_backends.aladyn import AladynBackend

    backend = AladynBackend()
    if not backend.available:
        pytest.skip("backend nativo indisponível")

    quantidade = len(native.DabBlendMode.__members__)
    for indice in range(quantidade):
        backend.set_brush_param("root", "blend_mode", indice)
        assert int(backend._facade.get_brush_profile().blend_mode) == indice

    with pytest.raises(ValueError):
        backend.set_brush_param("root", "blend_mode", quantidade + 5)


# ── 5. A tabela é internamente consistente ──────────────────────────────────

def test_chaves_sem_duplicata():
    chaves = [p.chave for p in TABELA]
    duplicadas = {c for c in chaves if chaves.count(c) > 1}
    assert not duplicadas, f"chaves repetidas na tabela: {duplicadas}"


def test_indice_cobre_a_tabela_inteira():
    for linha in TABELA:
        assert POR_GRUPO_E_ATRIBUTO[(linha.grupo, linha.atributo)] is linha
