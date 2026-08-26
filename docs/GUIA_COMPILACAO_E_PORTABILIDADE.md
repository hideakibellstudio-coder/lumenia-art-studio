# 📦 GUIA DE COMPILAÇÃO & EMPACOTAMENTO PORTÁTIL — LUMENIA

Este documento descreve o processo de configuração do ambiente, compilação do motor C++17 nativo, execução em desenvolvimento e geração do executável 100% autônomo e portátil (**Lumenia Alpha v0.2.0**).

---

## 1. Pré-Requisitos do Sistema

*   **Sistema Operacional:** Windows 10 / 11 (64-bit).
*   **Python:** Python 3.10 ou superior (Recomendado 3.12 ou 3.14).
*   **Compilador C++:** Microsoft Visual C++ (MSVC 2019/2022 v142/v143) ou LLVM/Clang com suporte a **C++17 e instruções SIMD (SSE2/AVX2)**.
*   **Dependências Python:**
    ```text
    PySide6>=6.6.0
    numpy>=1.24.0
    Pillow>=9.5.0
    pyinstaller>=6.0.0
    ```

---

## 2. Execução em Modo de Desenvolvimento

1.  **Clone ou abra o repositório:**
    ```powershell
    cd "z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\Lumenia"
    ```
2.  **Instale os pacotes necessários:**
    ```powershell
    pip install -r ui/requirements.txt
    ```
3.  **Execute o software:**
    ```powershell
    python ui/main.py
    ```

---

## 3. Como Gerar o Pacote Portátil Standalone (PyInstaller)

O Lumenia utiliza uma especificação customizada do PyInstaller para empacotar o executável com seu ícone oficial, o motor nativo C++ e todos os plugins em um diretório autônomo sem dependência de instalação.

### 📜 Especificação de Build (`Lumenia.spec`)

```python
# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None
project_root = r"z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\Lumenia"

a = Analysis(
    [os.path.join(project_root, 'ui', 'main.py')],
    pathex=[project_root],
    binaries=[
        (os.path.join(project_root, 'aladyn_engine_native.cp314-win_amd64.pyd'), '.'),
    ],
    datas=[
        (os.path.join(project_root, 'assets'), 'assets'),
        (os.path.join(project_root, 'plugins'), 'plugins'),
        (os.path.join(project_root, 'ui'), 'ui'),
    ],
    hiddenimports=[
        'PySide6', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets',
        'numpy', 'PIL', 'ctypes'
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Lumenia',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Sem janela de prompt piscando
    icon=os.path.join(project_root, 'assets', 'images', 'icon_lumenia.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Lumenia',
)
```

### ⚡ Comando de Build Automatizado

Execute no PowerShell:
```powershell
python -m PyInstaller --clean scratch/Lumenia.spec --distpath "z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\Lumenia_Alpha_Portable"
```

O resultado será a pasta:
📂 `Lumenia_Alpha_Portable/Lumenia/` contendo:
*   `Lumenia.exe` (Executável nativo com ícone oficial embutido)
*   `aladyn_engine_native.pyd` (Motor C++17)
*   `assets/` e `plugins/`
*   `Enviar_Feedback.html` (Formulário oficial de avaliação)
*   `LEIA-ME_TESTE_ALPHA.txt` (Instruções de uso)

---

## 4. Teste de Fumaça & Validação de Integridade

Para verificar se o build portátil inicia de forma limpa e sem erros de runtime:

```powershell
python -c "
import subprocess, time, sys
proc = subprocess.Popen([r'z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\Lumenia_Alpha_Portable\Lumenia\Lumenia.exe'])
time.sleep(2)
if proc.poll() is None:
    print('[OK] Lumenia.exe inicializou com sucesso e sem erros!')
    proc.terminate()
else:
    print('[FALHA] Executável encerrou com código:', proc.returncode)
"
```
