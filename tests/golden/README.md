# `tests/golden/` — resultados de referência (golden)

**Responsabilidade:** guardar os hashes do resultado atual de composição e de traço, para detectar mudança não intencional no motor.

## Porta de entrada

Lidos por `tests/test_compositing_characterization.py`, `tests/test_stroke_characterization.py` `tests/test_brush_engines_characterization.py`, `tests/test_composite_projection.py` e `tests/test_bridge_contract_version.py`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `compositing_golden.json` | Hash dos pixels compostos por cenário (modos, filtros, grupos). |
| `stroke_golden.json` | Hash dos pixels do traço por combinação de latência e estabilizador. |
| `engines_golden.json` | Hash dos pixels dos 9 motores de pincel, 12 variações cada (simples, trava de alfa, seleção, máscara de recorte, textura, elipse, dureza 0 e 1, multiplicar, aditivo, parâmetros do motor, textura com parâmetros). |
| `engines_golden.win32.json` | Só as células dos 9 motores cujo hash difere no Windows. Sobrepõe `engines_golden.json` quando `sys.platform == "win32"`; as demais seguem o hash do Linux, ou seja, são bit a bit iguais nas duas plataformas. Medido no Windows em 2026-10-02, com o Óleo de cerdas, a elipse e o ângulo da ponta, o grão fixo e o arredondamento: nenhuma das 108 células diverge, então o arquivo está vazio (`{}`). Se uma mudança futura fizer o Windows divergir, regrave só as células que divergem, como em Regras. |
| `composite_projection_golden.json` | Um resumo (16 hex) de tudo o que a tela mostrou em 12 passos de cada uma de 300 sequências aleatórias de operações de documento (`tests/composite_sequences.py`), gravado com o motor de antes da projeção do buffer composto (S3): a tela de agora tem de mostrar os mesmos pixels. Lido por `tests/test_composite_projection.py`. Não é regravado para acomodar um resultado novo: a prova de que a leitura preguiçosa é correta é a comparação com a recomposição total, que não depende deste arquivo. |
| `bridge_contract.json` | A versão do contrato da ponte e o hash dos `.pyi`: mudar o contrato sem subir a versão reprova o teste. |

## Regras

- Mudança de pixel intencional: apague o golden correspondente, rode o teste para regravar e explique no commit por que o resultado mudou.
- O golden de referência (`*_golden.json`) é gravado no Linux (g++ -O2, escalar). Nunca regrave o de referência a partir do Windows: um hash do Windows que o Linux não reproduz reprovaria o Linux.
- Por que o Windows difere: a conta do traço é `float`/`double` e termina na conversão para byte (arredonda desde 2026-10-02; truncava antes). Uma diferença no último bit de uma chamada da libm (`pow`, `atan2`, `tan`, `sin`) entre o runtime da MSVC e o da glibc vira 1 nível de cor (o smudge chega a 3) em 1 a 10% dos pixels do traço; o alfa fica idêntico. Qual chamada exata causa não está provado.
- Divergência por plataforma: `engines_golden.<sys.platform>.json` guarda **somente** as células que diferem do referencial. Para regravar, rode `LUMENIA_RECORD_PLATFORM_PINS=1 python -m pytest tests/test_brush_engines_characterization.py` naquela plataforma. Sem essa variável o arquivo nunca é escrito, então uma rodada comum no Windows não aprova divergência nova sozinha.
- Toda célula nova no arquivo de plataforma precisa de explicação no commit (qual chamada, qual diferença). O diff do arquivo é a revisão: se uma célula que antes batia com o Linux entrou, é regressão até provar o contrário.
- `test_platform_pins_are_real_divergences` reprova célula inexistente ou com hash igual ao referencial. Se a conta ficar bit a bit igual (libm trocada, arredondamento no lugar de truncamento), o arquivo de plataforma encolhe até sumir.
- Sem arquivo de plataforma (por exemplo macOS), vale o referencial. Se divergir, grave o arquivo daquela plataforma como acima.

## Regravações de propósito (2026-10-02)

Cada uma mudou o resultado do motor de propósito; o antigo passava no pino antigo e o novo reprovava até a regravação.

- Conversão para byte: de truncar para arredondar (`MathUtils::roundToByte`). Mudou o último nível de cor de parte dos pixels.
- Marcador e Aquarela (24 células): a cor do miolo é a escolhida, uma vez só. Antes o azul (30, 90, 170) saía (21, 63, 123) no Marcador e (2, 7, 31) na Aquarela concentrada, porque cada carimbo multiplicava o resultado do anterior.
- Borrar (12 células): carrega um pedaço da imagem e o arrasta; antes colhia uma cor só.
- Óleo (12 células `oil__*`): feixe de cerdas com cor, carga e relevo iluminado. Os 12 pinos reprovavam no motor novo e passavam 33/33 no antigo; depois da regravação só essas 12 células mudaram (as outras 96 ficaram iguais) e os 299 testes do arquivo passam com 1 e com 4 threads. São 8 hashes distintos porque o Óleo não lê os modos de dab nem a textura de tela: simples, multiplicar, aditivo e texturizado dão o mesmo traço, e os dois de parâmetros também.
- Elipse e ângulo da ponta (24 células: Óleo 11, Pincel 3, Borracha 3, Lápis 3, Nanquim 1, Marcador 1, Borrar 1, Aquarela 1): a proporção da ponta do carimbo passou a valer nos sete motores que a ignoravam (7 células), e o ângulo da ponta deixou de ser sobrescrito pela direção do traço na spline, onde "seguir o traço" desligado girava a ponta mesmo assim (as outras 17, inclusive a direção do primeiro carimbo do Óleo). O antigo passava no pino antigo e o novo reprovava até a regravação; as outras 84 células ficaram iguais.

## Regravações de propósito (2026-10-09)

- Traço com estabilização (`stroke_golden.json`, 4 células: `raw` e `facade`, latência desligada, estabilização 50 e 98): a janela do estabilizador passou a ser de tempo (antes contava eventos) e o fim do traço drena o estabilizador pelo caminho, com o afunilamento dentro da cauda, em vez do segmento reto até a caneta e da cauda extrapolada além dela. As 4 células com estabilização 0 ficaram iguais, e `engines_golden.json` (todas as células a 0%) também. Os testes que descrevem o comportamento novo estão em `tests/test_stroke_release_tail.py`; no motor antigo 10 dos 14 reprovam.
