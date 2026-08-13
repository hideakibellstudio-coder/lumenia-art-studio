# BUILD — ALADYN ENGINE + LUMENIA UI

Documento oficial de compilação e deploy do motor nativo C++ e da interface Lumenia.

---

## Visão Geral da Arquitetura

```
ALADYN + UI LUMENIA/
├── ALADYN ENGINE/          ← Motor C++17 + bindings PyBind11
│   ├── engine/             ← Código-fonte C++ puro (sem dependências Python)
│   ├── bridge/             ← Bindings PyBind11 (engine_bindings.cpp)
│   ├── setup.py            ← Script de compilação do .pyd
│   └── aladyn_engine_native.cp314-win_amd64.pyd   ← Saída do build (gerada)
│
└── Lumenia/                ← Interface Python/PySide6
    ├── aladyn_engine_native.cp314-win_amd64.pyd   ← ✅ ÚNICO local canônico de deploy
    ├── ui/
    │   ├── main.py         ← Ponto de entrada da aplicação
    │   └── engine_backends/
    │       └── aladyn.py   ← Adaptador Python → C++
    └── plugins/
```

> ⚠️ IMPORTANTE: O `.pyd` compilado deve existir em **apenas um lugar**: `Lumenia/`.
> Nunca copie o `.pyd` para subpastas como `Lumenia/ui/`. Ver seção **Anti-patterns**.

---

## Pré-requisitos

| Ferramenta     | Versão mínima | Notas                                                    |
|----------------|---------------|----------------------------------------------------------|
| Python         | 3.14.x 64-bit | Deve ser o mesmo Python que executa a Lumenia            |
| Visual Studio  | 2022 Community| Workload "Desenvolvimento para Desktop com C++"          |
| pybind11       | qualquer      | `pip install pybind11`                                   |
| setuptools     | qualquer      | `pip install setuptools`                                 |

Verificar pré-requisitos:

```powershell
python --version          # Python 3.14.x esperado
pip show pybind11         # deve retornar Version: x.x.x
cl /?                     # deve existir (MSVC) — rode dentro do Developer PowerShell
```

---

## Compilando o Motor C++

### 1. Abrir o terminal correto

Use o **"Developer PowerShell for VS 2022"** (ou "x64 Native Tools Command Prompt for VS 2022").
Isso garante que `cl.exe` e `link.exe` estejam no PATH.

### 2. Navegar até a pasta do engine

```powershell
cd "z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\ALADYN ENGINE"
```

### 3. Compilar

```powershell
python setup.py build_ext --inplace
```

O que esse comando faz:
- Compila todos os `.cpp` listados em `setup.py` com `/O2 /std:c++17`
- Linka contra `python314.lib` (via PyBind11)
- Gera `aladyn_engine_native.cp314-win_amd64.pyd` dentro de `ALADYN ENGINE/`

Saída esperada ao final:
```
Finished generating code
copying build\lib.win-amd64-cpython-314\aladyn_engine_native.cp314-win_amd64.pyd ->
```

> 💡 DICA: O build incremental só recompila os `.cpp` alterados.
> Recompilação completa: ~60s. Incremental: ~10-15s.

---

## Deploy do Binário para a Lumenia

Após compilar, copie o `.pyd` para `Lumenia/`:

```powershell
# Estando na pasta ALADYN ENGINE:
Copy-Item -Path "aladyn_engine_native.cp314-win_amd64.pyd" `
          -Destination "..\Lumenia\aladyn_engine_native.cp314-win_amd64.pyd" `
          -Force
```

### Build + Deploy em um único comando

```powershell
python setup.py build_ext --inplace; `
Copy-Item "aladyn_engine_native.cp314-win_amd64.pyd" "..\Lumenia\" -Force; `
Write-Host "✅ Build e deploy concluídos."
```

---

## Executando a Lumenia UI

```powershell
cd "z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\Lumenia\ui"
python main.py
```

Com logs de debug:

```powershell
python main.py --debug
```

### Como o `main.py` resolve o `.pyd`

O `main.py` adiciona `Lumenia/` ao `sys.path`:

```python
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)  # → aponta para Lumenia/
```

Quando `aladyn.py` executa `import aladyn_engine_native`, o Python encontra
o `.pyd` em `Lumenia/` e carrega. Sem gambiarras, sem `importlib`.

---

## Estrutura de Sources C++

```
engine/
├── boundary/public-api/
│   └── PaintEngineFacade.cpp   ← API pública — ponto de entrada para Python
├── core/
│   ├── canvas/
│   │   ├── TileGrid.cpp        ← Grade de tiles RGBA; copyFrom() para duplicação
│   │   └── SpatialCuller.cpp   ← Culling de tiles fora da viewport
│   ├── document/
│   │   ├── LayerStack.cpp      ← Pilha de camadas; addLayer/addGroup/duplicate
│   │   └── Compositor.cpp      ← Composição de camadas → buffer de saída RGBA
│   ├── engines/
│   │   └── *Engine.cpp         ← PencilEngine, InkerEngine, BrushEngine, etc.
│   ├── raster/
│   │   ├── DabRenderer.cpp     ← Renderiza dabs nos tiles
│   │   └── DabInterpolator.cpp ← Interpola dabs entre pontos do traço
│   └── stroke/
│       ├── VelocityTracker.cpp
│       └── DynamicStabilizer.cpp
└── bridge/core/bindings/
    └── engine_bindings.cpp     ← PyBind11: expõe PaintEngineFacade ao Python
```

Quando um novo arquivo `.cpp` é criado, ele **deve ser listado** em `setup.py`
dentro de `cpp_sources` para ser incluído na compilação.

---

## Adicionando um Novo Arquivo C++ ao Build

1. Criar o arquivo `.cpp` em `engine/` ou `bridge/`
2. Abrir `ALADYN ENGINE/setup.py`
3. Adicionar o caminho relativo em `cpp_sources`:

```python
cpp_sources = [
    ...
    "engine/core/meu_modulo/MeuArquivo.cpp",   # ← adicionar aqui
    ...
]
```

4. Recompilar e fazer deploy (ver seção acima).

---

## Expondo uma Nova Função ao Python

Toda nova função da `PaintEngineFacade` precisa ser registrada em `engine_bindings.cpp`:

```cpp
// engine_bindings.cpp — dentro do bloco py::class_<boundary::PaintEngineFacade>(...)
.def("nome_python", &boundary::PaintEngineFacade::NomeCpp)
```

Recompile e faça o deploy após qualquer mudança em `engine_bindings.cpp`.

---

## Verificando o Build

```powershell
python -c "
import sys
sys.path.insert(0, r'z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\Lumenia')
import aladyn_engine_native as m
f = m.PaintEngineFacade(100, 100)
print('OK — metodos:', [x for x in dir(f) if not x.startswith('_')])
"
```

---

## Anti-patterns — O que NÃO fazer

### ❌ Não copie o `.pyd` para `Lumenia/ui/` ou qualquer subpasta

O `sys.path` da Lumenia aponta para `Lumenia/` como raiz. Cópias em subpastas
geram colisão de versões e bugs silenciosos onde o Python carrega o binário errado,
enquanto testes unitários carregam o correto — resultando em comportamentos
impossíveis de reproduzir e difíceis de diagnosticar.

### ❌ Não edite o `.pyd` compilado diretamente

Ele é um binário gerado. Qualquer mudança no C++ exige recompilação via `setup.py`.

### ❌ Não misture versões de Python

O `.pyd` é compilado para `cp314` (CPython 3.14). Rodar a Lumenia com Python 3.12
ou 3.13 causará:

```
ModuleNotFoundError
# ou
ImportError: dynamic module does not define init function (PyInit_aladyn_engine_native)
```

### ❌ Não adicione `Lumenia/ui/` ao `sys.path` manualmente

O `main.py` adiciona apenas `Lumenia/` (pasta pai de `ui/`). Isso é suficiente
para resolver `import ui.*` e `import aladyn_engine_native`. Adicionar `ui/`
ao path interfere na resolução dos módulos.

---

## Checklist de Build Completo

- [ ] Abrir **Developer PowerShell for VS 2022**
- [ ] `cd` para `ALADYN ENGINE/`
- [ ] `python setup.py build_ext --inplace` — aguardar sem erros
- [ ] `Copy-Item "aladyn_engine_native.cp314-win_amd64.pyd" "..\Lumenia\" -Force`
- [ ] Confirmar que **não existe** `.pyd` em `Lumenia/ui/`
- [ ] Executar `python main.py` de `Lumenia/ui/`
- [ ] Confirmar no log: `[AladynBackend] Módulo nativo aladyn_engine_native carregado com sucesso`
