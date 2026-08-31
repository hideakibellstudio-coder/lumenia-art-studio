# 📦 MANIFESTO: ENGENHARIA DE EMPACOTAMENTO PORTÁTIL UNIVERSAL
> **Padrão Arquitetural para Distribuição Autocontida (Zero-Install) de Aplicações Python, Qt/PySide e Extensões Nativas (C++/Rust)**

---

## 🧭 1. Introdução e Filosofia

Distribuir software desktop moderno construído em **Python com GUIs ricas (PySide6/PyQt6) e módulos nativos de alto desempenho (C++/PyBind11/Rust)** exige uma estratégia que garanta:

1. **Zero Instalação (True Portability):** O usuário apenas descompacta e roda. Sem necessidade de privilégios de Administrador, sem instaladores invasivos e sem depender de Python ou compiladores pré-instalados na máquina alvo.
2. **Boot Instantâneo:** Inicialização entre **0.3s e 1.2s**, eliminando o atraso de auto-extração do modo `--onefile`.
3. **Imunidade a Conflitos de DLL:** Todas as bibliotecas C/C++, runtimes do sistema e dependências gráficas ficam encapsuladas em um diretório isolado.
4. **Resiliência contra Falsos-Positivos de Antivírus:** Evita descompactações suspeitas no diretório `%TEMP%`.

---

## 🏛️ 2. Topologia Arquitetural: O Padrão `Onedir + _internal`

A partir do **PyInstaller 6.0+**, o padrão de diretório único (`--onedir`) isola toda a complexidade técnica dentro da subpasta `_internal/`, mantendo a raiz do usuário limpa e profissional.

```
📁 MeuSoftware_v1.0.0_Portable/
│
├── 🚀 MeuSoftware.exe              ← Bootloader C compilado (inicia o Python em C)
├── 📄 LEIA-ME.txt                  ← Instruções rápidas de uso e suporte
├── 🌐 Suporte_ou_Feedback.html     ← Página de apoio/contato offline
│
└── 📁 _internal/                   ← NÚCLEO AUTOCONTIDO (Isolamento total)
    ├── 🐍 python314.dll / python3.dll ← Interpretador CPython isolado
    ├── 📦 base_library.zip         ← Módulos padrão do Python (.pyc)
    │
    ├── ⚡ meu_modulo_nativo.*.pyd   ← Binários C++ / PyBind11 / Rust
    ├── ⚙️ VCRUNTIME140.dll / MSVCP* ← Runtimes MSVC do Visual Studio
    │
    ├── 🎨 PySide6/ / PyQt6/        ← Framework gráfico e DLLs do Qt (Qt6Core, Qt6Gui, etc.)
    │   └── plugins/platforms/qwindows.dll ← Driver de janela do Windows
    │
    ├── 🧩 numpy/, psutil/, ...     ← Bibliotecas externas compiladas
    ├── 📁 app/ ou 📁 src/          ← Código-fonte da aplicação compilado em bytecode
    └── 📁 assets/                  ← Recursos visuais (ícones, temas, fontes, sons)
```

---

## 📐 3. Os 4 Pilares da Engenharia de Portabilidade

### 🔹 Pilar 1: Resolução Canônica de Caminhos (`Path Resolver`)
**Problema:** Em desenvolvimento, os arquivos estão relativos a `__file__`. Quando empacotado pelo PyInstaller, os arquivos ficam dentro de `sys._MEIPASS` (que aponta para a pasta `_internal/`).

**Solução Obrigatória:** Crie um módulo universal de resolução de caminhos (`path_resolver.py` ou adicione no seu `utils.py`):

```python
"""
path_resolver.py — Resolução universal de recursos para Dev e Produção.
"""
from __future__ import annotations
import os
import sys

def get_bundle_dir() -> str:
    """
    Retorna o diretório base dos recursos:
    - Se congelado (PyInstaller): retorna o caminho de '_internal' (sys._MEIPASS).
    - Se em desenvolvimento: retorna a raiz do projeto.
    """
    if getattr(sys, 'frozen', False):
        # Modo empacotado (PyInstaller)
        return getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    
    # Modo de desenvolvimento (executando via 'python main.py')
    # Ajuste o número de os.path.dirname conforme a profundidade deste arquivo
    return os.path.dirname(os.path.abspath(__file__))

def get_asset_path(*rel_path_parts: str) -> str:
    """Retorna o caminho absoluto determinístico para qualquer recurso em assets/."""
    return os.path.join(get_bundle_dir(), "assets", *rel_path_parts)

def get_app_data_dir(app_name: str = "MeuSoftware") -> str:
    """
    Retorna o diretório para salvar configurações e preferências:
    - Modo Portátil Puro: salva numa pasta local 'data/' ao lado do executável.
    - Se não tiver permissão de escrita: faz fallback seguro para APPDATA.
    """
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        local_data = os.path.join(exe_dir, "data")
        try:
            os.makedirs(local_data, exist_ok=True)
            test_file = os.path.join(local_data, ".write_test")
            with open(test_file, "w") as f:
                f.write("ok")
            os.remove(test_file)
            return local_data
        except OSError:
            pass  # Sem permissão de escrita local, usa fallback

    fallback_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), app_name)
    os.makedirs(fallback_dir, exist_ok=True)
    return fallback_dir
```

---

### 🔹 Pilar 2: Inclusão Determinística de Módulos Nativos (`.pyd`, `.dll`, `.so`)
Quando seu projeto consome C++ (PyBind11/Cython) ou Rust (PyO3), o binário compilado (`.pyd`) deve ser explicitamente declarado no `.spec` em `binaries` para que o PyInstaller resolva suas dependências dinâmicas no PE header (Windows).

- **Regra:** O compilador C++ e o interpretador Python usado no empacotamento **devem ter exatamente a mesma arquitetura e versão** (ex: CPython 3.14 64-bit com MSVC v143 x64).

---

### 🔹 Pilar 3: Dependências de Plataforma do Qt / Framework Gráfico
Se você usa PySide6 ou PyQt6:
- O PyInstaller precisa empacotar os plugins de plataforma (`platforms/qwindows.dll`).
- Drivers de software fallback como `opengl32sw.dll` devem ser incluídos para garantir que a interface abra mesmo em máquinas virtuais ou PCs antigos sem aceleração de hardware OpenGL.

---

### 🔹 Pilar 4: Executável Limpo sem Terminal Fantasma
Para aplicativos gráficos:
- Defina `console=False` no `.spec`.
- Isso evita que uma janela de prompt de comando preta abra junto com a janela do seu programa.

---

## 📑 4. O Arquivo Universal de Especificação (`app.spec`)

Salve este arquivo na raiz do seu projeto com o nome `portable_build.spec`. Ele é agnóstico e configurável:

```python
# -*- mode: python ; coding: utf-8 -*-
"""
portable_build.spec — Especificação Universal de Empacotamento Portátil
========================================================================
Compatível com Python 3.10+, PySide6/PyQt6, Módulos Nativos C++/Rust e Assets.
"""
import os
import sys

block_cipher = None

# 1. Configurações Principais do Seu Projeto
APP_NAME = "MeuSoftware"
ENTRY_POINT = "main.py"
ICON_FILE = os.path.join("assets", "icons", "app_icon.ico")

PROJECT_ROOT = os.path.abspath(os.path.curdir)

# 2. Definição de Arquivos de Dados (Assets, Temas, JSONs, Configs)
# Sintaxe: (caminho_origem_no_disco, pasta_destino_dentro_do__internal)
datas = []

optional_folders = ["assets", "templates", "locales", "plugins"]
for folder in optional_folders:
    folder_path = os.path.join(PROJECT_ROOT, folder)
    if os.path.exists(folder_path):
        datas.append((folder_path, folder))

# 3. Definição de Binários Nativos (.pyd, .dll C++, .so)
binaries = []

# Exemplo: Procura por qualquer .pyd ou .dll customizada na raiz
for file in os.listdir(PROJECT_ROOT):
    if file.endswith(".pyd") or (file.endswith(".dll") and not file.startswith("python")):
        binaries.append((os.path.join(PROJECT_ROOT, file), "."))

# 4. Hidden Imports (Módulos importados dinamicamente via importlib ou Qt plugins)
hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtSvg",
    "numpy",
    "ctypes",
]

# 5. Módulos a Excluir (Reduz drasticamente o tamanho final do pacote)
excludes = [
    "tkinter",
    "unittest",
    "pydoc",
    "test",
    "sqlite3",
]

# 6. Análise de Código e Dependências
a = Analysis(
    [os.path.join(PROJECT_ROOT, ENTRY_POINT)],
    pathex=[PROJECT_ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 7. Configuração do Executável Bootloader
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                    # Comprime binários se UPX estiver no PATH
    console=False,               # False = Sem janela preta de console
    disable_windowed_traceback=False,
    icon=ICON_FILE if os.path.exists(ICON_FILE) else None,
)

# 8. Coleta dos Arquivos para a Pasta '_internal'
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,               # Nome da subpasta gerada em dist/
)
```

---

## ⚡ 5. Script Completo de Automação de Build (`package_portable.py`)

Crie o arquivo `package_portable.py` na raiz do seu projeto. Ele cuida do ciclo completo: compilação, injeção de documentação, geração do `.zip` e validação com teste de fumaça:

```python
"""
package_portable.py — Pipeline de Build e Distribuição Portátil 1-Click
=======================================================================
Uso:
    python package_portable.py
"""
from __future__ import annotations
import os
import sys
import shutil
import subprocess
import time
import zipfile

# CONFIGURAÇÕES DO PROJETO
APP_NAME = "MeuSoftware"
APP_VERSION = "v1.0.0"
DIST_DIR = os.path.abspath("dist")
APP_OUTPUT_DIR = os.path.join(DIST_DIR, APP_NAME)
ZIP_OUTPUT_NAME = f"{APP_NAME}_{APP_VERSION}_Portable.zip"

def log_step(step: str, msg: str):
    print(f"\n\033[1;34m[{step}]\033[0m \033[1m{msg}\033[0m")

def clean_previous_builds():
    log_step("1/5", "Limpando diretórios de builds anteriores...")
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            shutil.rmtree(folder, ignore_errors=True)
            print(f"   -> Removido: {folder}/")
    if os.path.exists(ZIP_OUTPUT_NAME):
        os.remove(ZIP_OUTPUT_NAME)
        print(f"   -> Removido arquivo ZIP anterior: {ZIP_OUTPUT_NAME}")

def run_pyinstaller():
    log_step("2/5", "Executando PyInstaller (Standalone Onedir Engine)...")
    spec_file = "portable_build.spec"
    
    if not os.path.exists(spec_file):
        print(f"❌ Erro: Arquivo de especificação '{spec_file}' não encontrado!")
        sys.exit(1)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        spec_file
    ]
    
    res = subprocess.run(cmd)
    if res.returncode != 0:
        print("❌ Erro durante o empacotamento com PyInstaller.")
        sys.exit(res.returncode)
    print("✅ Binários empacotados com sucesso.")

def inject_documentation_and_support():
    log_step("3/5", "Injetando arquivos de apoio na raiz do pacote portátil...")
    
    # Cria um LEIA-ME caso não exista
    readme_path = os.path.join(APP_OUTPUT_DIR, "LEIA-ME_PORTATIL.txt")
    if not os.path.exists(readme_path):
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(f"==================================================================\n")
            f.write(f" {APP_NAME} — {APP_VERSION} (Versão Portátil Autocontida)\n")
            f.write(f"==================================================================\n\n")
            f.write(f"Como usar:\n")
            f.write(f"1. Extraia o arquivo .zip para qualquer pasta.\n")
            f.write(f"2. Execute: {APP_NAME}.exe\n\n")
            f.write(f"Não requer instalação nem permissões de administrador.\n")
        print(f"   -> Criado: LEIA-ME_PORTATIL.txt")

    # Copia outros arquivos auxiliares se existirem
    aux_files = ["LICENSE", "Enviar_Feedback.html", "CHANGELOG.md"]
    for file in aux_files:
        if os.path.exists(file):
            shutil.copy2(file, os.path.join(APP_OUTPUT_DIR, file))
            print(f"   -> Copiado para a raiz: {file}")

def create_portable_zip():
    log_step("4/5", f"Compactando diretório em {ZIP_OUTPUT_NAME}...")
    
    with zipfile.ZipFile(ZIP_OUTPUT_NAME, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        for root, dirs, files in os.walk(APP_OUTPUT_DIR):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, start=DIST_DIR)
                zipf.write(abs_path, rel_path)
    
    zip_size_mb = os.path.getsize(ZIP_OUTPUT_NAME) / (1024 * 1024)
    print(f"✅ Arquivo ZIP gerado: {ZIP_OUTPUT_NAME} ({zip_size_mb:.2f} MB)")

def smoke_test_executable():
    log_step("5/5", "Executando Teste de Fumaça (Smoke Test) no executável portátil...")
    exe_path = os.path.join(APP_OUTPUT_DIR, f"{APP_NAME}.exe")
    
    if not os.path.exists(exe_path):
        print(f"❌ Executável não encontrado em: {exe_path}")
        sys.exit(1)

    print(f"   -> Testando inicialização de: {exe_path}")
    proc = subprocess.Popen([exe_path])
    time.sleep(3)  # Aguarda 3 segundos para detectar crash imediato
    
    exit_code = proc.poll()
    if exit_code is None:
        print("   -> 🟢 Executável inicializou normalmente sem crashes de DLL ou Python!")
        proc.terminate()
    else:
        print(f"   -> 🔴 FALHA NO SMOKE TEST: Executável encerrou com código {exit_code}")
        sys.exit(1)

if __name__ == "__main__":
    print(f"🚀 Iniciando Pipeline de Empacotamento Portátil para '{APP_NAME}'...")
    clean_previous_builds()
    run_pyinstaller()
    inject_documentation_and_support()
    create_portable_zip()
    smoke_test_executable()
    print("\n🎉 \033[1;32mPIPELINE CONCLUÍDO COM SUCESSO! PACOTE PRONTO PARA DISTRIBUIÇÃO.\033[0m\n")
```

---

## 🛠️ 6. Guia de Resolução de Problemas (Troubleshooting)

### ❌ 1. O `.exe` abre e fecha instantaneamente (sem mensagem de erro)
- **Causa:** Um erro de importação ocorreu antes da interface gráfica inicializar.
- **Diagnóstico Rápido:** Altere temporariamente no seu `.spec` a linha `console=False` para `console=True`. Recompile e rode pelo terminal para ver o traceback completo do Python.

### ❌ 2. `ModuleNotFoundError: No module named 'meu_pacote'`
- **Causa:** O módulo foi importado dinamicamente ou através de plugins que o PyInstaller não detectou na análise estática.
- **Solução:** Adicione o nome do módulo na lista `hiddenimports = ['meu_pacote']` no arquivo `.spec`.

### ❌ 3. `ImportError: DLL load failed while importing meu_modulo_nativo`
- **Causa:** O arquivo `.pyd` depende de DLLs C++ que não estão no `PATH` ou a versão do Python é incompatível (ex: compilado para Python 3.12, mas empacotado com Python 3.14).
- **Solução:** Verifique se as DLLs do Visual C++ (`VCRUNTIME140.dll`, `MSVCP140.dll`) estão presentes no `_internal` e certifique-se de compilar o `.pyd` com o mesmo executável Python que roda o PyInstaller.

### ❌ 4. Janela Qt não renderiza ou dá erro de `platforms plugin "windows"`
- **Causa:** O plugin `qwindows.dll` não foi copiado.
- **Solução:** O PyInstaller resolve isso automaticamente se `PySide6` for incluído nos `hiddenimports`. Certifique-se de que a pasta `_internal/PySide6/plugins/platforms/qwindows.dll` existe.

---

## 📋 7. Checklist Rápido de Aplicação

- [ ] Arquivo `path_resolver.py` implementado no projeto para carregar assets via `sys._MEIPASS`.
- [ ] Arquivo `portable_build.spec` criado na raiz.
- [ ] Script de automação `package_portable.py` configurado com o nome do aplicativo.
- [ ] Executar `python package_portable.py`.
- [ ] Testar a descompactação do `.zip` em uma máquina sem Python instalado para homologação final.
