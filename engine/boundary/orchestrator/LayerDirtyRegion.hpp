#pragma once

#include "../../core/document/LayerStack.hpp"
#include "../../utils/Rect2D.hpp"

namespace aladyn::engine::boundary::orchestrator {

// Extraido de LayerStackOrchestrator.hpp sem nenhuma alteracao de logica
// (Achado #6: aquele arquivo acumulava o calculo geometrico e a orquestracao
// de mutacao; sao dois assuntos). O corpo abaixo e identico ao que a auditoria
// de camadas validou, incluindo a correcao de camadas de filtro.
class LayerDirtyRegion {
public:
    // ─── Achado #1 do panorama de auditoria profunda de camadas
    // (claude/panorama-motor-camadas-auditoria-profunda-2026-09-19.md) ────────
    //
    // Calcula a região suja (em coordenadas de pixel) afetada por uma mudança
    // de propriedade puramente visual (opacidade/blend/visibilidade/clipping)
    // em UMA camada, para permitir compositeRegion() em vez de composite()
    // completo. Invariante de segurança: o resultado é sempre um
    // superconjunto seguro dos pixels que podem mudar -- nunca um
    // subconjunto. Isso vale porque a contribuição de uma camada ao
    // composite final (pintura própria, ou o efeito de servir de base de
    // clipping para outra camada) nunca ultrapassa a própria área pintada
    // dessa camada; fora dela a camada tem alpha zero e não contribui nada,
    // com qualquer opacidade/blend/visibilidade/clipping.
    //
    // Para uma camada de desenho comum: união dos tiles alocados e
    // não-vazios da própria TileGrid.
    // Para um grupo: união recursiva do conteúdo de todas as camadas
    // descendentes (grupos aninhados incluídos), já que um grupo não pinta
    // pixels na própria TileGrid -- todo o conteúdo visível vem dos filhos.
    //
    // Retorna um Rect2D vazio quando não há nenhum pixel pintado (camada ou
    // subárvore inteira vazia); compositeRegion() trata isso como no-op
    // seguro (ver Compositor::compositeRegion: "if (minX > maxX || minY >
    // maxY) return;").
    static utils::Rect2D computeLayerVisualDirtyRegion(const document::LayerStack& stack, int index) {
        const document::Layer* layer = stack.getDrawingLayer(index);
        if (!layer) {
            return utils::Rect2D{};
        }

        const utils::Rect2D fullCanvas{
            0.0, 0.0,
            static_cast<double>(stack.getWidth()),
            static_cast<double>(stack.getHeight())
        };

        // CORREÇÃO (regressão pega por tests/test_compositing_characterization.py::
        // test_filtro_com_opacidade_zero_nao_altera_nada): uma camada de filtro não
        // pinta pixels na própria TileGrid -- seu efeito é aplicado sobre o buffer
        // já composto por baixo dela (Compositor::applyFilterToBuffer /
        // FilterApplier::apply), então a extensão afetada não pode ser derivada dos
        // tiles da própria camada (estariam sempre vazios). Cai para o canvas
        // inteiro nesse caso -- é exatamente o comportamento original antes desta
        // otimização, então nenhuma regressão de correção é introduzida, só se
        // perde o ganho de performance para esse tipo específico de camada.
        if (layer->isFilter()) {
            return fullCanvas;
        }

        utils::Rect2D bounds{};
        bool any = false;
        bool sawFilterDescendant = false;
        auto accumulateFrom = [&](const document::Layer& l) {
            if (l.isFilter()) { sawFilterDescendant = true; return; }
            l.getTileGrid().forEachTile([&](const auto&, const canvas::Tile& tile) {
                if (tile.isEmpty()) return;
                bounds = any ? bounds.united(tile.getBounds()) : tile.getBounds();
                any = true;
            });
        };

        if (!layer->isGroup()) {
            accumulateFrom(*layer);
        } else {
            // Grupo: une o conteúdo de todos os descendentes. A própria
            // TileGrid de um grupo nunca recebe pinceladas diretamente.
            for (size_t i = 0; i < stack.getDrawingLayerCount(); ++i) {
                const document::Layer* candidate = stack.getDrawingLayer(static_cast<int>(i));
                if (!candidate || candidate == layer || candidate->isGroup()) continue;
                const document::LayerNode* p = candidate->getParent();
                bool isDescendant = false;
                while (p) {
                    if (p == layer) { isDescendant = true; break; }
                    p = p->getParent();
                }
                if (isDescendant) accumulateFrom(*candidate);
            }
        }

        // Mesma lógica: se qualquer descendente do grupo for uma camada de
        // filtro, a extensão afetada real não é limitada aos tiles pintados
        // pelos irmãos -- cai para o canvas inteiro por segurança.
        if (sawFilterDescendant) {
            return fullCanvas;
        }

        return any ? bounds : utils::Rect2D{};
    }
};

} // namespace aladyn::engine::boundary::orchestrator
