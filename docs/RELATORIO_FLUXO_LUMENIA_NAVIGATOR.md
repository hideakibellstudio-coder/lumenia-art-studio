# Relatório: o fluxo Lumenia ↔ ARCcC-Navigator

*(2026-09-15 — documento vivo. Complementa `relatorio-visao-estrategica-lumenia.md`, que descreve o produto; este descreve o método de construí-lo.)*

---

## 1. O que mudou no fluxo de desenvolvimento

Até a Fase 2, o desenvolvimento do Lumenia seguia o ciclo normal: decidir o que
construir, construir, testar, seguir. A malha de 390 testes cobria
comportamento — o programa faz o que deve fazer? — e o teto de 450 LOC cobria
tamanho. Os dois funcionam, e os dois têm o mesmo ponto cego: **não dizem nada
sobre as ligações entre as partes.**

Um teste verde prova que um caminho específico funciona hoje. Não prova que
`ui/core/dialogs/` não está chamando direto um método do motor nativo pelas
costas do adaptador. Não prova que mudar a assinatura de `LayerManager` não vai
quebrar três plugins que a acessam por despacho dinâmico. Essa classe de defeito
não aparece em teste: aparece meses depois, quando alguém mexe na camada de
baixo e algo sem relação aparente para de funcionar.

O novo fluxo acrescenta uma terceira pergunta ao ciclo, entre "construir" e
"seguir":

> **O que exatamente depende do que eu acabei de mexer — e o índice consegue
> provar isso, ou só supor?**

Quem responde é o ARCcC-Navigator, e a resposta é sempre classificada em uma de
cinco categorias epistemológicas. Essa classificação é o coração do método, e
vale explicá-la pelo que ela *recusa* a fazer:

| Categoria | O que significa |
| :--- | :--- |
| `confirmed_violation` | Regra violada **com prova estática concreta**. |
| `suspicious` | Padrão de risco **sem** resolução definitiva. |
| `uncheckable` | Dinamismo fora do alcance da análise estática. |
| `declared_exception` | Exceção autorizada e justificada formalmente. |
| `insufficient_info` | Falta de dados — sintaxe, compdb ausente. |

A maioria das ferramentas de análise colapsa isso em "erro" e "aviso", e por
isso produz listas que ninguém lê: um aviso pode ser um defeito real ou pode ser
a ferramenta não tendo entendido o código, e não há como saber sem investigar um
por um. Separar "eu provei" de "eu não consegui descartar" é o que torna o
relatório utilizável. **`suspicious` não é uma acusação; é a ferramenta
admitindo ignorância de forma auditável.**

---

## 2. Por que corrigir a base em vez de adicionar features

O argumento direto: **cada relação não resolvida é um lugar onde uma mudança
futura pode quebrar algo de forma invisível.**

Quando o Navigator consegue ligar `doc.zoom` ao símbolo `Document.zoom`, isso
vira uma aresta no grafo, e o comando `impact` passa a responder de verdade
"o que quebra se eu mexer aqui". Quando não consegue, o acesso existe no código
mas não existe no mapa. A análise de impacto, então, é adivinhação — e qualquer
refatoração feita em cima dela é feita no escuro.

Isso é exatamente o oposto do que a Fase 3 exige. Buffers de 16-bit/float e
shaders GPU não são features de superfície: são trocas nas camadas mais fundas
do pipeline, que tudo o mais atravessa. Fazer isso com um grafo incompleto é a
receita conhecida de regressão que ninguém consegue rastrear — o bug aparece em
aquarela porque alguém mexeu no buffer de composição, e três dias se vão até
alguém ligar uma coisa à outra.

Há também o argumento econômico, que no caso deste projeto não é secundário. Uma
feature nova adicionada sobre uma base não mapeada custa duas vezes: uma para
escrever, outra (maior, mais tarde, em momento pior) para descobrir o que ela
quebrou. Congelar features e mapear a base primeiro troca um custo futuro
incerto e alto por um custo presente conhecido e baixo.

**O congelamento não é conservadorismo. É sequenciamento.**

---

## 3. A simbiose: o projeto constrói a ferramenta

Esta é a parte que só ficou visível com o tempo, e é o achado mais interessante
de todo o esforço.

O ARCcC-Navigator **não foi projetado e depois aplicado ao Lumenia.** Cada
capacidade que ele tem hoje nasceu de uma falha que só um projeto grande, real e
heterogêneo conseguiu provocar. A cronologia das versões do extrator é, lida de
outro jeito, a lista de coisas que o Lumenia ensinou:

| Versão | O que o Lumenia revelou |
| :--- | :--- |
| **v4** | Flags MSVC repassadas cruas ao libclang desligavam **toda** a análise C++ em silêncio. Um motor inteiro fora da auditoria, com o relatório dizendo que estava tudo bem. |
| **v5** | O resolvedor confundia "alvo fora do projeto" (`os.path.dirname`) com "alvo interno que não consegui fixar". 59.735 falsas suspeitas. |
| **v6** | A extração perdia o receptor da expressão (`self.x` virava `x`) e duplicava cada chamada de método. |
| **v7** | Anotações de parâmetro não eram usadas para resolver `param.atributo`. |
| **v8** | A resolução por tipo anotado ignorava herança — e o Lumenia usa mixins pesadamente. |
| **v9** | Atributos de instância (`self.x = ...` no `__init__`) **nunca foram indexados**. Classes que declaram estado do jeito normal em Python apareciam no índice só com métodos. |

Nenhuma dessas foi antecipada. Todas foram descobertas porque o Lumenia é
grande o bastante (529 arquivos, Python + C++ + PyBind11 + `.pyi`), heterogêneo
o bastante e **real** o bastante para quebrar suposições que um corpus de teste
sintético jamais quebraria. Um projeto de brinquedo não tem mixins compostos,
nem um motor nativo compilado com MSVC, nem dublês de teste que colidem por nome
com classes de produção.

**O Lumenia é o documento de requisitos do Navigator, escrito em forma de
falhas.** E a relação é de mão dupla: cada capacidade nova do Navigator torna a
próxima auditoria do Lumenia mais precisa, o que expõe a próxima limitação, e
assim por diante. O ciclo se alimenta.

### O perigo que esse ciclo cria

Há um risco embutido que vale nomear, porque ele quase custou caro:
**uma ferramenta de governança que falha em silêncio produz falsa confiança —
exatamente o oposto do que o congelamento de features pretende comprar.**

O F-024 é o caso canônico. O relatório vinha limpo, com zero violações
comprovadas, e estava limpo porque a análise C++ estava desligada. Zero achados
sobre zero código analisado. Um relatório limpo sobre um índice vazio é pior que
um relatório sujo, porque um relatório sujo pelo menos te faz olhar.

Disso nasceu um critério de portão que não existia antes: **antes de confiar em
qualquer `verify`, a contagem de símbolos precisa ser plausível e não pode haver
`cxx_empty_extraction` em massa. A auditoria tem que provar que de fato olhou.**

---

## 4. O método que se firmou: medir antes de emendar

Uma coisa se repetiu tantas vezes nesta rodada que virou procedimento fixo.

Três hipóteses foram derrubadas por medição, nesta sessão apenas:

1. **"As 127 suspeitas vêm da falta do `compile_commands.json`."** Falso. O
   compdb foi gerado, `insufficient_info` caiu de 1 para 0 — e as 127 ficaram
   idênticas byte a byte.
2. **"Anotar `win: MainWindow` resolve as 61 relações."** Falso. Resolveu 23.
   As outras 38 vinham de mixins, e o resolvedor só olhava membros diretos.
3. **"A classe `RenderWidget` vence por ser grande; desempate por tamanho
   resolve."** Falso. `Document` não estava perdendo a disputa — **não estava na
   disputa**, porque seus atributos de instância nunca haviam sido indexados.

Nenhuma das três foi descoberta por raciocínio. Todas por rodar um script de
diagnóstico contra o banco real, ou por abrir e ler o código-fonte de um achado
de amostra. O raciocínio produziu três respostas confiantes e erradas; a medição
produziu três respostas certas.

O procedimento resultante, agora fixo:

1. **Simular a regra contra o banco real antes de ligá-la.** Os scripts
   `diagnose_relation.py`, `diagnose_mismatch.py` e
   `diagnose_missing_annotation.py` existem para isso: leem o SQLite direto,
   aplicam a lógica exata da regra e imprimem o que ela *acusaria* — sem alterar
   nada, sem reindexar, e em saída compacta o bastante para caber numa conversa.
2. **Ler a fonte de pelo menos um achado antes de confiar na regra.** Foi isso
   que pegou "anote `document` como `RenderWidget`" — recomendação confiante,
   100% de cobertura, e completamente errada.
3. **Só então commitar.**

O custo desse procedimento é um comando a mais. O custo de pular é commitar uma
regra que dá conselhos errados com aparência de certeza — e conselho errado com
aparência de certeza é pior que nenhum conselho, porque alguém age nele.

---

## 5. Onde o Lumenia está agora

Estado medido no snapshot `snap_1789442169_b1c2bb2f`:

| Métrica | Valor |
| :--- | ---: |
| `confirmed_violation` | **0** |
| `insufficient_info` | **0** |
| Símbolos indexados | 9.762 |
| Relações | 52.608 |
| Achados `suspicious` | 191 |
| Relações com classe-alvo **nomeada** | 834 |
| Zona Verde (<300 LOC) | 452 arquivos |
| Zona Amarela (300–449) | 50 arquivos |
| Zona Vermelha (≥450) | 4 arquivos, todos sob exceção declarada |

O número de suspeitas subiu de 105 para 191, e **isso é melhora, não piora.**
Antes, um único achado genérico engolia dezenas de relações e dizia apenas
quantas ficaram soltas. Agora 60 desses achados dizem **qual classe anotar** e
**quantas relações aquela linha converte** em arestas reais do grafo. Os maiores
concentram muito valor: `w: RenderWidget` resolve 97 de uma vez, `layer:
LocalLayer` resolve 44, `doc: Document` resolve 36. Cerca de dez arquivos cobrem
mais da metade das 834.

### O peso desses 60 achados na decisão da Fase 3

Eles **não são defeitos de comportamento.** O Lumenia roda exatamente igual com
ou sem as anotações. São lacunas de contrato declarado.

Mas o critério do portão é *"nenhuma dependência entre pilares escondida atrás
de dinamismo"*, e um receptor sem anotação **não é prova de que existe
dependência escondida — é prova de que a ferramenta não consegue descartar que
exista.** Anotar converte incerteza em fato nos dois sentidos: ou vira aresta
legítima, ou revela um acesso que não deveria estar ali. Enquanto não for feito,
os 834 acessos permanecem não-decididos, e um portão honesto não conta
não-decidido como aprovado.

---

## 6. O Navigator genérico: o que é realista

A ambição de rodar em qualquer projeto, convertê-lo para ARCcC e ainda corrigir
suas bases se decompõe em três problemas de dificuldade muito diferente. Vale
separá-los, porque um já está quase pronto e outro é pesquisa.

**(a) Analisar qualquer projeto — já funciona, faltando pouco.**
O extrator, o resolvedor, a prova de coerência, as cinco categorias e o pacote
de contexto não sabem nada sobre o Lumenia. São genéricos por construção. O que
é específico é o `LUMENIA_PROFILE`: quais são os pilares, quais dependências são
permitidas, quais exceções estão declaradas. Apontar o Navigator para outro
repositório Python/C++ hoje já produz zonas de LOC, grafo de símbolos, relações
resolvidas e o pacote de contexto. Só as regras de fronteira ficam mudas, por
falta de perfil.

**(b) Medir a distância até o ARCcC — é o produto real e está ao alcance.**
Este é o passo que eu argumentaria ser o mais valioso, e ninguém está fazendo.
Dado um repositório qualquer, inferir um perfil candidato a partir da estrutura
de diretórios existente, e então relatar: quantos arquivos passam do teto,
quais imports violariam a separação de pilares proposta, quais módulos têm
dependência circular, quais fronteiras já existem de fato ainda que sem nome.
Não converte nada — **mede o custo de converter**, com números. Para quem tem
um código legado e quer saber no que está se metendo antes de decidir, isso
vale por si só, e é uma extensão natural do que já está construído.

**(c) Converter automaticamente — outro tipo de problema.**
Mover arquivos e reescrever imports é mecânico. Decidir **o que é núcleo e o que
é fronteira** num código que nunca foi pensado assim é design, não análise, e
depende de intenção que não está no código. Uma ferramenta pode propor um
recorte e verificar se o recorte proposto se sustenta; não pode saber se é o
recorte certo. O caminho honesto aqui é assistivo: a ferramenta propõe, mede a
consequência da proposta, e a decisão continua humana.

A distinção que importa: **(a) e (b) são extensões do que já existe. (c) é um
produto diferente.** E (b) sozinho já é uma ferramenta que não tem equivalente
óbvio no mercado.

---

## 7. O efeito sobre o custo de operação

O objetivo declarado desta linha de trabalho era que **agentes mais fracos e
mais baratos conseguissem carregar o trabalho** — que o raciocínio caro ficasse
embutido na ferramenta, não fosse recomprado a cada sessão.

O que já é mensurável nessa direção:

- **Relatório de verificação via MCP:** 194.000 caracteres colados (~50.000
  tokens) reduzidos a cerca de 1.000 tokens, consultando e resumindo localmente.
- **Pacote de contexto:** 2.688 → 1.511 tokens com *mais* conteúdo útil, depois
  de corrigir quatro defeitos — seleção de símbolo, blocos duplicados, homônimos
  falsos que eram variáveis locais, e um corpo de função longo consumindo o
  orçamento inteiro.
- **Extração de relações:** 81.204 → 50.952 (−37%) removendo duplicatas, **sem
  perda de informação única** — verificado em dois arquivos reais: 39 pontos
  distintos de código cobertos antes e depois.
- **Achados acionáveis:** 834 relações que antes exigiam investigação humana
  agora vêm com a classe-alvo nomeada.

O último item é o mais importante dos quatro, e é qualitativamente diferente dos
outros três. Os três primeiros economizam tokens. O quarto **move a inteligência
para dentro da ferramenta**: "anote `layer` como `LocalLayer`; isso converte 44
relações" é uma instrução que qualquer agente executa corretamente, porque não
sobrou raciocínio para fazer. O raciocínio foi feito uma vez, no verifier, e
agora roda de graça a cada execução.

É essa a diferença entre uma ferramenta que economiza contexto e uma que
acumula competência.

---

## 8. Itens abertos

**No portão da Fase 3:**

- **F-020** — job de CI para o caminho AVX2. Patch pronto; `.github/workflows/`
  é caminho protegido e exige aplicação manual.
- **Teste de sessão longa** — memória e VRAM não devem crescer
  monotonicamente. Exige execução, não código.
- **Validação com artista real** fora da máquina de desenvolvimento. Idem.
- **As 60 anotações** — trabalho mecânico, com instrução explícita para cada um.

**No próprio Navigator:**

- **F-027, agravado** — `core/verifier.py` passou bem do teto de 450 LOC que a
  própria ferramenta impõe aos projetos que audita, e cresceu de novo nesta
  rodada. A ferramenta de governança está violando a governança. Não é urgente;
  é constrangedor, e vai piorar.
- **Assign simples no corpo de classe** — `sizeChanged = Signal(...)` ainda não
  é indexado. É por isso que os três achados de `panel` ficam em 62–75% em vez
  de 100%. Custa uma reindexação completa (~540s) sozinho; vale agrupar com a
  próxima mudança de extrator.
- **Anotação completa, contrato incompleto** — `win.menu_bar = MenuBar(win)`
  atribui estado de fora da classe, então esses atributos não são membros de
  `MainWindow`. É um achado legítimo e distinto dos 60, ainda não escrito.

---

## 9. Em uma frase

O Lumenia parou de ganhar features para ganhar **provas**; e o instrumento que
produz essas provas está sendo construído pelo próprio Lumenia, que é grande e
real o bastante para quebrá-lo de maneiras que nenhum teste sintético
conseguiria — de modo que cada auditoria deixa duas coisas mais sólidas, o
projeto e a ferramenta que o audita.
