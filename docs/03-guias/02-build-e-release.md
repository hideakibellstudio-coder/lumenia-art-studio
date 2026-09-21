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

## 💿 3. Compilação do Instalador Oficial (Inno Setup)

O script `scripts/lumenia_installer.iss` compila o executável gerado em um instalador profissional para Windows:

```powershell
& "C:\Users\HIDE\AppData\Local\Programs\Inno Setup 6\ISCC.exe" scripts\lumenia_installer.iss
```

- **Compressão**: LZMA2/Ultra64 com compressão sólida multi-thread.
- **Artefato Gerado**: `build/installer/Lumenia_Setup_v0.2.0.exe` (~55.6 MB).
- **Recursos Inclusos**:
  - Instalação no diretório `Program Files\Lumenia Art Studio`.
  - Atalhos no Desktop e Menu Iniciar.
  - Associação de arquivos de extensão `.lmn` e `.lumenia`.
  - Desinstalador limpo registrado no Painel de Controle do Windows.

---

## ⚠️ 4. Limitações Conhecidas

Ainda não existe instalador assinado, assinatura de artefatos nem seleção automática entre variantes SIMD (`scalar`/`avx2`). Essas etapas pertencem a um futuro job de release, não a uma cópia manual do `.pyd`.
