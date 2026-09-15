# 🏛️ Governança Arquitetural ARCcC (Atomic Recursive Componentization by Contract)

O **Lumenia Art Studio** é construído estritamente sob a metodologia **ARCcC** (*Atomic Recursive Componentization by Contract*). O ARCcC é um modelo de governança arquitetural projetado para garantir modularidade extrema, manutenibilidade a longo prazo, isolamento de falhas e ausência de dependências circulares em sistemas híbridos (C++20 + Python).

---

## 📐 1. Princípios Fundamentais do ARCcC

1. **Atomicidade e Responsabilidade Única (SRP)**:
   - Todo módulo ou componente deve resolver uma única responsabilidade funcional bem delimitada.
   - Classes monolíticas de "Deus" (God Objects) são formalmente proibidas.

2. **Recursividade Componentizada**:
   - Componentes complexos são decompostos recursivamente em subcomponentes atômicos.
   - Um painel complexo, por exemplo, é composto por painel base, controladores de eventos, mixins de estado e componentes visuais isolados.

3. **Contratos Estritos e Tipados**:
   - Toda comunicação entre a camada nativa (C++) e a interface (Python) é mediada por contratos formais tipados:
     - Interfaces abstratas no C++ (`PaintEngineFacade`).
     - Contratos de tipagem estática no Python (`bridge/boundary/contracts/aladyn_engine_native.pyi`).
     - Contratos de backend abstratos (`ui/core/engine/backend.py`).

4. **Isolamento de Efeitos Colaterais via Mixins Especializados**:
   - Em vez de uma classe backend gigante, o `AladynBackend` herda linearmente de mixins atômicos especializados por domínio:
     - `AladynMdiMixin`: Gestão de instâncias multi-documento em tempo $O(1)$.
     - `AladynSelectionMixin`: Máscaras de seleção e operações booleanas.
     - `AladynTransformMixin`: Motores de interpolação e matrizes afins.
     - `AladynGeometryMixin`: Guias de perspectiva, réguas e simetria radial.
     - `AladynLayerMixin`: Árvore hierárquica de camadas e filtros.
     - `AladynBrushMixin`: Parâmetros de pincéis e curvas dinâmicas.
     - `AladynStrokeMixin`: Ciclo de vida de traço, interpolação e telemetria.
     - `AladynColorMixin`: Perfis ICC, transformações LittleCMS e soft-proofing.
     - `AladynCapabilitiesMixin`: Publicação explícita de capacidades suportadas.

---

## 🚦 2. A Métrica de Linhas de Código (Teto Estrito de 450 LOC)

Para impedir o surgimento de classes infladas e débitos técnicos ocultos, o projeto aplica a **Regra dos Tetos de Linhas de Código**:

| Zona | Linhas de Código (LOC) | Classificação | Ação Exigida |
|---|:---:|:---:|---|
| 🟢 **Zona Verde** | $\le 250$ LOC | Ideal / Atômico | Nenhuma. Código com excelente modularidade. |
| 🟡 **Zona Amarela** | $251$ a $449$ LOC | Aceitável / Alerta | Monitoramento. Módulos coesos permitidos. |
| 🔴 **Zona Vermelha** | $\ge 450$ LOC | **VIOLAÇÃO GRAVE** | **Refatoração imediata obrigatória**. Nenhuma PR ou release é aceito com arquivos na Zona Vermelha. |

### Censo Atual do Projeto:
- Total de arquivos Python na Zona Vermelha: **0 (ZERO)**.
- Todos os 13 arquivos anteriormente na Zona Vermelha foram modularizados e divididos em submódulos coesos.

---

## 🛡️ 3. Regras de Fronteira e Pilares

O projeto é particionado em 4 pilares com regras rígidas de importação:

1. **`engine/` (C++20)**: Núcleo matemático e de renderização. **NÃO possui qualquer dependência de Python ou Qt**. Depende apenas da STL e opcionalmente OpenMP.
2. **`bridge/` (C++/PyBind11)**: Traduz chamadas do Python para a facade C++ e expõe tipos primitivos seguros (buffers imutáveis, strings, tuplas).
3. **`ui/` (Python/PySide6)**: Camada de apresentação e orquestração. Não realiza pintura de pixels direta em CPU/GPU; delega integralmente ao backend através da interface abstrata `EngineBackend`.
4. **`plugins/`**: Módulos desacoplados que estendem funcionalidades através da API de plugins (`ui/core/plugins/manager.py`), sem acoplamento direto com detalhes internos de outros plugins.\n