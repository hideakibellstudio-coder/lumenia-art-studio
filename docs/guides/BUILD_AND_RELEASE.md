# 📦 Guia de Compilação e Distribuição Comercial (F-016)

Este documento descreve o fluxo oficial para compilar a extensão nativa C++, gerar o executável autônomo portátil (*Standalone Portable*) e criar o instalador oficial do Windows.

---

## ⚙️ 1. Compilação do Motor Nativo C++ (`aladyn_engine_native`)

A extensão nativa é compilada com MSVC C++20 via PyBind11 utilizando o script oficial `scripts/build_native.py`:

```powershell
python scripts/build_native.py --simd scalar --force
```

- **Flags de Compilação**: `/std:c++20 /O2 /W4 /EHsc /openmp`.
- **Artefato Gerado**: `aladyn_engine_native.cp314-win_amd64.pyd` na raiz do projeto.
- **Manifesto de Build**: Salva o SHA-256 e timestamp em `build/native-build.json`.

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
  - Desinstalador limpo registrado no Painel de Controle do Windows.\n