# PROTOCOLO DE AGENTE — ARCcC-Navigator

> Este arquivo é dirigido a **agentes de IA**, não a humanos. Siga-o literalmente.
> Ele define quando consultar o Navigator, como interpretar cada resposta, e o
> que é proibido fazer com ela. Ignorar este protocolo produz mudanças que
> passam nos testes e quebram a arquitetura.

**Configuração deste repositório** *(preencha ao adotar em outro projeto)*:

```
PROJETO   = Lumenia
PERFIL    = lumenia
NAVIGATOR = Z:\DESENVOLVIMENTO\+ LUMENIA CLEAN\ARCcC-Navigator
TETO_LOC  = 450 (erro) / 300 (aviso)
```

---

## 1. GATILHOS — quando você é obrigado a consultar

| Situação | Comando obrigatório | Antes ou depois |
| :--- | :--- | :--- |
| Vai alterar um símbolo existente | `navigator_context` naquele símbolo | **antes** de escrever |
| Vai alterar assinatura, contrato público ou `.pyi` | `navigator_impact` | **antes** de escrever |
| Vai criar arquivo novo | verificar o pilar de destino no perfil | **antes** de escrever |
| Terminou de escrever | `navigator_verify` | **depois** |
| Não sabe onde algo vive | `navigator_search` / `navigator_symbol` | a qualquer momento |

**Não leia dez arquivos para entender um símbolo.** `navigator_context` devolve o
contrato, os consumidores e o corpo relevante dentro de um orçamento de tokens.
Ler arquivos inteiros à mão é mais caro e menos completo.

---

## 2. PRIMEIRO DE TUDO: o relatório mentiu?

**Antes de ler qualquer achado**, confirme que a auditoria de fato olhou:

| Verificação | Valor aceitável | Se falhar |
| :--- | :--- | :--- |
| Contagem de símbolos | compatível com o tamanho do projeto | **PARE.** Índice incompleto. |
| `insufficient_info` | `0`, ou explicado | **PARE.** Avise o humano. |
| `cxx_empty_extraction` | ausente | **PARE.** Análise C++ desligada. |

**Um relatório limpo sobre um índice vazio parece perfeito.** Zero achados sobre
zero código analisado é o modo de falha mais perigoso desta ferramenta, e já
aconteceu neste projeto: um motor C++ inteiro ficou fora da auditoria por dias
enquanto o relatório dizia que estava tudo bem.

Se qualquer verificação falhar, **não relate "arquitetura limpa"**. Relate que o
índice está incompleto.

---

## 3. AS CINCO CATEGORIAS — o que cada uma exige de você

Esta é a parte que agentes erram com mais frequência. As categorias **não são
níveis de severidade**. São níveis de *certeza*.

| Categoria | Significa | O que você faz |
| :--- | :--- | :--- |
| `confirmed_violation` | Provado com evidência estática | **Corrija, ou declare exceção formal.** Nunca ignore. |
| `suspicious` | A ferramenta **não conseguiu decidir** | **NÃO é bug.** Leia a remediação. Se ela nomeia a ação, execute. Se não, deixe para o humano. |
| `uncheckable` | Dinamismo fora do alcance estático | Deixe. Nada a fazer. |
| `declared_exception` | **Autorizado** no perfil | **Não toque.** Corrigir isto é desfazer uma decisão deliberada. |
| `insufficient_info` | Faltam dados para julgar | Conserte a **entrada** (compdb, sintaxe), não o código. |

### O erro mais caro que você pode cometer

> Ver 191 `suspicious` e tentar "consertar" os 191.

`suspicious` significa que a **ferramenta** tem uma limitação, não que o
**código** tem um defeito. A maioria se resolve declarando um tipo, não mudando
comportamento. Mudar comportamento para calar um `suspicious` introduz bugs
reais para silenciar uma incerteza da ferramenta. **Isso é dano líquido.**

---

## 4. O QUE FAZER COM CADA TIPO DE ACHADO

| `rule_id` | Ação | Quem decide |
| :--- | :--- | :--- |
| `missing_type_annotation` | Adicione a anotação **se** a remediação nomear **uma** classe. Se disser "ou" entre classes, **pare e pergunte**. | Você / humano se ambíguo |
| `annotation_contract_mismatch` | Troque a anotação pelo tipo que a remediação nomeia. | Você |
| `dynamic_dispatch_risk` | **Não aja.** É resíduo sem instrução. Relate o número, siga em frente. | Humano |
| `forbidden_import` sem exceção | Roteie pela camada autorizada. Nunca adicione exceção por conta própria. | Humano aprova a exceção |
| `max_lines_error` | Decomponha em módulos coesos. Nunca comprima linhas para caber. | Você |
| `cxx_empty_extraction` / `clang_parse_error` | Problema de configuração, não de código. Avise. | Humano |

### Anotações: a regra estrita

Aplique uma anotação sugerida **somente** quando:

1. a remediação nomeia **exatamente uma** classe; **e**
2. a cobertura relatada é **100%**, ou os atributos não cobertos são
   explicáveis (sinais Qt, atributos atribuídos de fora da classe).

Quando a classe vem de outro módulo e o import pode criar ciclo, use:

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .modulo import Classe

def funcao(param: Classe) -> None: ...
```

Isso dá o tipo ao Navigator e a qualquer type checker **sem executar import
nenhum em tempo de execução**.

**Nunca invente uma anotação que a ferramenta não sugeriu.** Uma anotação errada
cria uma aresta falsa no grafo, e o grafo é a base de todas as outras respostas.

---

## 5. PROIBIÇÕES

| Proibido | Por quê |
| :--- | :--- |
| Rodar `index` via MCP | Bloqueia o servidor stdio e derruba a sessão. **Terminal apenas.** |
| Puxar o relatório `verify` inteiro | São ~194 mil caracteres. Use o sumário com `limit`. |
| Declarar exceção no perfil por conta própria | Exceção é decisão do humano, sempre. |
| "Consertar" `declared_exception` | É autorização deliberada. |
| Mudar comportamento para calar `suspicious` | Troca incerteza por bug. |
| Adicionar código a arquivo em zona amarela sem checar | Pode empurrar para zona vermelha. Cheque o LOC antes. |
| Apresentar referência textual como chamada confirmada | Confundir os dois é o defeito que esta ferramenta existe para evitar. |
| Relatar economia de caracteres como economia de tokens | Não é a mesma coisa. Meça ou não afirme. |

---

## 4.1 EM C++, PERGUNTE PELO CABEÇALHO

Para impacto em C++, **mire o `.hpp`, não o `.cpp`.**

O USR do Clang aponta para a declaração canônica, que vive no cabeçalho. Medido
neste projeto: das arestas C++ resolvidas, 2087 chamadas aterrissam em `.hpp`
contra 34 em `.cpp`. O cabeçalho é o contrato; o `.cpp` é **uma** das
implementações dele.

A diferença é real e não é bug. Exemplo medido no `Compositor`:

| alvo | impactados | arquivos |
| :--- | ---: | ---: |
| `Compositor.cpp` | 4 | 2 |
| `Compositor.hpp` | 11 | 8 |

Os dois estão certos. O `.cpp` implementa as sobrecargas com
`vector<unique_ptr<Layer>>`; seis orquestradores chamam as sobrecargas com
`vector<Layer*>`, declaradas no cabeçalho e implementadas em outro lugar. Mudar
o `.cpp` de fato não os atinge.

**Regra:** quer saber quem depende do contrato, pergunte pelo cabeçalho. Quer
saber quem depende desta implementação específica, pergunte pelo `.cpp`.

---

## 5.1 DUAS COISAS FICAM VELHAS POR MOTIVOS DIFERENTES

| Mudou o quê | O que fica velho | Como atualizar |
| :--- | :--- | :--- |
| Código **do projeto** | o índice (snapshot) | `index` no terminal |
| Código **do Navigator** | o processo do servidor MCP | **reiniciar o servidor MCP** |

O servidor lê o snapshot do banco a cada chamada, mas carrega os módulos Python
uma única vez, quando sobe. Uma correção no `core/` do Navigator **não tem
nenhum efeito** sobre as respostas via MCP até o servidor ser reiniciado — e as
respostas continuam chegando normalmente, com a cara de sempre, produzidas pelo
código antigo.

**Sintoma:** você corrigiu algo, reindexou, e a resposta veio idêntica à de
antes. Antes de concluir que a correção não funcionou, confirme que o servidor
foi reiniciado depois dela.

---

## 6. DEPOIS DE ESCREVER: a catraca

Rode `verify`. Compare com o número anterior.

- **Caiu ou igual** → siga.
- **Subiu** → você introduziu algo. Investigue **antes** de entregar.

Se a mudança tocou arquivos indexados, rode `index` no terminal antes do
`verify`, senão você está auditando a versão antiga.

---

## 7. QUANDO PARAR E PERGUNTAR

Pare e consulte o humano quando:

- a remediação oferece **mais de uma** classe candidata;
- corrigir exigiria **mover código entre pilares**;
- o achado sugere que a **arquitetura declarada** está errada, não o código;
- `confirmed_violation` aparece e a correção não é óbvia e local;
- as verificações de sanidade da seção 2 falharam.

**Você constata e executa instrução nomeada. Você não decide arquitetura.**
Decidir o que é núcleo e o que é fronteira depende de intenção que não está no
código — e o humano é quem tem a intenção.

---

## 8. RESUMO EM SETE LINHAS

1. Antes de mexer: `context`. Antes de mexer em contrato: `impact`.
2. Antes de ler achados: confirme que o índice não está vazio.
3. `suspicious` é incerteza da ferramenta, não defeito do código.
4. `declared_exception` não se toca.
5. Anotação só quando a remediação nomeia **uma** classe.
6. Depois de mexer: `verify`. O número não pode subir.
7. Ambiguidade, movimentação entre pilares, ou dúvida sobre a arquitetura:
   **pergunte**.
