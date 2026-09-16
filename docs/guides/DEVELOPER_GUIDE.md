# 💻 Guia do Desenvolvedor (Developer Guide)

Este guia orienta a configuração de ambiente, fluxo de desenvolvimento e regras de conformidade para trabalhar na base de código do **Lumenia**.

---

## 🛠️ 1. Pré-requisitos de Ambiente

- **Sistema Operacional**: Windows 10/11 x64.
- **Python**: Versão 3.11 a 3.14 (64-bit).
- **Compilador C++**: Microsoft Visual Studio 2022 (MSVC 14.40+) com suporte a C++20 e CMake.
- **Ambiente Virtual**:
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\activate
  pip install -r requirements-dev.txt
  ```

---

## 📂 2. Estrutura de Diretórios Limpa

```text
Lumenia/
├── engine/              # Motor C++20 (isento de Python/Qt)
├── bridge/              # Camada PyBind11 e contratos .pyi
├── ui/                  # Aplicação Python / PySide6
│   ├── boundary/        # Shell e orquestradores de menu/canvas
│   ├── core/            # Núcleo de domínio (document, color, history, plugins)
│   ├── engine_backends/ # Adaptadores de motor e mixins
│   └── infrastructure/  # Logging, arquivos e utilitários
├── plugins/             # Plugins do ecossistema
├── assets/              # Ícones SVG, cursores e imagens
├── scripts/             # Automação de build e empacotamento
├── tests/               # 390 testes automatizados
└── docs/                # Documentação técnica unificada
```

---

## 📐 3. Padrões de Código e Verificação ARCcC

1. **Limite de Linhas de Código**: Nunca crie nem altere arquivos para que excedam **450 linhas de código (LOC)**. Se um arquivo estiver se aproximando de 400 LOC, divida-o preventivamente em subcomponentes ou mixins especializados.
2. **Preservação de Testes Verdes**: Todo commit deve manter a suíte de testes em **100% GREEN**:
   ```powershell
   python -m pytest
   ```
3. **Auditoria com o ARCcC Navigator**:
   Antes de submeter alterações de arquitetura, valide a conformidade com o ARCcC Navigator:
   ```powershell
   cd ..\ARCcC-Navigator
   python main.py index Lumenia
   python main.py verify Lumenia --profile lumenia
   ```\n