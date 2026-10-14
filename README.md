# 🎨 Lumenia Art Studio

<div align="center">
  <img src="assets/images/icon_lumenia.png" alt="Lumenia Logo" width="128" height="128">
  <br>
  <strong>Estúdio desktop de arte e pintura digital</strong>
  <br>
  <em>PySide6 + ALADYN Native Engine em C++20</em>
  <br><br>
  <img src="https://img.shields.io/badge/Versão-v0.2.0%20Alpha-9333ea?style=for-the-badge" alt="Versão Alpha">
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge" alt="Python 3.11 ou superior">
  <img src="https://img.shields.io/badge/C%2B%2B-C%2B%2B20%20SIMD-blue?style=for-the-badge" alt="C++20 SIMD">
  <img src="https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt6-success?style=for-the-badge" alt="PySide6 Qt6">
</div>

---

## 📖 Sobre o projeto

O **Lumenia Art Studio** é um aplicativo desktop para ilustração, concept art, lineart e pintura digital. A interface é construída com **Python/PySide6** e os trechos de processamento intensivo são executados pelo **ALADYN Engine**, um motor nativo em **C++20** conectado ao Python por meio de **pybind11**.

A arquitetura do projeto segue o modelo ARCcC, com separação entre interface, estado da aplicação, ponte Python/C++, motor nativo e infraestrutura. Consulte [`AGENTS.md`](AGENTS.md) antes de alterar a estrutura do projeto.

> **Estado atual de compatibilidade:** o fluxo oficial de desenvolvimento e empacotamento é **Windows x64**. O código contém partes portáveis, mas o binário nativo `.pyd`, os vínculos do Windows e o pacote portátil precisam ser compilados para o sistema operacional, arquitetura e versão de Python de destino. Não é possível usar o mesmo `.pyd` em todas as máquinas.

## ✨ Principais recursos

- Motor de pincéis nativo com estabilização, interpolação Catmull-Rom, pressão, inclinação e rotação de caneta.
- Pincéis de tinta, lápis, marcador, aquarela, óleo, borracha, blur e smudge.
- Camadas, grupos, clipping mask, alpha lock, opacidade e modos de mesclagem.
- Seleções retangulares, elípticas, laço livre, laço poligonal e marching ants.
- Varinha mágica e balde de tinta com tolerância configurável.
- Transformação livre com alças, pivô central e interpolação nativa.
- Simetrias, réguas, snapping e perspectivas de um, dois e três pontos.
- Gerenciamento de cores, perfis ICC/LittleCMS, soft-proofing e temas visuais.
- Formato nativo `.lmn` com documentos em camadas.
- Distribuição portátil gerada com Nuitka.

## 🧱 Estrutura do repositório

```text
lumenia-art-studio/
├── engine/                  # Motor ALADYN em C++20
│   ├── boundary/            # API pública e orquestradores
│   ├── core/                # Matemática, raster, documento, camadas e pincéis
│   ├── infrastructure/      # Disco, compressão, licenciamento e crash handling
│   └── utils/               # Tipos e utilitários de baixo nível
├── bridge/                  # Bindings pybind11 e contratos .pyi
├── ui/                      # Interface, estado, infraestrutura e plugins PySide6
├── assets/                  # Ícones, temas e avisos de terceiros
├── docs/                    # Documentação técnica e guias de build/release
├── scripts/                 # Automação de build, testes e validações
├── tests/                   # Testes automatizados
├── main.py                  # Entrada do aplicativo
├── setup.py                 # Definição da extensão C++/pybind11
├── pyproject.toml           # Metadados e dependências Python
├── requirements-dev.lock    # Dependências travadas para Windows x64
└── AGENTS.md                # Constituição arquitetural e regras operacionais
```

## 🖥️ Plataformas e matriz de build

| Plataforma | Execução Python | Extensão nativa | Pacote portátil | Status |
|---|---:|---:|---:|---|
| Windows x64 | Sim | Sim (`.pyd`) | Sim (`.exe`) | **Fluxo oficial** |
| Linux x64 | Parcial, com adaptações | Não coberto pelo build oficial | Não | Experimental |
| macOS | Não validado | Não validado | Não | Experimental |
| Windows ARM64 | Não validado | Não validado | Não | Experimental |

Para uma máquina diferente, compile o motor e o pacote **na própria máquina de destino**. A compatibilidade depende de:

1. sistema operacional e arquitetura;
2. versão/ABI do Python;
3. compilador C++ e runtime instalados;
4. instruções SIMD disponíveis na CPU;
5. dependências Python e Qt instaladas.

O build padrão `scalar` é o mais compatível. O build `avx2` só deve ser usado quando todas as máquinas de destino suportarem AVX2.

---

# 🚀 Compilação completa no Windows x64

Esta é a sequência recomendada para uma máquina nova. Os comandos abaixo devem ser executados a partir da raiz do repositório.

## 1. Instalar ferramentas do sistema

Instale:

- [Git](https://git-scm.com/);
- [Python 3.11 ou superior](https://www.python.org/downloads/windows/) — use Python x64 e habilite a opção **Add Python to PATH**;
- [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/), selecionando:
  - **Desktop development with C++**;
  - MSVC x64/x86 build tools;
  - Windows 10 ou Windows 11 SDK;
  - C++ CMake tools, se oferecido pelo instalador.

O script `scripts/build_native.py` procura automaticamente o Visual Studio por meio do `vswhere`. Também é possível executar os comandos a partir de um **x64 Native Tools Command Prompt for Visual Studio**.

Confira as instalações:

```powershell
py --version
git --version
where.exe py
```

## 2. Clonar o repositório

```powershell
git clone https://github.com/hideakibellstudio-coder/lumenia-art-studio.git
cd lumenia-art-studio
```

## 3. Criar um ambiente virtual isolado

Não instale as dependências do projeto globalmente. O ambiente virtual evita conflitos com outras aplicações Python:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
python -m pip install --upgrade pip
```

Se o PowerShell bloquear a ativação, execute uma vez, como usuário atual:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Como alternativa, use o Prompt de Comando:

```bat
.venv\Scripts\activate.bat
```

## 4. Instalar dependências

Para reproduzir exatamente o ambiente de desenvolvimento Windows x64:

```powershell
python -m pip install --requirement requirements-dev.lock
```

O arquivo de lock usa hashes e versões específicas. Se estiver usando uma versão de Python ou uma plataforma sem wheel compatível, o `pip` poderá rejeitar a instalação. Nesse caso, use Python x64 compatível ou instale as dependências declaradas no `pyproject.toml` sem o lock apenas para desenvolvimento experimental:

```powershell
python -m pip install --editable .
python -m pip install pytest pytest-qt ruff nuitka
```

> O lock oficial é voltado para Windows x64 e para as versões de Python exercitadas pelo projeto. Não remova `--require-hashes` para gerar uma release reproduzível.

## 5. Compilar a extensão nativa C++

O motor precisa ser compilado antes de iniciar o aplicativo:

```powershell
python scripts/build_native.py --simd scalar
```

Esse comando:

- configura o compilador MSVC automaticamente;
- compila a extensão `aladyn_engine_native` em C++20;
- coloca objetos e intermediários em `../build/temp_native`;
- copia apenas o módulo `.pyd` final para a raiz, porque o Python precisa encontrá-lo;
- grava metadados em `../build/native-build.json`.

Para forçar uma recompilação completa:

```powershell
python scripts/build_native.py --simd scalar --force
```

Para uma build específica de máquinas que comprovadamente suportam AVX2:

```powershell
python scripts/build_native.py --simd avx2 --force
```

> **Importante:** não distribua um build AVX2 para uma CPU sem AVX2. Para maior compatibilidade, use sempre `scalar` como artefato público padrão.

Para gerar símbolos PDB fora do repositório durante diagnóstico de crashes:

```powershell
python scripts/build_native.py --simd scalar --pdb
```

## 6. Validar a instalação

Verifique se o módulo nativo foi carregado:

```powershell
python -c "import aladyn_engine_native; print(aladyn_engine_native.__file__)"
```

Execute os testes:

```powershell
python -m pytest
```

Para conferir apenas a coleta de testes:

```powershell
python -m pytest --collect-only -q
```

Execute o linter:

```powershell
ruff check .
```

## 7. Executar o aplicativo

```powershell
python main.py
```

Também é possível usar o lançador do Windows:

```powershell
.\Launch_Lumenia.bat
```

Se o aplicativo iniciar sem o canvas funcional, confirme primeiro se existe exatamente um arquivo `aladyn_engine_native*.pyd` na raiz e se ele foi compilado com a mesma versão/arquitetura do Python em uso.

---

# 📦 Gerar uma versão portátil `.exe`

A distribuição portátil usa Nuitka e deve ser gerada depois de compilar o motor nativo.

```powershell
python scripts/build_portable.py
```

A saída fica fora do repositório:

```text
../build/portable/Lumenia.dist/
├── Lumenia.exe
├── aladyn_engine_native.pyd
├── assets/
├── licenses/
└── release-manifest.json
```

O script também inclui os recursos necessários, copia licenças de terceiros e cria um manifesto SHA-256. Para escolher outro diretório externo:

```powershell
python scripts/build_portable.py --output ..\build\portable-release
```

Teste o executável em uma máquina Windows limpa, sem o ambiente virtual do desenvolvedor. Isso confirma que todas as DLLs, plugins Qt, assets, fontes e licenças foram incluídos no bundle.

> A distribuição portátil é específica para Windows x64 e para o conjunto de instruções com que o motor foi compilado. Para outra plataforma, é necessário um pipeline de build próprio para essa plataforma.

## 🏗️ Gerar um instalador

O repositório mantém o pipeline portátil separado do instalador. Depois de gerar e validar `Lumenia.dist`, siga o guia de release em [`docs/03-guias/02-build-e-release.md`](docs/03-guias/02-build-e-release.md) para gerar o instalador com Inno Setup/Velopack e revisar os avisos legais.

---

# 🧹 Política de build out-of-tree

Para manter o repositório leve e reproduzível:

- não crie `build/`, `dist/`, `tmp/`, `temp/`, `scratch/`, `logs/` ou `test_outputs/` dentro do repositório;
- os intermediários devem ficar em `../build`;
- os entregáveis finais devem ficar em `../dist` ou em outro diretório externo;
- não versione `.obj`, `.pdb`, `.ilk`, `.lib`, `.coverage`, relatórios de crash ou dumps;
- imagens e relatórios temporários devem ser gravados no diretório temporário do sistema;
- antes de finalizar uma alteração, confira:

```powershell
git status --short
```

A única exceção esperada é o módulo nativo `aladyn_engine_native*.pyd` na raiz, quando necessário para executar ou empacotar a aplicação localmente. Ele não deve ser usado como substituto de um build reproduzível.

---

# 🧪 Desenvolvimento e validação

Ative os hooks versionados uma vez por clone:

```powershell
git config core.hooksPath .githooks
```

Comandos úteis:

```powershell
# Suíte completa
python -m pytest

# Linter
ruff check .

# Conferência do layout e documentação ARCcC
python -m tests.arccc_package_docs

# Métricas de acoplamento
python -m tests.arccc_coupling_metrics --top 20

# Regras de build Windows a partir de Linux/CI, quando aplicável
python scripts/check_windows_build.py
```

Consulte `AGENTS.md` para as regras de arquitetura, limites de LOC, contratos entre componentes, dependências permitidas e protocolo de higiene.

---

# 🛠️ Solução de problemas

### `Microsoft Visual C++ is required`

Instale o Visual Studio Build Tools com o workload **Desktop development with C++** e o Windows SDK. Depois reabra o terminal ou use o **x64 Native Tools Command Prompt**.

### `vswhere.exe not found`

O Visual Studio Installer não está instalado no caminho esperado. Abra o instalador do Visual Studio, adicione o workload C++, ou configure manualmente o ambiente executando o build em um prompt nativo do Visual Studio.

### `No module named aladyn_engine_native`

Compile o motor na raiz do projeto:

```powershell
python scripts/build_native.py --simd scalar --force
```

Depois confirme que o `.pyd` gerado corresponde ao Python ativo:

```powershell
python -c "import sys; print(sys.version); print(sys.executable)"
```

### `DLL load failed` ao importar o `.pyd`

Verifique todos estes pontos:

- Python x64 e compilador x64, não uma mistura x86/x64;
- mesma versão/ABI de Python usada para compilar e executar;
- runtime do Visual C++ instalado;
- build `scalar` quando a CPU não oferece AVX2;
- apenas um `aladyn_engine_native*.pyd` na raiz.

### Falha no `pip install --requirement requirements-dev.lock`

O lock contém hashes para wheels suportadas. Use Python x64 compatível com o lock e atualize o pip. Em outra plataforma, o lock oficial pode não conter wheels; nesse caso, siga a instalação experimental descrita na seção de dependências.

### O portátil funciona no computador de build, mas não em outro

Não copie apenas o `.exe`. Distribua a pasta `Lumenia.dist` completa. Gere novamente o bundle com `scripts/build_portable.py`, valide o manifesto e teste em uma máquina limpa.

---

# 📚 Documentação relacionada

- [`AGENTS.md`](AGENTS.md) — constituição arquitetural e regras obrigatórias para agentes e desenvolvedores.
- [`docs/README.md`](docs/README.md) — índice da documentação técnica.
- [`docs/03-guias/02-build-e-release.md`](docs/03-guias/02-build-e-release.md) — build portátil, release e instalador.
- [`pyproject.toml`](pyproject.toml) — metadados e dependências Python.
- [`setup.py`](setup.py) — fontes C++ e configuração da extensão pybind11.
- [`scripts/build_native.py`](scripts/build_native.py) — compilação do motor nativo.
- [`scripts/build_portable.py`](scripts/build_portable.py) — geração e validação da distribuição portátil.

# 🗺️ Roadmap

- [ ] Formas vetoriais e primitivas rápidas.
- [ ] Texto editável diretamente no canvas.
- [ ] Mais harmonias e modos de cor.
- [x] Réguas, simetrias e guias de perspectiva.
- [x] Formato nativo `.lmn` com camadas.
- [x] Consolidação da base C++ e integração ponta a ponta.

# 📄 Licença e contato

- **Projeto:** Lumenia Art Studio / ALADYN Engine
- **Equipe:** Lumenia Team / Aladyn Team
- **Contato:** `lumeniateam@protonmail.com`
- **Licença:** consulte [`TERMS_AND_LICENSE.txt`](TERMS_AND_LICENSE.txt) e os avisos em `assets/legal/`.
