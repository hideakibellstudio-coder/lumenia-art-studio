#pragma once

#include "../../core/document/LayerStack.hpp"
#include "../../core/document/Compositor.hpp"
#include "../../core/canvas/PixelBuffer.hpp"
#include "../../core/canvas/MipmapPyramid.hpp"
#include "../../utils/Rect2D.hpp"
#include <cstdint>

namespace aladyn::engine::boundary::orchestrator {

// Contrato unico de "o que uma operacao de documento precisa tocar".
//
// Motivacao (Achado #6 do panorama de auditoria profunda de camadas,
// claude/panorama-motor-camadas-auditoria-profunda-2026-09-19.md): antes deste
// agregado, toda chamada do PaintEngineFacade a um orquestrador repetia a mesma
// tupla de quatro argumentos (m_layerStack, m_compositor, m_outputBuffer,
// m_canvasTexture.backgroundColor) e depois repetia touchDocument() na linha
// seguinte. Isso era ~140 linhas de plumbing no facade e, pior, deixava a
// invalidacao de geracao/mipmap como responsabilidade do chamador -- qualquer
// metodo novo que esquecesse touchDocument() ficava silenciosamente com cache
// de display obsoleto.
//
// Aqui a tupla vira um tipo e o "documento mudou" vira um metodo. O facade
// passa a ser uma camada de traducao de uma linha por operacao, e a
// invalidacao acompanha a mutacao em vez de depender de disciplina.
//
// Referencias, nao copias: o contexto e construido sob demanda a cada chamada
// (PaintEngineFacade::docContext()) e nunca armazenado, entao nao ha risco de
// referencia pendente apos resizeCanvas() ou syncHistoryGeometry() trocarem os
// buffers/compositor por instancias novas.
struct DocumentContext {
    document::LayerStack&    layerStack;
    document::Compositor&    compositor;
    canvas::PixelBuffer&     outputBuffer;
    const utils::ColorRGBA& bgColor;
    uint64_t&                documentGeneration;
    canvas::MipmapPyramid&   mipmapPyramid;
    bool                     linearGamma{true};
    bool                     deepColor{false};

    // Equivalente exato de PaintEngineFacade::touchDocument().
    void touch() const noexcept {
        ++documentGeneration;
        mipmapPyramid.markDirty();
    }

    void compositeAll() const {
        compositor.composite(layerStack.getAllLayersForComposition(), outputBuffer, bgColor);
    }

    void compositeRegion(const utils::Rect2D& dirty) const {
        compositor.compositeRegion(layerStack.getAllLayersForComposition(), dirty, outputBuffer, bgColor);
    }
};

} // namespace aladyn::engine::boundary::orchestrator
