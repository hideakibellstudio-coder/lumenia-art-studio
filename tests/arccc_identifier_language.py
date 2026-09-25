"""
arccc_identifier_language.py
============================
Conta, arquivo por arquivo, identificadores com palavras em português — nomes
de classe, função, variável, argumento e atributo no Python; nomes que
aparecem no código C++ (fora de comentários e textos). Mantém a catraca
`arccc_identifier_baseline.json`, usada por
`tests/test_arccc_identifier_language_ratchet.py`.

Por que existe
--------------
Seção 14 do ARCcC: todo código é escrito em inglês (pastas, arquivos,
classes, funções, variáveis, constantes). Português é permitido em
comentários, documentação e mensagens ao usuário (`tr(...)`), nunca no nome.
Em 2026-09-24 havia nomes em português no código de produção (`estado_vivo`,
`Homografia`, `roiAoRedor`) e nos testes (`test_traco_e_deterministico`).

A lista de palavras é curta e evita palavras que também são inglesas
(`motor`, `grade`, `base`, `sim`...), então a contagem é um piso: um nome
em português com palavra fora da lista não é contado. A catraca só desce.

Uso
---
    python -m tests.arccc_identifier_language            # relatório por arquivo
    python -m tests.arccc_identifier_language --tighten  # baixa a catraca (nunca sobe)
    python -m tests.arccc_identifier_language --rename velho.py novo.py
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = Path(__file__).resolve().parent / "arccc_identifier_baseline.json"

PY_DIRS = ("ui", "tests", "scripts", "benchmarks")
CXX_DIRS = ("engine", "bridge", "tests/native")
CXX_SUFFIXES = (".hpp", ".cpp", ".h")

# Palavras portuguesas comuns em nomes de código. Sem acento (o nome é
# normalizado antes). Fora da lista de propósito: palavras que também são
# inglesas ou abreviações comuns (motor, grade, base, real, total, normal,
# final, sim, sem, ate, do, no, na).
PT_WORDS = frozenset("""
abrir acoplamento altura amostra amostras angulo antes antiga antigo aqui arquivo arquivos atual atualizado
atualizar aviso azul balde borda borracha branco caminho camada camadas caneta carregar catraca centro chave
chaves cheio como conferir conta contagem cor cores criar dados deve depois desenhar desfazer desfoque
direita disponiveis documento dono eixo eixos entrada erro erros escala esperada esperado espelhar espelho
esquerda estado estavel exportar falha falso faltando fechar ferramenta ferramentas fim fundo garantir girar
gravacao guia guias historico homografia igual imagem imagens inicio janela largura lapis limpar linha linhas
lista maior mais mao mascara medida medidas medido medidores medir menor menos mesmo montar mostrar nativa
nativo nenhum nenhuma nome nova novo nunca obtido oleo outra outro padrao painel papel para paraByte pasta
perfil pincel pintar pivo pode ponto pontos preto primeira primeiro quadro quadros raio recuperacao refazer
regua relatorio saida salvar selecao sempre simetria sujo tabela tamanho tela teste testes textura tinta
todas todos traco tracos trava travar tudo ultima ultimo usadas valor valores varinha varrer vazia vazio
velho vermelho verde vivo
alca alvo alvos analisar aplicar arrastar atalho botao caixa caixas canto cantos convexo copia copiar cruz
demonstracao desligar deslocamento deslocamentos distancia distancias distorcao formigas girado horario lado
lados matriz maximo minimo operacao operacoes passada plano posicao posicoes quadrado raios redor residuos
retangulo rotulo rotulos selecionada selecionado sinal sincronizar unitario usar
alcance celula cobertura fonte inverso margem meio soma
""".split())

_SPLIT = re.compile(r"_+|(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_CXX_COMMENT = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)
_CXX_STRING = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')
_CXX_IDENT = re.compile(r"\b[A-Za-z_]\w*\b")


def _plain(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn").lower()


def portuguese_words(identifier: str) -> list[str]:
    return [w for w in (_plain(t) for t in _SPLIT.split(identifier) if t) if w in PT_WORDS]


def _python_names(source: str) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
            names.add(node.attr)
    return names


def _cxx_names(source: str) -> set[str]:
    code = _CXX_STRING.sub('""', _CXX_COMMENT.sub(" ", source))
    code = "\n".join(line for line in code.splitlines() if not line.lstrip().startswith("#include"))
    return set(_CXX_IDENT.findall(code))


def iter_source_files() -> list[Path]:
    files: list[Path] = []
    for base in PY_DIRS:
        files += [p for p in (ROOT / base).rglob("*.py") if "__pycache__" not in p.parts]
    for base in CXX_DIRS:
        files += [p for p in (ROOT / base).rglob("*") if p.suffix in CXX_SUFFIXES]
    return sorted(set(files))


def scan_file(path: Path) -> list[str]:
    """Identificadores com palavra portuguesa neste arquivo (sem repetição)."""
    source = path.read_text(encoding="utf-8", errors="ignore")
    names = _python_names(source) if path.suffix == ".py" else _cxx_names(source)
    return sorted(n for n in names if portuguese_words(n))


def scan_all() -> dict[str, list[str]]:
    found = {}
    for path in iter_source_files():
        names = scan_file(path)
        if names:
            found[path.relative_to(ROOT).as_posix()] = names
    return found


def load_baseline() -> dict[str, int]:
    if not BASELINE_PATH.exists():
        return {}
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def save_baseline(baseline: dict[str, int]) -> None:
    BASELINE_PATH.write_text(json.dumps(dict(sorted(baseline.items())), indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")


def tighten() -> int:
    """Baixa a catraca até o valor atual; nunca sobe um número."""
    baseline = load_baseline()
    current = {path: len(names) for path, names in scan_all().items()}
    new = {path: min(count, baseline[path]) if path in baseline else count for path, count in current.items()}
    save_baseline(new)
    return sum(new.values())


def rename(old: str, new: str) -> None:
    baseline = load_baseline()
    if old in baseline:
        baseline[new] = baseline.pop(old)
        save_baseline(baseline)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--tighten", action="store_true", help="baixa a catraca até o valor atual")
    parser.add_argument("--rename", nargs=2, metavar=("VELHO", "NOVO"))
    args = parser.parse_args()
    if args.rename:
        rename(*args.rename)
        return 0
    if args.tighten:
        print(f"catraca: {tighten()} identificadores em português")
        return 0
    found = scan_all()
    for path, names in sorted(found.items(), key=lambda kv: -len(kv[1])):
        print(f"{len(names):4d}  {path}: {', '.join(names[:8])}{' ...' if len(names) > 8 else ''}")
    print(f"\ntotal: {sum(len(n) for n in found.values())} em {len(found)} arquivos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
