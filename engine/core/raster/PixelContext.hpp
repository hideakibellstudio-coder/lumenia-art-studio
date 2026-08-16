#ifndef ALADYN_ENGINE_PIXEL_CONTEXT_HPP
#define ALADYN_ENGINE_PIXEL_CONTEXT_HPP

namespace aladyn::engine::document {
class Layer;
}

namespace aladyn::engine::raster {

// ─── ESTRUTURA UNIFICADA DE CONTEXTO DE PINTURA E MÁSCARAS DE PIXEL ─────────
//
// Encapsula todas as restrições e regras de deposição que operam a nível de
// pixel durante o desenho de um carimbo (dab).
// Permite expandir novos recursos (Seleção, Stencil, Quick Mask) sem alterar
// as assinaturas virtuais dos mini-motores de pincel.
// ───────────────────────────────────────────────────────────────────────────
struct PixelContext {
    bool alphaLocked{false};
    const document::Layer* clipBaseLayer{nullptr};

    // Campos de expansão futura (reservados para Seleções e Stencils 2D)
    const void* selectionMask{nullptr};
    const void* stencilMask{nullptr};
};

} // namespace aladyn::engine::raster

#endif // ALADYN_ENGINE_PIXEL_CONTEXT_HPP
