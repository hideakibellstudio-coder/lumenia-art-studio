#ifndef ALADYN_ENGINE_LAYER_BLEND_MODE_HPP
#define ALADYN_ENGINE_LAYER_BLEND_MODE_HPP

// Modos de mesclagem de camada. Espelhado 1:1 em Python por
// ui/core/document/layer_blend_mode.py; o documento reexporta como
// document::LayerBlendMode (LayerNode.hpp).

namespace aladyn::engine::document::blending {

enum class LayerBlendMode {
    Normal      = 0,  // Alpha Over tradicional
    Multiply    = 1,  // Multiplicação de cores
    Screen      = 2,  // Divisão / Claridade
    Overlay     = 3,  // Sobreposição de contraste
    Darken      = 4,  // Escurecer
    Lighten     = 5,  // Clarear
    Erase       = 6,  // Borracha de camada (Alpha Erase)
    PassThrough = 7,  // Atravessar (Modo padrão para Grupos)
    ColorDodge  = 8,  // Subexposição de cor / Brilho Neon
    ColorBurn   = 9,  // Superexposição de cor / Contraste denso
    Difference  = 10, // Diferença / Inversão cromática
    Exclusion   = 11, // Exclusão
    Add         = 12, // Adicionar / Luz Pura
    SoftLight   = 13, // Luz Suave
    HardLight   = 14, // Luz Direta
    VividLight  = 15, // Luz Brilhante
    LinearLight = 16, // Luz Linear
    PinLight    = 17, // Luz Pontual
    HardMix     = 18, // Mistura Sólida
    Subtract    = 19  // Subtrair
};

} // namespace aladyn::engine::document::blending

#endif // ALADYN_ENGINE_LAYER_BLEND_MODE_HPP
