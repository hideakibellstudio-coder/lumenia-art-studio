# Pendências atuais da fase de correção da base

> Documento vivo. Sintetiza e substitui `historico/estado-da-base-2026-09-15.md`
> e a parte ainda acionável de `historico/auditoria-f017-f031-endurecimento-navigator.md`.
> Atualizado com verificação ao vivo no terminal em 2026-09-20 (não é estimativa
> nem cópia do relatório anterior). Toda mudança de status aqui deve vir com uma
> linha correspondente em `../README.md`.

**Regra de ouro desta fase:** nenhuma feature nova. Cada item abaixo remove
código, remove ambiguidade, ou adiciona verificação. Nada aqui é estético.

---

## ✅ Resolvido nesta sessão (2026-09-20, segunda rodada)

Estes três itens estavam listados como P0/P1 até esta rodada. Detalhes de
cada implementação estão no changelog do `../README.md`.

- **CI restaurada** — `.github/workflows/ci.yml` criado, com jobs `windows`
  (matriz 3.11/3.12/3.13, build `--simd scalar`) e `windows-avx2` (F-020,
  build `--simd avx2` com verificação explícita de carregamento do módulo).
- **Teste de regressão `.pyi` × binário compilado** —
  `tests/test_pyi_contract_matches_binary.py` criado, baseado em `ast`
  (não regex), comparando bidirecionalmente o contrato declarado com o
  módulo compilado. Aproveitado para remover 2 declarações mortas do
  `.pyi` (`get_pixel_data_size`, `get_display_pixel_data_size`).
- **`EngineBackend` dividido em protocolos por papel** —
  `ui/core/engine/backend_protocols.py` criado, com 11 `Protocol`s
  (`CoreLifecycleProtocol`, `StrokeProtocol`, `BrushProtocol`,
  `CanvasResourceProtocol`, `LayerProtocol`, `SelectionTransformProtocol`,
  `GeometryProtocol`, `TelemetryProtocol`, `ColorProtocol`,
  `RenderPipelineProtocol`, `HistoryProtocol`) cobrindo os 178 métodos de
  `EngineBackend`, gerados via `ast` a partir da classe real (não
  transcritos à mão) e verificados por `tests/test_engine_backend_protocols.py`
  (`isinstance()` de `AladynBackend` e `WgpuRustBackend` contra os 11
  papeis). **Importante:** isto é aditivo — `EngineBackend` continua
  existindo como contrato universal, sem nenhum método removido ou
  movido. O ganho é permitir testar/implementar um papel isoladamente
  sem precisar de um backend inteiro; não reduz, por si só, o tamanho de
  `EngineBackend` nem os `hasattr` do adaptador (ver P1 abaixo).

## 🟡 P1 — alto retorno, esforço baixo/médio

### Guardas `hasattr(self._facade, ...)`
107 → 12 entre 2026-09-15 e 2026-09-20 (queda de 89%). `02-simplificacao-da-ponte.md`
descreve o padrão de substituição (`_exigir_facade()` que lança em vez de
silenciar). Os 12 restantes são o que falta para fechar F-028 por completo.

### `EngineBackend` continua com 178 métodos na classe original
A divisão em protocolos (ver acima) nomeia o recorte natural, mas não
reduz a classe `EngineBackend` em si — ela segue sendo o contrato
universal com 152 → 178 métodos. O próximo passo natural, ainda não
feito, é avaliar se as implementações concretas (`AladynBackend`,
`WgpuRustBackend`) podem delegar a papeis internamente em vez de apenas
satisfazê-los estruturalmente.

## 🟢 P2 — menor urgência

- **~184 achados `suspicious` do Navigator** não triados individualmente
  (exceção declarada, ou investigado e aceito). Ver `03-protocolo-do-navigator.md`
  antes de interpretar qualquer achado — `suspicious` é limitação da
  ferramenta em construção de prova, não defeito automático do código.
- **Forward-reference em string não reconhecida pelo resolvedor do Navigator**
  (achado novo de 2026-09-20): `w: "RenderWidget" = self.widget` — padrão já
  estabelecido no próprio arquivo — continua marcado como `missing_type_annotation`
  mesmo correto. Limitação do Navigator, não do código Lumenia.

## ⚪ P4 — cobertura que nunca existiu

- Teste de sessão longa (`scripts/monitor_sessao.ps1` existe, sem critério de
  aprovação nem execução registrada como gate).
- Validação com artista real fora da máquina de desenvolvimento.

---

## Como este documento se relaciona com os outros

- `02-simplificacao-da-ponte.md` — o *como* dos itens P1 acima (guardas e
  protocolos por papel).
- `03-protocolo-do-navigator.md` — leitura obrigatória antes de interpretar
  qualquer número de `suspicious`/`confirmed_violation` citado aqui.
- `04-testes-e-qualidade.md` — como rodar a suíte que valida qualquer mudança
  feita a partir deste documento.
- `05-fluxo-lumenia-navigator.md` — o método geral de trabalhar com o Navigator
  ao longo de uma sessão de correção.
- `../historico/` — auditorias fechadas que geraram os números-base citados
  aqui (F-001 a F-031). Não são pendência; são proveniência.
