# 📦 Guia de Compilação e Distribuição Comercial (F-016)

Este documento descreve o fluxo oficial para compilar a extensão nativa C++, gerar o executável autônomo portátil (*Standalone Portable*) e criar o instalador oficial do Windows.

---

## ⚙️ 1. Compilação do Motor Nativo C++ (`aladyn_engine_native`)

A extensão nativa é compilada com MSVC C++20 via PyBind11 utilizando o script oficial `scripts/build_native.py`:

```powershell
python scripts/build_native.py --simd scalar --force
```

- **Flags de Compilação**: `/EHsc /bigobj /std:c++20 /openmp /O2` (declaradas em `setup.py`).
- **Artefato Gerado**: `aladyn_engine_native.cp314-win_amd64.pyd` na raiz do projeto.
- **Manifesto de Build**: Salva o SHA-256 e timestamp em `build/native-build.json`.

---

## ⚙️ 1.1 Pré-requisitos

- Python 3.11+ de 64 bits — a versão usada para compilar precisa ser a mesma que carregará o `.pyd` gerado (a extensão distribuída no repositório foi compilada com Python 3.14, refletido no nome do artefato `aladyn_engine_native.cp314-win_amd64.pyd`).
- Visual Studio 2022 com **Desktop development with C++** e Windows SDK.
- Dependências de desenvolvimento com hashes declaradas em `requirements-dev.lock`:

```powershell
python -m pip install -r requirements-dev.lock
```

### Variantes SIMD

`scalar` é o artefato base compatível com processadores Windows x64 sem AVX2:

```powershell
python scripts/build_native.py --simd scalar --force
```

Em uma frota controlada que exija AVX2, gere e distribua um artefato separado:

```powershell
python scripts/build_native.py --simd avx2 --force
```

Uma variante AVX2 não deve substituir o artefato base sem uma política de detecção e seleção no instalador — essa seleção automática ainda não existe (ver nota de limitações ao final deste guia).

Ao terminar, o script grava `build/native-build.json` com `python_version`, `python_abi`, `msvc_tools_version`, a variante `simd` usada e o SHA-256 (`extension_sha256`) do `.pyd`. Esse registro permite comparar o binário executado localmente ou em CI com a configuração que o produziu.

### Validação

```powershell
python tests/run_all_tests.py
python benchmarks/run_engine_benchmarks.py --output build/benchmarks/engine.json
python main.py
```

O benchmark grava JSON com ambiente, p50/p95 de criação da fachada, traço e `refresh_display`, além dos bytes de pixels. É uma base de comparação entre máquinas e commits, não um gate com valores fixos, porque hardware e carga do sistema alteram a medida.

---

## 🚀 2. Compilação Portátil Autônoma (Nuitka)

Para empacotar a aplicação completa (Python + PySide6 + C++ Engine + Dependências) em uma distribuição autônoma que roda em qualquer Windows sem necessidade de Python instalado:

```powershell
python scripts/build_portable.py --output build/portable
```

- **Compilador Utilizado**: MSVC 14.44 com cache acelerado `clcache`.
- **Plugins Nuitka**: `--enable-plugin=pyside6`.
- **Artefato Gerado**: `build/portable/Lumenia.dist/Lumenia.exe`.
- **Manifesto Criptográfico**: Gera automaticamente `build/portable/Lumenia.dist/release-manifest.json` com os hashes SHA-256 de todos os arquivos distribuídos.

---

## 💿 3. Instalador, Atualizações e Release (Velopack)

Desde 2026-10-08 o instalador é o do **Velopack** (o script do Inno Setup saiu). O programa
instala por usuário em `%LocalAppData%\Lumenia` (sem UAC), a versão em uso fica em `current\`
e cada atualização baixa só o que mudou (pacote delta) e troca a pasta quando o programa fecha,
mantendo a versão anterior se algo falhar. Os dados do usuário ficam em `%AppData%\Lumenia`
(`ui/infrastructure/runtime_paths.py`), fora da pasta trocada.

Pré-requisitos só na máquina de build: .NET SDK e `vpk` (`dotnet tool install -g vpk`).

```powershell
# 1. No gerador de licenças (repositório privado, fora deste): o motor passa a confiar na chave de produção
python -m lumenia_licgen export --key prod --lumenia "<este repositório>"

# 2. Release
python scripts/build_release.py --channel stable --notes notas.md            # gera em ../dist/releases/stable
python scripts/build_release.py --channel stable --notes notas.md --upload   # e publica (GITHUB_TOKEN)
python scripts/build_release.py --channel alpha --dry-run                    # só mostra o plano
```

- **Chave de licença**: o script recusa empacotar um motor que ainda confia na chave `dev`.
- **Símbolos**: o motor é compilado com `--pdb`; o PDB fica em `../build/pdb/aladyn_engine_native-<hash>.pdb`
  (o hash é o do `.pyd`, registrado em `native-build.json`). Guarde-o: sem ele um minidump de queda não é legível.
- **Feed**: as releases ficam no repositório **público** `lumenia-releases` (só instaladores e pacotes;
  o código continua privado). O programa lê dele (`APP_UPDATE_REPOSITORY` em `ui/infrastructure/app_info.py`).
- **Canais**: `stable`, `beta`, `alpha`. Cada canal tem o próprio feed; o usuário escolhe na configuração (`updates.channel`).
- **Data de lançamento**: o script grava `<!-- released: AAAA-MM-DD -->` nas notas; o programa não instala uma
  versão lançada depois do período de atualizações da licença do usuário.
- **Cópia portátil**: o `Portable.zip` gerado pelo `vpk` roda sem instalar; com um arquivo `portable.flag` ao lado
  do executável os dados ficam ao lado dele.

## ⚠️ 4. Limitações Conhecidas

Ainda não existe assinatura de código (o SmartScreen avisa no primeiro download) nem seleção automática
entre variantes SIMD (`scalar`/`avx2`). Com um certificado, `vpk pack --signParams` assina o executável e o instalador.
