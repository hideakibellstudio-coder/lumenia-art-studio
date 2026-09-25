# `ui/plugins/panels/` — plugins de interface

**Responsabilidade:** os painéis e ferramentas que se encaixam no workspace (pincel, cor, camadas, navegador, geometria, gravação, telemetria...).

## Porta de entrada

Registrados em `ui/plugins/builtin_registry.py`; cada plugin recebe o `PluginContext` e pede serviços ao `ServiceRegistry`.

## Conteúdo

| Pasta | Responsabilidade |
|---|---|
| `brush_plugin/` | o painel da doca esquerda com a coluna de ferramentas, o seletor de presets, a prévia do traço, os parâmetros rápidos e a página de opções da ferramenta ativa; o painel avançado do pincel. |
| `color_plugin/` | o painel da roda de cores (HSV, harmonias, recentes) na doca esquerda. |
| `geometry_plugin/` | o painel de guias (réguas, simetria, perspectiva) e seus ajustes avançados. |
| `layers_plugin/` | o painel de camadas: árvore (modelo, view, delegate), opacidade e modo de mesclagem, barras de ações, papel e textura, camadas de filtro. |
| `navigator_plugin/` | o painel com a miniatura do documento, o retângulo da área visível e controles de zoom, rotação e espelhamento. |
| `recording_plugin/` | grava quadros do canvas durante a pintura e exporta o timelapse em MP4 (FFmpeg) ou ZIP; painel na doca direita e barra flutuante de controle. |
| `telemetry_plugin/` | o painel de desempenho do motor em tempo real (latência por etapa do pipeline, FPS, memória), desligável sem custo. |

## Regras

- Lei nº 1: plugin não importa plugin irmão. Comunicação por `ui/core` (estado, serviços) ou pelo `WorkspaceService`.
