# 🎯 Benchmark Competitivo de Produto & Rotas de Evolução

> **Documento Estratégico e Direcionador de Produto — Lumenia Art Studio**  
> **Ramo Associado:** `feature/evolucao-produto`  
> **Data de Emissão:** 2026-09-21  
> **Status:** Ativo / Direcionador da Fase de Evolução de Produto  
> **Relacionado:** [`01-visao-estrategica.md`](file:///z:/DESENVOLVIMENTO/+%20LUMENIA%20CLEAN/Lumenia/docs/05-visao-e-futuro/01-visao-estrategica.md), [`06-auditoria-orbital-decomposta.md`](file:///z:/DESENVOLVIMENTO/+%20LUMENIA%20CLEAN/Lumenia/docs/01-correcao-da-base/06-auditoria-orbital-decomposta.md)

---

## 1. Contexto e Transição de Fase

Com a conclusão da **Rodada 14** da metodologia de auditoria orbital, a base técnica do Lumenia atingiu solidez arquitetural comprovada:
- **725 testes automatizados (100% de aprovação)** cobrindo a UI, plugins, ponte PyBind11 e núcleo físico C++.
- **Zero Vazamentos de Recursos:** Gate de sessão longa aprovado ($\Delta\text{GDI} = 0$, $\Delta\text{Handles} = 0$, Drift de Memória Privada = $0.00\text{ MB} / 100\text{ ciclos}$).
- **Governança ARCcC:** 100% dos arquivos Python e C++ na Zona Verde (< 450 linhas).

Com a fundação saneada, o foco da branch **`feature/evolucao-produto`** passa a ser **o acabamento de produto e a competitividade da experiência do artista**. Em vez de dispersar esforço adicionando novas ferramentas do zero, o objetivo é **refinar o que já temos construído**, elevando a usabilidade e a fluidez ao patamar dos líderes de mercado.

---

## 2. Matriz Comparativa: O Que Temos vs Mercado

Ao comparar o Lumenia lado a lado com os 4 gigantes de software criativo:
- **Clip Studio Paint** (o padrão da indústria para lineart, arte-final e estabilização de traço)
- **Procreate** (o padrão de fluidez, minimalismo e sensibilidade tátil)
- **Krita** (a referência desktop para pintura profunda e arquitetura de camadas)
- **Infinite Painter** (a referência em harmonias cromáticas e interface orgânica)

Identifica-se que o Lumenia já possui o motor nativo e os recursos fundamentais, mas apresenta lacunas de acabamento distribuídas pelos **5 Grandes Rios**:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ RIO 1: TRAÇO & PINCEL (Procreate & Clip Studio)                                                 │
│ • O que temos: Estabilizador WMA (0-98%), Catmull-Rom, Pressão/Tilt/Twist, SIMD Dab Renderer.  │
│ • A Lacuna Competitiva:                                                                         │
│   1. Curva Global de Calibração de Pressão (mão leve vs mão pesada do artista).                 │
│   2. Tapering (Afilamento dinâmico de entrada e saída da ponta do traço).                       │
│   3. Mistura Úmida (Color Pickup / Wet Blending na ponta do pincel).                            │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ RIO 2: CÂMERA, VIEWPORT & AMBIENTE (Procreate & Photoshop)                                      │
│ • O que temos: Zoom 5%-3200%, Pan subpixel, Rotação 360°, Flip H/V, Navigator bidirecional.     │
│ • A Lacuna Competitiva:                                                                         │
│   1. Modo Clean Canvas / Tela Imersiva (Tecla Tab para ocultar painéis e focar na arte).        │
│   2. Duplo-clique para Fit-to-Screen rápido e reset instantâneo de rotação (0° snap).           │
│   3. Feedback visual discreto de Undo/Redo no topo (HUD Toast: "Desfazer: Traço").              │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ RIO 3: CAMADAS & PRODUTIVIDADE (Photoshop & Krita)                                              │
│ • O que temos: 13 Blend modes, grupos (Pass Through), Alpha Lock, Clipping Mask, Opacidade.     │
│ • A Lacuna Competitiva:                                                                         │
│   1. Solo Mode de Camada (Alt + Clique no olho para isolar temporariamente uma camada).         │
│   2. Renomeação In-Place direta na árvore com duplo-clique.                                     │
│   3. Atalho de teclado canônico Ctrl+E para Merge Down rápido.                                  │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ RIO 4: SELEÇÃO & TRANSFORMAÇÃO (Photoshop & Clip Studio)                                        │
│ • O que temos: Retângulo, Elipse, Varinha Mágica, Polígono, Marching Ants 60fps, Free Transform │
│ • A Lacuna Competitiva:                                                                         │
│   1. Expansão/Contração de Seleção (Expand/Contract de 1-5px para fechar gaps sob lineart).     │
│   2. Ajuste interativo de sensibilidade da Varinha Mágica (arraste de tolerância ao vivo).      │
│   3. Modos Skew (Cisalhamento) e Perspectiva nas 8 alças da Transformação Livre (Ctrl+T).       │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ RIO 5: COR & PALETAS (Infinite Painter & Clip Studio)                                           │
│ • O que temos: Roda HSL, Eyedropper HUD 4x, Perfis ICC LittleCMS, Prova de Daltonismo.           │
│ • A Lacuna Competitiva:                                                                         │
│   1. Histórico Vivo de Cores Recentes (Swatches automáticos gravados ao soltar a caneta).       │
│   2. Alternância instantânea de Cor Primária / Secundária via tecla "X".                        │
│   3. Guias de Harmonias Cromáticas na Roda (Análogas, Complementares, Triádicas).               │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. As 5 Rotas de Evolução Coesa

### Rota A — Rio 1: Traço & Sensibilidade ("The Brush Feel")
*Foco: Fazer o artista sentir que o traço responde à mão de forma orgânica e imediata.*
1. **Calibração Global de Curva de Pressão:**
   - Diálogo com curva Bezier editável com 3 pontos interativos.
   - Área de teste rápido de traço ao lado da curva.
   - Presets de sensibilidade: Suave (mão leve), Normal, Firme (mão pesada).
2. **Tapering (Afilamento de Ponta e Cauda):**
   - Interpolação de raio no início e final do traço baseada em velocidade/comprimento.
   - Essencial para lineart limpa, cabelos e arte-final de quadrinhos.
3. **Descarte Instantâneo de Traço em Andamento:**
   - Tecla `Esc` aborta o traço corrente sem registrar passo no histórico.

---

### Rota B — Rio 2: Viewport, Câmera & Imersão ("The Studio Experience")
*Foco: Eliminar qualquer distração entre o olhar do artista e o documento.*
1. **Modo Clean Canvas (`Tab`):**
   - Pressionar `Tab` recolhe suavemente as docas e barras laterais.
   - Hover na borda da tela exibe temporariamente os controles.
2. **Navegação Expressa:**
   - Duplo clique na ferramenta de zoom/pan aciona *Fit View* (enquadrar documento).
   - Duplo clique no slider de rotação ou botão dedicado restaura o ângulo para 0° com snap suave de 5°.
3. **HUD Toast de Ações no Canvas:**
   - Pequeno indicador semitransparente no topo central do viewport que surge por 1.2s ao acionar Undo/Redo:
     - `Desfazer: Traço de Pincel`
     - `Refazer: Preenchimento de Cor`
     - `Espelhado Horizontalmente`

---

### Rota C — Rio 3: Workflow de Camadas ("The Studio Pipeline")
*Foco: Reduzir os cliques e fricção no gerenciamento de arquivos complexos.*
1. **Solo Mode (`Alt + Clique no Ícone do Olho`):**
   - Isola a camada selecionada, ocultando todas as outras.
   - Um segundo `Alt + Clique` restaura o estado de visibilidade anterior exato de todas as camadas.
2. **Atalhos Canônicos de Camada:**
   - `Ctrl+E`: Mescla a camada ativa na inferior (*Merge Down*) respeitando clipping masks e modo de mesclagem.
   - `Ctrl+Shift+N`: Cria nova camada sem popup modal bloqueante.
3. **Edição In-Place do Nome da Camada:**
   - Duplo clique no texto do item da camada abre editor direto na linha (`QLineEdit` sem borda).

---

### Rota D — Rio 4: Seleção & Transformação de Alta Precisão
*Foco: Ferramentas de edição e recorte profissionais para coloristas e ilustradores.*
1. **Modificadores de Seleção (`Seleção -> Modificar`):**
   - `Expandir Seleção (Expand)`: Adiciona de 1 a 10px ao contorno ativo (vital para preencher cores sob lineart sem frestas brancas).
   - `Contrair Seleção (Contract)`: Reduz o contorno da seleção.
   - `Suavizar Borda (Feather)`: Aplica difusão gaussiana nas bordas da máscara.
2. **Distorção Livre e Cisalhamento na Transformação (`Ctrl+T`):**
   - Segurar `Ctrl` ao arrastar um vértice transforma em modo perspectiva livre.
   - Segurar `Ctrl + Shift` aplica cisalhamento (*skew*).

---

### Rota E — Rio 5: Cores & Harmonias Cromáticas
*Foco: Dar agilidade e inteligência cromática ao pintor digital.*
1. **Alternância Rápida de Cores Primária / Secundária (`X`):**
   - Tecla `X` inverte a cor primária de desenho com a cor secundária de suporte.
2. **Barra de Cores Recentes Viva:**
   - Fita dinâmica de 12 swatches no rodapé do painel de cores que acumula automaticamente as cores comitadas em traços e preenchimentos.
3. **Harmonias Cromáticas Interativas:**
   - Indicadores visuais na Roda de Cores para esquemas Complementares, Análogos e Triádicos em tempo real.

---

## 4. Princípios de Execução na Branch `feature/evolucao-produto`

1. **Um Rio por Vez:** O desenvolvimento deve focar em um único curso de rio do início ao fim, evitando dispersão.
2. **Preservação de Governança ARCcC:** Nenhum arquivo pode ultrapassar 450 linhas (Zona Verde).
3. **Zero Regressão:** Manter 100% dos 725 testes existentes verdes a cada incremento.
4. **Testes Dedicados por Rota:** Cada nova funcionalidade de rota deve vir acompanhada de sua respectiva suíte de validação de ponta a ponta.
