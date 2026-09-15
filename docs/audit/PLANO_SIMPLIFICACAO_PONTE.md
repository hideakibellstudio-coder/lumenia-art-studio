# Simplificar a ponte UI → motor

*(2026-09-15 — medido, não estimado. Nenhuma feature nova: só remoção e
unificação do que já existe.)*

---

## 1. O que foi medido

### A camada adaptadora `ui/engine_backends/`

| | |
| :--- | ---: |
| linhas | 1.861 |
| métodos | 182 |
| referências a `self._facade` | **451** |
| guardas `hasattr(self._facade, ...)` | **108** |

Isso é ~2,5 toques no facade por método: guarda, chamada, às vezes guarda de
novo. E 108 `hasattr` significa que o código **não confia** que o motor tenha o
método que ele está prestes a chamar.

### O contrato `ui/core/engine/backend.py`

| | |
| :--- | ---: |
| métodos em `EngineBackend` | **152** |
| sem corpo real (`pass` / `return {}`) | **137** |

90% da interface existe só para ser sobrescrita.

### A mesma propriedade, declarada N vezes

| propriedade | lugares |
| :--- | ---: |
| `brush_size` | 5 |
| `opacity` | 5 |
| `stabilizer` | 5 |
| `hardness` | 4 |
| `spacing_factor` | 2 |

Os cinco lugares: criação do widget, handler da UI, contrato abstrato,
adaptador concreto, e o par get/apply de preset.

---

## 2. O diagnóstico

**O comprimento da estrada não é o problema. O número de lugares que precisam
concordar é.**

Cinco saltos mecânicos seriam aceitáveis. Cinco *declarações independentes* da
mesma propriedade não são, porque elas divergem — e já divergiram: a regressão
do estabilizador corrigida hoje foi exatamente o lugar nº 5 (o preset) saindo de
sincronia com os lugares 2, 3 e 4.

E os 108 `hasattr` têm causa rastreável, encontrada hoje por acidente: **o `.pyi`
não bate com o módulo compilado.** O `PointerEvent` real aceita `tilt_x`,
`tilt_y` e `twist`; o contrato declara quatro campos. Se o contrato mente, ninguém
confia nele — e a desconfiança vira guarda defensiva em cada chamada.

A cadeia causal completa:

```
contrato não verificado
   → ninguém confia
      → guarda em toda chamada  (451 toques, 108 hasattr)
         → cada propriedade precisa ser declarada em todo nível
            → os níveis divergem
               → regressão silenciosa
```

Atacar as guardas sem consertar a raiz só as traz de volta.

---

## 3. O que fazer, em ordem

### Passo 1 — Verificar o contrato *(pequeno, alto retorno, faça primeiro)*

Um teste que compara o `.pyi` com o módulo **compilado**, por introspecção.
PyBind11 expõe as assinaturas no `__doc__` de cada método; `inspect` e
`dir()` dão o resto.

O teste falha hoje (achamos a divergência do `PointerEvent`), e é isso que o
torna valioso: ele transforma "o contrato pode estar errado" em "o contrato
está certo, provado a cada execução".

**Por que primeiro:** enquanto o contrato não for confiável, remover as 108
guardas é imprudente. Depois dele, é seguro — e cada guarda removida é um
ramo a menos para testar.

Custo: ~40 linhas de teste. Retorno: destrava os passos 2 e 4.

### Passo 2 — Uma tabela para as propriedades de pincel

Hoje cada propriedade aparece em cinco lugares. A proposta é declarar **uma
vez**, como dado:

```python
@dataclass(frozen=True)
class PropriedadeDePincel:
    chave: str              # chave do preset  ("brush_size")
    setter: str             # método do backend ("set_brush_size")
    leitura: Callable       # como ler do facade
    grupo: str | None = None   # para as que vão por set_brush_param
```

Dessa tabela derivam: os setters do adaptador, o `get_brush_profile_dict`, o
`apply_brush_preset_dict` e o `key_mappings` — que hoje são quatro listas
mantidas à mão, com ~46 entradas cada.

**Ganho medido:** elimina a possibilidade da regressão de hoje. Não reduz a
distância entre botão e motor; reduz o número de lugares que podem discordar,
que é o que de fato quebra.

**Cuidado:** o round-trip hoje é assimétrico — `get_brush_profile_dict` produz
42 chaves e não produz `engine_type`, `shape_preset` nem `brush_height_preset`.
A tabela precisa marcar explicitamente quais são só-escrita, senão a unificação
introduz perda de estado.

### Passo 3 — Alinhar o contrato aos mixins que já existem

`EngineBackend` tem 152 métodos numa classe só. Os mixins **já** definem o
recorte natural: pincel, camada, seleção, transformação, cor, geometria,
recursos, traço, MDI.

Trocar a interface única por protocolos por papel (`ControleDePincel`,
`ControleDeCamada`, …) não inventa estrutura — **nomeia a que já está lá**. E
cada papel passa a ser implementável e testável isoladamente, o que hoje é
impossível: para testar qualquer coisa é preciso um backend inteiro.

Custo: mecânico, mas toca muitos arquivos. Faça depois do passo 1.

### Passo 4 — Decidir sobre as 451 guardas

Duas opções, e elas têm risco diferente:

**(a) Facade nulo.** Um objeto no-op quando não há documento aberto, para que
`self._facade` nunca seja `None`. Some o `if self._facade` de centenas de
lugares.
*Risco:* silencia erro real. Chamar um motor inexistente passa a não fazer nada
em vez de falhar — o oposto da filosofia do resto do projeto.

**(b) Ponto único de entrada.** Um único `_exigir_facade()` que lança quando
não há contexto, e os métodos chamam sem guardar.
*Risco:* menor. Falha alto, no lugar certo, com mensagem.

**Recomendação: (b).** Ela remove a repetição sem trocar erro por silêncio. E
depois do passo 1, os `hasattr` somem de graça, porque o contrato passa a ser
garantido.

---

## 4. O que NÃO fazer

**Não faça os quatro de uma vez.** O passo 1 muda a natureza dos outros três: com
o contrato verificado, metade do trabalho dos passos 2 e 4 desaparece sozinho.

**Não encurte a estrada por encurtar.** A separação UI → contrato → adaptador →
motor é o ARCcC funcionando: é ela que permite o `wgpu_rust.py` existir ao lado
do `aladyn.py`. Colapsar camadas resolveria a sensação de distância e destruiria
a capacidade de trocar o motor — que é um dos pilares do projeto.

**O alvo é a duplicação de declaração, não o número de saltos.**

---

## 5. Ordem sugerida e critério de pronto

| passo | custo | pronto quando |
| :--- | :--- | :--- |
| 1. verificar o contrato | ~40 linhas | o teste passa e o `.pyi` bate com o `.pyd` |
| 2. tabela de pincel | médio | as 4 listas viram 1, e o teste de caracterização segue verde |
| 3. protocolos por papel | mecânico | cada papel tem teste próprio sem backend completo |
| 4. entrada única do facade | médio | `hasattr(self._facade` chega a zero |

Nenhum deles adiciona funcionalidade. Os quatro **removem** código.
