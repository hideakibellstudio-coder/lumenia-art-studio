# 🛡️ MANIFESTO: EMPACOTAMENTO PORTÁTIL BLINDADO COM NUITKA
> **Padrão Arquitetural para Compilação em Código de Máquina Nativo (Zero-Source-Code, Zero-Install, Boot Instantâneo) de Aplicações Python, PySide6/Qt e Extensões C++**

---

## 🧭 1. Introdução e Filosofia

O padrão tradicional de empacotamento em Python (baseado em PyInstaller) tem uma fragilidade grave para software comercial ou proprietário: **ele apenas empacota bytecodes (`.pyc`)**, os quais podem ser descompilados de volta para código-fonte legível em poucos segundos.

Para atingir **proteção total de propriedade intelectual**, sem abrir mão da **velocidade de boot instantânea** e da **simplicidade de um pacote portátil (descompactou -> usou)**, este manifesto adota o **[Nuitka](https://nuitka.net/)** como compilador oficial de distribuição.

### O Salto de Paradigma: PyInstaller vs. Nuitka

| Critério | PyInstaller Padrão | Nuitka Standalone (`--standalone`) |
| :--- | :--- | :--- |
| **Proteção do Código** | 🔴 **Nula**: Extraível e descompilável em segundos via `pycdc` ou `uncompyle6`. | 🟢 **Máxima**: Código Python é transpilado para **C** e compilado para **Assembly de Máquina (x86_64)** via MSVC/GCC. Não existem bytecodes. |
| **Velocidade de Abertura (Boot)** | ⚡ Rápido no modo `--onedir` (~1.0s). | ⚡ **Tão rápido ou mais rápido (~0.6s - 1.0s)**: Funções C nativas são chamadas diretamente na inicialização. |
| **Experiência do Usuário Final** | 📦 Pasta portátil com `.exe` (Zero-Install). | 📦 **Exatamente igual**: Pasta portátil com `.exe` (Zero-Install). |
| **Tamanho e Limpeza** | ⚖️ Inclui interpretador CPython e biblioteca padrão. | 🧹 Otimizado: Descarta bibliotecas não utilizadas do Qt e do Python. |
| **Tempo de Build (Para o Dev)** | ⚡ 30 a 60 segundos. | ⏳ 3 a 8 minutos (compilação C/C++ otimizada com `/O2`). |

---

## 🏛️ 2. Topologia do Pacote Portátil Nuitka Standalone

No modo `--standalone`, o Nuitka gera uma pasta autônoma (distribuível via `.zip`) com todo o ecossistema compilado:

```
📁 MeuSoftware_v1.0.0_Portable/
│
├── 🚀 MeuSoftware.exe                  ← Binário compilado em C puro (Sem Python legível)
├── 📄 LEIA-ME.txt                      ← Instruções rápidas para o usuário final
├── 🌐 Suporte_ou_Feedback.html         ← Guia ou formulário de feedback offline
│
├── ⚡ meu_modulo_nativo.*.pyd           ← Suas extensões C++ / PyBind11 já compiladas
├── ⚙️ python314.dll / vcruntime140*.dll ← Runtimes nativos necessários
│
├── 🎨 PySide6/ (ou PyQt6/)             ← DLLs Qt6 enxutas (apenas o que o app realmente usa)
│   ├── Qt6Core.dll, Qt6Gui.dll, Qt6Widgets.dll
│   └── plugins/platforms/qwindows.dll  ← Driver de janelas Windows
│
├── 📁 assets/                          ← Ícones (.ico, .svg, .png), temas, fontes
└── 📁 plugins/ (ou dados extras)       ← Plugins ou módulos dinâmicos adicionais
```

---

## 📐 3. Os 4 Pilares da Engenharia com Nuitka

### 🔹 Pilar 1: Resolução Canônica de Caminhos com Detecção de Código Compilado
O Nuitka injeta uma variável especial chamada `__compiled__` no runtime. Além disso, no modo `--standalone`, os assets ficam localizados diretamente na mesma pasta do executável principal (`sys.executable`).

Crie um módulo `path_resolver.py` universal para seu projeto:

```python
"""
path_resolver.py — Resolução de caminhos transparente para Dev e Nuitka Compilado.
"""
from __future__ import annotations
import os
import sys

def is_compiled_by_nuitka() -> bool:
    """Verifica se o código está rodando compilado pelo Nuitka."""
    return "__compiled__" in globals() or getattr(sys, "frozen", False)

def get_app_root() -> str:
    """
    Retorna o diretório raiz da aplicação:
    - Se compilado pelo Nuitka Standalone: diretório da pasta onde está o MeuSoftware.exe
    - Se em desenvolvimento (python main.py): diretório do projeto fonte.
    """
    if is_compiled_by_nuitka():
        return os.path.dirname(os.path.abspath(sys.executable))
    
    # Modo desenvolvimento: sobe os níveis necessários até a raiz
    return os.path.dirname(os.path.abspath(__file__))

def get_asset_path(*relative_parts: str) -> str:
    """Retorna o caminho absoluto determinístico para qualquer arquivo em assets/."""
    return os.path.join(get_app_root(), "assets", *relative_parts)

def get_portable_data_dir(app_name: str = "MeuSoftware") -> str:
    """
    Retorna o diretório para gravar configs, logs e preferências:
    - Modo Portátil: prioriza uma subpasta local 'data/' ao lado do executável.
    - Fallback: usa a pasta APPDATA se o diretório do app estiver em local somente-leitura.
    """
    app_root = get_app_root()
    local_data = os.path.join(app_root, "data")
    try:
        os.makedirs(local_data, exist_ok=True)
        test_file = os.path.join(local_data, ".write_test")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        return local_data
    except OSError:
        # Sem permissão de escrita local (ex: Arquivos de Programas)
        fallback = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), app_name)
        os.makedirs(fallback, exist_ok=True)
        return fallback
```

---

### 🔹 Pilar 2: Integração com Extensões C++ Existentes (`.pyd`)
Se o seu projeto consome um módulo C++ nativo (como o `aladyn_engine_native.*.pyd` compilado com PyBind11):
- O Nuitka é inteligente o suficiente para não tentar recompilar o que já é binário C++.
- Você apenas instrui o Nuitka a incluir esse `.pyd` no diretório raiz do pacote via flag:
  `--include-data-files=meu_modulo_nativo*.pyd=.`

---

### 🔹 Pilar 3: Plugin Especializado para PySide6 / PyQt6
Frameworks Qt exigem dezenas de arquivos auxiliares (traduções, plugins de plataforma como `qwindows.dll`, engines de renderização de SVG e drivers de fallback OpenGL).
- O Nuitka possui um plugin dedicado de altíssima eficiência: **`--enable-plugin=pyside6`**.
- Ele faz **análise estática** e remove módulos não utilizados do Qt (como `QtWebEngine`, `QtQuick3D`, etc.), economizando até 200 MB no tamanho final do pacote.

---

### 🔹 Pilar 4: Executável de Produção Windows (Sem Terminal Fantasma)
Para softwares com interface gráfica:
- `--windows-disable-console`: Impede que uma janela de prompt preta abra atrás da interface.
- `--windows-icon-from-ico=...`: Grava o ícone oficial dentro dos recursos do executável PE do Windows.
- `--windows-company-name=...` e `--windows-product-version=...`: Adiciona metadados profissionais aos detalhes do arquivo no Windows Explorer.

---

## ⚡ 4. O Comando Universal do Nuitka (CLI)

No PowerShell (ou prompt do VS 2022):

```powershell
python -m nuitka `
    --standalone `
    --enable-plugin=pyside6 `
    --windows-disable-console `
    --windows-icon-from-ico=assets/images/app_icon.ico `
    --windows-company-name="MinhaEmpresa" `
    --windows-product-name="MeuSoftware" `
    --windows-product-version="1.0.0.0" `
    --include-data-dir=assets=assets `
    --include-data-dir=plugins=plugins `
    --include-data-files=*.pyd=. `
    --output-dir=dist_nuitka `
    --remove-output `
    main.py
```

---

## 🤖 5. Script Completo de Automação de Build (`package_nuitka_portable.py`)

Salve este script na raiz do seu projeto. Ele gerencia o build do Nuitka, copia documentação complementar, gera o arquivo `.zip` portátil e executa um teste de fumaça (Smoke Test) automatizado:

```python
"""
package_nuitka_portable.py — Pipeline de Compilação Nativa & Empacotamento Blindado
===================================================================================
Executa a compilação C/C++ via Nuitka, injeta arquivos auxiliares e gera o .zip final.

Uso:
    python package_nuitka_portable.py
"""
from __future__ import annotations
import os
import sys
import shutil
import subprocess
import time
import zipfile

# -----------------------------------------------------------------------------
# ⚙️ CONFIGURAÇÕES DO PROJETO (Personalize para seu app)
# -----------------------------------------------------------------------------
APP_NAME = "MeuSoftware"
APP_VERSION = "v1.0.0"
ENTRY_POINT = "main.py"

ICON_PATH = os.path.join("assets", "images", "app_icon.ico")
OUTPUT_PARENT_DIR = "dist_nuitka"
# O Nuitka cria a pasta de saída nomeada como <entrypoint>.dist
NUITKA_DIST_DIR = os.path.join(OUTPUT_PARENT_DIR, f"{os.path.splitext(ENTRY_POINT)[0]}.dist")
FINAL_PORTABLE_DIR = os.path.join(OUTPUT_PARENT_DIR, APP_NAME)
ZIP_PACKAGE_NAME = f"{APP_NAME}_{APP_VERSION}_Portable.zip"


def print_step(step: str, description: str):
    print(f"\n\033[1;36m[{step}]\033[0m \033[1m{description}\033[0m")


def verify_prerequisites():
    print_step("1/6", "Verificando dependências de compilação...")
    try:
        import nuitka
        print(f"   -> Nuitka encontrado: versão {nuitka.__version__}")
    except ImportError:
        print("❌ Nuitka não instalado. Execute: pip install nuitka")
        sys.exit(1)


def clean_previous_builds():
    print_step("2/6", "Limpando diretórios de compilações anteriores...")
    for target in [OUTPUT_PARENT_DIR, ZIP_PACKAGE_NAME]:
        if os.path.isdir(target):
            shutil.rmtree(target, ignore_errors=True)
            print(f"   -> Removido diretório: {target}/")
        elif os.path.isfile(target):
            os.remove(target)
            print(f"   -> Removido arquivo: {target}")


def run_nuitka_compilation():
    print_step("3/6", "Executando compilação nativa C/C++ com Nuitka...")
    print("   ⏳ Isso pode levar entre 3 a 7 minutos (compilação completa com MSVC)...")
    
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--enable-plugin=pyside6",
        "--windows-disable-console",
        "--output-dir=" + OUTPUT_PARENT_DIR,
        "--remove-output",  # Remove a pasta de build temporária (.build) após finalizar
        "--assume-yes-for-downloads",
    ]

    # Adiciona ícone se existir
    if os.path.exists(ICON_PATH):
        cmd.append(f"--windows-icon-from-ico={ICON_PATH}")

    # Adiciona pastas de dados
    for folder in ["assets", "plugins", "templates", "locales"]:
        if os.path.exists(folder):
            cmd.append(f"--include-data-dir={folder}={folder}")

    # Inclui módulos nativos pré-compilados (.pyd) se houver
    for item in os.listdir("."):
        if item.endswith(".pyd"):
            cmd.append(f"--include-data-files={item}=.")

    # Ponto de entrada
    cmd.append(ENTRY_POINT)

    t0 = time.time()
    result = subprocess.run(cmd)
    t1 = time.time()

    if result.returncode != 0:
        print(f"❌ Falha na compilação do Nuitka (código {result.returncode}).")
        sys.exit(result.returncode)

    print(f"✅ Compilação C/C++ concluída em {t1 - t0:.1f} segundos!")

    # Renomeia <entrypoint>.dist para o nome canônico do App
    if os.path.exists(NUITKA_DIST_DIR):
        if os.path.exists(FINAL_PORTABLE_DIR):
            shutil.rmtree(FINAL_PORTABLE_DIR)
        os.rename(NUITKA_DIST_DIR, FINAL_PORTABLE_DIR)


def inject_auxiliary_files():
    print_step("4/6", "Injetando guias e documentação na raiz do pacote...")
    
    readme_file = os.path.join(FINAL_PORTABLE_DIR, "LEIA-ME_PORTATIL.txt")
    with open(readme_file, "w", encoding="utf-8") as f:
        f.write(f"====================================================================\n")
        f.write(f" {APP_NAME} — {APP_VERSION} (Versão Portátil Blindada)\n")
        f.write(f"====================================================================\n\n")
        f.write(f"Instruções:\n")
        f.write(f"1. Extraia o conteúdo deste arquivo para uma pasta qualquer.\n")
        f.write(f"2. Execute o arquivo: {APP_NAME}.exe\n\n")
        f.write(f"• 100% Autocontido: Não requer instalação nem privilégios de Admin.\n")
        f.write(f"• Código Nativo Compilado de Alto Desempenho.\n")
    print(f"   -> Criado: LEIA-ME_PORTATIL.txt")

    for aux in ["Enviar_Feedback.html", "LICENSE"]:
        if os.path.exists(aux):
            shutil.copy2(aux, os.path.join(FINAL_PORTABLE_DIR, aux))
            print(f"   -> Copiado: {aux}")


def create_portable_zip():
    print_step("5/6", f"Compactando pacote em {ZIP_PACKAGE_NAME}...")
    with zipfile.ZipFile(ZIP_PACKAGE_NAME, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        for root, dirs, files in os.walk(FINAL_PORTABLE_DIR):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, start=OUTPUT_PARENT_DIR)
                zipf.write(abs_path, rel_path)

    mb_size = os.path.getsize(ZIP_PACKAGE_NAME) / (1024 * 1024)
    print(f"✅ Pacote compactado gerado com sucesso: {ZIP_PACKAGE_NAME} ({mb_size:.2f} MB)")


def smoke_test_distribution():
    print_step("6/6", "Executando Teste de Fumaça (Smoke Test) no binário gerado...")
    
    # No Nuitka, o executável herda o nome do entrypoint ou do diretório
    exe_candidates = [
        os.path.join(FINAL_PORTABLE_DIR, f"{APP_NAME}.exe"),
        os.path.join(FINAL_PORTABLE_DIR, f"{os.path.splitext(ENTRY_POINT)[0]}.exe")
    ]
    target_exe = next((p for p in exe_candidates if os.path.exists(p)), None)

    if not target_exe:
        print(f"❌ Executável principal não localizado em {FINAL_PORTABLE_DIR}")
        sys.exit(1)

    print(f"   -> Abrindo processo para validação de boot: {target_exe}")
    proc = subprocess.Popen([target_exe])
    time.sleep(3)  # Aguarda 3 segundos para certificar que o boot ocorreu

    status = proc.poll()
    if status is None:
        print("   -> 🟢 Executável compilado abriu com sucesso e sem crashes de DLL!")
        proc.terminate()
    else:
        print(f"   -> 🔴 Erro de runtime: o executável encerrou prematuramente com código {status}")
        sys.exit(1)


if __name__ == "__main__":
    print(f"\n🚀 Iniciando Pipeline de Distribuição Blindada com Nuitka: {APP_NAME}\n")
    verify_prerequisites()
    clean_previous_builds()
    run_nuitka_compilation()
    inject_auxiliary_files()
    create_portable_zip()
    smoke_test_distribution()
    print(f"\n🎉 \033[1;32mDISTRIBUIÇÃO CONCLUÍDA! PACOTE FINAL BLINDADO DISPONÍVEL EM: {ZIP_PACKAGE_NAME}\033[0m\n")
```

---

## 💡 6. Dicas de Otimização e Performance do Nuitka

### 🚀 Acelerando Compilações com Cache (`ccache`)
Como o Nuitka compila dezenas de arquivos C++, compilações subsequentes podem demorar apenas segundos se o cache estiver ativo. O Nuitka faz o download automático do `ccache` no Windows caso você autorize (`--assume-yes-for-downloads`).

### 📦 Reduzindo o Tamanho Final (`--nofollow-import-to`)
Se o seu projeto importa alguma biblioteca que traz dependências pesadas e dispensáveis (como `matplotlib`, `pytest` ou ferramentas de teste), bloqueie sua inclusão:
```powershell
--nofollow-import-to=pytest,unittest,tkinter,scipy
```

### 🛡️ Por que NÃO usar `--onefile` em projetos grandes de GUI?
O Nuitka oferece a opção `--onefile`, que empacota tudo em um único `.exe`. No entanto, para softwares com PySide6 (que têm 100+ MB de DLLs Qt), o modo `--onefile` é obrigado a descompactar tudo na memória ou no disco temporário a cada clique do usuário, gerando um atraso de inicialização de vários segundos.
O modo **`--standalone` compactado em `.zip`** é o padrão ouro da indústria: **boot em menos de 1 segundo e integridade total**.

---

## 📋 7. Checklist Rápido de Adoção

- [ ] Instalar o Nuitka no ambiente virtual: `pip install nuitka`.
- [ ] Ter o Visual Studio 2022 instalado com o workload "Desenvolvimento para Desktop com C++".
- [ ] Implementar o `path_resolver.py` para carregar assets sem caminhos relativos frágeis.
- [ ] Rodar `python package_nuitka_portable.py`.
- [ ] Testar o executável extraído do `.zip` em uma máquina sem Python e sem Visual Studio.
