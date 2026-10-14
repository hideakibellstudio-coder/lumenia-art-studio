# `.github/` — configuração do GitHub

**Responsabilidade:** documentação operacional da integração contínua e do processo de compilação do Lumenia Art Studio.

## Porta de entrada

- Workflow manual: `workflows/ci.yml`.
- Guia de compilação para desenvolvedores: este arquivo.
- Regras arquiteturais obrigatórias: [`../AGENTS.md`](../AGENTS.md).

> **Resumo rápido:** o caminho oficial de compilação é **Windows x64**. Primeiro instalamos as ferramentas, depois criamos um ambiente Python, instalamos as dependências, compilamos o motor C++ e, por fim, executamos os testes ou geramos a versão portátil.

---

# Guia de compilação para iniciantes

Este guia explica, passo a passo, como preparar um computador Windows para compilar o projeto. Você não precisa conhecer C++ para seguir os passos, mas precisa copiar os comandos exatamente como aparecem.

## 1. O que será instalado

O projeto usa duas partes principais:

- **Python/PySide6:** interface visual do aplicativo.
- **C++20/pybind11:** motor nativo ALADYN, compilado como um arquivo `.pyd` que o Python carrega.

Instale os seguintes programas antes de começar:

1. **Git for Windows** — permite baixar o código-fonte.
2. **Python x64 3.11 ou superior** — escolha a versão de 64 bits.
3. **Visual Studio Build Tools** — fornece o compilador C++ da Microsoft.

### 1.1 Instalar o Git

Baixe e instale o Git for Windows. Durante a instalação, as opções padrão normalmente são suficientes.

Depois, abra o **PowerShell** e confira:

```powershell
git --version
```

Se aparecer um número de versão, o Git está instalado.

### 1.2 Instalar o Python

Instale o Python para Windows x64. Na primeira tela do instalador, marque:

```text
Add Python to PATH
```

Depois, feche e abra novamente o PowerShell e confira:

```powershell
py --version
python --version
```

O projeto requer Python 3.11 ou superior. Use sempre o mesmo Python para instalar dependências, compilar e executar o programa.

### 1.3 Instalar o compilador C++

Instale o **Visual Studio Build Tools**. No instalador, marque o workload:

```text
Desktop development with C++
```

Dentro desse workload, confirme que estão selecionados:

- MSVC Build Tools para x64/x86;
- Windows SDK;
- ferramentas padrão de compilação C++.

Após a instalação, reinicie o PowerShell. O script do projeto tenta localizar o Visual Studio automaticamente usando `vswhere.exe`. Também é possível abrir o atalho **x64 Native Tools Command Prompt for VS** e executar os comandos a partir dele.

---

## 2. Baixar o código do projeto

Escolha uma pasta de trabalho que não seja uma pasta temporária do Windows. No PowerShell, execute:

```powershell
mkdir $HOME\Projetos
cd $HOME\Projetos
git clone https://github.com/hideakibellstudio-coder/lumenia-art-studio.git
cd lumenia-art-studio
```

A partir deste ponto, todos os comandos deste guia devem ser executados dentro da pasta do projeto, a menos que o guia diga o contrário.

Confira se você está no local correto:

```powershell
Get-Location
Get-ChildItem
```

Você deve ver arquivos como `main.py`, `setup.py`, `pyproject.toml`, além das pastas `engine`, `bridge`, `ui`, `scripts` e `tests`.

---

## 3. Criar o ambiente virtual Python

O ambiente virtual mantém as dependências do Lumenia separadas de outros programas instalados no computador.

Crie o ambiente:

```powershell
py -3.11 -m venv .venv
```

Ative-o:

```powershell
.\.venv\Scripts\Activate.ps1
```

Quando estiver ativo, o PowerShell normalmente exibirá `(.venv)` no início da linha.

Confirme que o Python usado é o do ambiente virtual:

```powershell
python --version
python -c "import sys; print(sys.executable)"
```

O caminho exibido por `sys.executable` deve apontar para `.venv\Scripts\python.exe`.

### Se o PowerShell bloquear a ativação

Execute uma vez:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Feche e abra o PowerShell, volte para a pasta do projeto e tente novamente:

```powershell
.\.venv\Scripts\Activate.ps1
```

Como alternativa, use o Prompt de Comando:

```bat
.venv\Scripts\activate.bat
```

---

## 4. Instalar as dependências

Com o ambiente virtual ativo, atualize o instalador de pacotes:

```powershell
python -m pip install --upgrade pip
```

Para reproduzir o ambiente oficial Windows x64, instale o arquivo travado de dependências:

```powershell
python -m pip install --requirement requirements-dev.lock
```

Esse arquivo instala, entre outros componentes:

- PySide6 e Qt6 para a interface;
- NumPy, SciPy e Pillow para processamento de imagens;
- pybind11 para conectar Python e C++;
- pytest e pytest-qt para testes;
- Ruff para análise do código Python;
- Nuitka para gerar a distribuição portátil;
- Velopack para o fluxo de instalação e atualizações.

A opção `--require-hashes` já está no arquivo de lock. Ela verifica se os pacotes baixados correspondem exatamente aos arquivos aprovados pelo projeto.

Se o `pip` informar que não encontrou um wheel compatível, verifique se você está usando **Windows x64** e uma versão de Python suportada pelo arquivo `requirements-dev.lock`.

---

## 5. Ativar os hooks do Git

O projeto possui uma verificação automática antes de cada commit. Ative-a uma vez por clone:

```powershell
git config core.hooksPath .githooks
```

O hook chama `scripts/pre_commit.py`. Ele ajuda a impedir que código quebrado, artefatos temporários ou violações arquiteturais sejam commitados.

---

## 6. Compilar o motor C++ nativo

Esta é a etapa que transforma o código C++ do ALADYN Engine no módulo Python `aladyn_engine_native*.pyd`.

Com o ambiente virtual ativo e dentro da raiz do projeto, execute:

```powershell
python scripts/build_native.py --simd scalar
```

### O que o comando faz

O script:

1. localiza o compilador MSVC;
2. configura o ambiente de compilação x64;
3. compila o código C++20 e os bindings pybind11;
4. coloca objetos e intermediários fora do repositório, em `../build/temp_native`;
5. copia o módulo `.pyd` final para a raiz do projeto;
6. grava metadados em `../build/native-build.json`.

O modo `scalar` é o modo padrão e mais compatível. Use-o para desenvolvimento normal e para a distribuição pública.

### Recompilar tudo do zero

Se você alterou vários arquivos C++ ou suspeita que há objetos antigos, force a recompilação:

```powershell
python scripts/build_native.py --simd scalar --force
```

### Compilar com AVX2

Somente use AVX2 quando tiver certeza de que todas as máquinas de destino suportam essa instrução:

```powershell
python scripts/build_native.py --simd avx2 --force
```

Um arquivo compilado com AVX2 pode não abrir em computadores sem AVX2. Por isso, `scalar` deve ser o artefato público padrão.

### Gerar símbolos PDB para investigar crashes

Se for necessário analisar um minidump, gere os símbolos fora do repositório:

```powershell
python scripts/build_native.py --simd scalar --pdb
```

Os arquivos PDB ficam em `../build/pdb` e não devem ser commitados.

---

## 7. Confirmar que o módulo nativo foi carregado

Depois da compilação, execute:

```powershell
python -c "import aladyn_engine_native; print(aladyn_engine_native.__file__)"
```

O comando deve imprimir o caminho de um arquivo parecido com:

```text
...\lumenia-art-studio\aladyn_engine_native.cp311-win_amd64.pyd
```

O nome exato depende da versão do Python instalada. Deve existir apenas um arquivo `aladyn_engine_native*.pyd` na raiz do projeto.

---

## 8. Executar os testes

Primeiro, confira se o pytest consegue encontrar os testes:

```powershell
python -m pytest --collect-only -q
```

Depois, execute a suíte completa:

```powershell
python -m pytest
```

A entrega só deve continuar se os testes terminarem sem falhas.

Para executar um teste específico, informe o caminho do arquivo:

```powershell
python -m pytest tests/test_color_management_cms.py
```

---

## 9. Executar o linter

O linter verifica erros comuns no código Python:

```powershell
ruff check .
```

Se o Ruff encontrar um import não utilizado que possa ser removido automaticamente:

```powershell
ruff check --fix .
```

Revise as alterações depois do `--fix` antes de fazer um commit.

---

## 10. Abrir o aplicativo em modo de desenvolvimento

Com o ambiente virtual ativo e o motor compilado:

```powershell
python main.py
```

Também é possível usar o lançador do Windows:

```powershell
.\Launch_Lumenia.bat
```

Se o programa abrir mas o canvas não funcionar, repita a verificação do módulo nativo da seção 7 e confirme se o `.pyd` foi compilado para a mesma arquitetura e versão do Python em uso.

---

# Gerar a versão portátil `.exe`

A versão portátil contém o executável e os arquivos necessários para rodar em outro Windows sem o ambiente virtual do desenvolvedor.

Antes de iniciar, confirme que:

- o ambiente virtual está ativo;
- as dependências foram instaladas;
- o motor nativo foi compilado com `--simd scalar`;
- `python -c "import aladyn_engine_native"` funciona;
- os testes foram executados.

Gere a distribuição:

```powershell
python scripts/build_portable.py
```

Os artefatos intermediários ficam fora do repositório, normalmente em:

```text
../build/portable/
```

A saída final deve conter uma pasta semelhante a:

```text
../build/portable/Lumenia.dist/
├── Lumenia.exe
├── aladyn_engine_native.pyd
├── assets/
├── licenses/
└── release-manifest.json
```

O script também copia licenças de terceiros e gera `release-manifest.json` com hashes SHA-256 dos arquivos distribuídos.

Para escolher outro diretório externo:

```powershell
python scripts/build_portable.py --output ..\build\portable-release
```

Não copie apenas `Lumenia.exe`. Distribua a pasta `Lumenia.dist` completa. Teste-a em uma máquina Windows limpa, sem o `.venv`, para confirmar que todos os recursos, DLLs, plugins Qt, assets e licenças foram incluídos.

O instalador oficial é uma etapa separada. Depois de validar a distribuição portátil, siga [`../docs/03-guias/02-build-e-release.md`](../docs/03-guias/02-build-e-release.md).

---

# Regra de higiene dos arquivos gerados

O projeto usa compilação **out-of-tree**. Isso significa que os arquivos temporários de compilação devem ficar fora da pasta do repositório.

### Permitido

- `../build/temp_native/` — objetos e intermediários C++;
- `../build/portable/` — intermediários e saída portátil;
- `../build/pdb/` — símbolos PDB opcionais;
- `../dist/` — entregáveis finais de distribuição;
- pasta temporária do sistema — scripts e imagens de inspeção descartáveis.

### Proibido dentro do repositório

Não crie nem versione:

- `build/`, `dist/`, `tmp/`, `temp/`, `scratch/`, `dumps/`, `logs/` ou `test_outputs/`;
- arquivos `.obj`, `.ilk`, `.pdb`, `.lib`, `.coverage` ou dumps de crash;
- imagens de teste ou relatórios temporários;
- cópias antigas do `.pyd` em subpastas.

A única exceção operacional é o `aladyn_engine_native*.pyd` na raiz, porque o Python precisa encontrá-lo para executar e empacotar o aplicativo. Esse arquivo não substitui a limpeza dos intermediários externos.

Antes de finalizar qualquer alteração, confira:

```powershell
git status --short
```

Se aparecer um arquivo temporário que não deveria estar no repositório, remova-o antes de criar o commit.

---

# Solução de problemas comuns

## `Microsoft Visual C++ is required`

O compilador C++ não foi encontrado. Abra o Visual Studio Installer e instale o workload **Desktop development with C++**, incluindo o MSVC x64/x86 e o Windows SDK. Depois, abra um novo terminal.

## `vswhere.exe not found`

O script não conseguiu localizar a instalação do Visual Studio. Repare a instalação do Visual Studio Build Tools ou execute o comando a partir do **x64 Native Tools Command Prompt for VS**.

## `No module named aladyn_engine_native`

O motor ainda não foi compilado ou o `.pyd` não está na raiz correta. Execute:

```powershell
python scripts/build_native.py --simd scalar --force
```

Depois teste novamente:

```powershell
python -c "import aladyn_engine_native; print(aladyn_engine_native.__file__)"
```

## `DLL load failed`

Verifique:

1. se Python e MSVC são ambos x64;
2. se o `.pyd` foi compilado usando o mesmo ambiente Python que está executando o programa;
3. se o runtime do Visual C++ está instalado;
4. se a build é `scalar` quando a máquina não suporta AVX2;
5. se há somente um `aladyn_engine_native*.pyd` na raiz.

## O `pip install` falha por causa de hashes ou wheels

O lock oficial é voltado para Windows x64 e versões suportadas de Python. Confirme a arquitetura do Python:

```powershell
python -c "import platform; print(platform.architecture())"
```

Se você estiver usando outra plataforma ou versão não suportada, o lock pode não conter um pacote compatível. Não remova `--require-hashes` para tentar criar uma release reproduzível; corrija primeiro a versão do Python ou a plataforma.

## A versão portátil funciona no computador de compilação, mas não em outro

Não copie somente o `.exe`. Copie a pasta `Lumenia.dist` completa e teste novamente em uma máquina Windows limpa. Gere o bundle outra vez se algum arquivo ou DLL estiver faltando.

---

# Verificações antes de um commit

Execute, na ordem:

```powershell
python -m pytest
ruff check .
git status --short
```

Se a alteração tocar `engine/`, `bridge/` ou `setup.py`, também valide o build para Windows conforme as regras de [`../AGENTS.md`](../AGENTS.md).

O workflow do GitHub Actions não roda automaticamente em cada push ou pull request. Quando necessário, ele pode ser iniciado manualmente em:

```text
GitHub → Actions → Lumenia CI → Run workflow
```

Se um workflow manual falhar por erro do código, corrija o código antes de qualquer outra ação.

---

## Arquivos relacionados

| Arquivo | Finalidade |
|---|---|
| [`../AGENTS.md`](../AGENTS.md) | Regras arquiteturais, higiene e comandos canônicos. |
| [`../README.md`](../README.md) | Visão geral do projeto e guia resumido. |
| [`../setup.py`](../setup.py) | Lista de fontes C++ e configuração do módulo pybind11. |
| [`../pyproject.toml`](../pyproject.toml) | Metadados e dependências Python do projeto. |
| [`../requirements-dev.lock`](../requirements-dev.lock) | Dependências travadas para Windows x64. |
| [`../scripts/build_native.py`](../scripts/build_native.py) | Compilação do motor nativo C++. |
| [`../scripts/build_portable.py`](../scripts/build_portable.py) | Geração da distribuição portátil. |
| [`workflows/ci.yml`](workflows/ci.yml) | Workflow manual de integração contínua. |

## Regras

- O CI roda somente à mão, conforme decisão do dono do projeto em 25 de setembro de 2026.
- Cada alteração deve ser validada localmente com a suíte de testes; alterações em C++ também exigem a verificação de build para Windows.
- A política de compilação out-of-tree é obrigatória: intermediários e entregáveis não devem poluir a árvore do código.
- Quando o CI for disparado e ficar vermelho por erro do código, a correção deve vir antes de qualquer outra tarefa.
