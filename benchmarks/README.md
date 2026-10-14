# `benchmarks/` — medidas de desempenho

**Responsabilidade:** medir o motor e os caminhos da aplicação que o usuário sente (cópia do canvas na repintura, entrada da caneta, salvar e abrir), em JSON comparável. É a "evidência" do ciclo ARCcC 4.4.8: o mesmo comando antes e depois de uma mudança de desempenho.

## Porta de entrada

- Motor: `python benchmarks/run_engine_benchmarks.py`.
- Aplicação: `python benchmarks/run_app_benchmarks.py` (`--only engine,ui,brush_engines,guides,files`, `--sizes 1920x1080`, `--quick` para checar o próprio executor).
- Comparar com uma rodada anterior: `python benchmarks/run_app_benchmarks.py --compare antes.json` (sai com 1 se alguma mediana piorar mais que `--tolerance`, 25% por padrão, acima do piso de ruído).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `run_engine_benchmarks.py` | Mede e exporta a linha de base do motor nativo (formato conferido por `tests/test_engine_benchmark_runner.py`). |
| `run_app_benchmarks.py` | Roda cada cenário da aplicação num processo próprio e junta o JSON; opção `--compare`. |
| `app_engine_paths.py` | Cenário `engine`: cópia do canvas inteiro, a região que a tela pede (1600×900 e 128×128), a vista afastada (pirâmide limpa, depois de uma mudança, a reconstrução inteira de referência e, com perfil de cor, depois de uma mudança), traço de 120 amostras (1 e 20 camadas), opacidade, desfazer e refazer, pelo contrato público do backend. |
| `app_ui_paths.py` | Cenário `ui`: abertura até a janela, documento novo, custo de cada amostra da caneta pelo roteador real e repintura do canvas (ajustado e a 100%). |
| `app_brush_engines.py` | Cenário `brush_engines`: traço rápido (40 px entre amostras, 4 ms de intervalo) com cada mini motor (pincel, lápis, nanquim, borracha, marcador, desfoque, borrão, aquarela, óleo) em três tamanhos sobre um canvas já pintado (desfoque e borrão não fazem nada em canvas vazio); custo de cada amostra (`sample.*`) e do traço inteiro (`stroke.*`), número de carimbos (`dabs.*`) e tempo por etapa do último traço (`stages_last_stroke`: raster, registro do desfazer, composição). Há também um caso com teto de opacidade (cópia de trabalho da camada). |
| `app_guides_paths.py` | Cenário `guides`: a caneta e a repintura do canvas com cada guia (régua, curva, 1/2/3 pontos, isométrica, curvilinear com tudo ligado) e cada simetria (espelho, radial, caleidoscópio) ligadas, contra `none` (sem guia): `hover_move`/`repaint_hover` (mouse passando sem botão: a conta do roteador e a repintura que ele pede, que com guia é o canvas inteiro), `pen_move`/`repaint_stroke` (traço), `repaint_idle` (nada mudou), `repaint_zoom` (cada passo de zoom muda a posição de toda linha) e `overlay_render` (a camada de guias pintada do zero). O preço de uma guia é a diferença para `none`. A janela é redimensionada para um tamanho de tela real (`viewport.*` diz quantos pixels o canvas mostra): uma pintura só cobre a parte visível. |
| `app_file_paths.py` | Cenários `files` (traços esparsos) e `files_dense` (camadas todas pintadas): salvar nas suas duas metades (`save_capture_ms` é a que trava a interface, `save_write_s` roda em outra thread) e abrir (`open_read_s` + `open_restore_s` é a abertura na thread da interface; `open_interface_s` e `open_event_loop_max_gap_ms` são a abertura como o aplicativo a faz, lendo e decodificando numa thread de fundo); tempo, tamanho e crescimento do pico de memória. |
| `compare_runs.py` | Compara dois resultados: medianas e totais, tolerância relativa e piso de ruído por unidade. |
| `app_common.py` | Resumo estatístico, repetição, leitura de tamanhos e do pico de memória (Linux/macOS por `resource`, Windows por `psapi`). |

## Regras

- Pode importar `aladyn_engine_native` diretamente (exceção da Lei nº 2 para benchmarks); os cenários da aplicação usam só o contrato público de `EngineBackend`.
- Sem limite de tempo fixo em teste: o que depende do hardware não é asserção. Os limites de S1 são conferidos comparando duas rodadas na mesma máquina.
- O cenário `ui` roda com `LUMENIA_DISABLE_OPENGL=1`: a plataforma offscreen não tem OpenGL, e com o widget GL todo `paintEvent` vira um no-op, o que deixaria o `drawImage` fora da repintura medida. As regiões repintadas dependem do recorte que o Qt faz da janela offscreen; o custo da aquisição por região está no cenário `engine` (`display_region_*`).
- A configuração do usuário não é tocada: cada cenário recebe um `LUMENIA_CONFIG_PATH` temporário.
- O ramo Windows de `peak_memory_mb` (psapi) não roda no Linux do agente; os números de memória do Windows ainda não foram conferidos.
