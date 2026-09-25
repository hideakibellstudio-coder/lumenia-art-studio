#ifndef ALADYN_ENGINE_FILTER_SETTINGS_HPP
#define ALADYN_ENGINE_FILTER_SETTINGS_HPP

// Contrato de entrada dos filtros: tipo, parâmetros e opacidade efetiva da
// camada de ajuste. Os filtros não conhecem FilterLayer (a pasta-mãe); é a
// camada que monta estas configurações (FilterLayer::settings).

#include <cstddef>
#include <vector>

namespace aladyn::engine::document::filters {

enum class FilterType {
    HueSat = 0,             // Matiz / Saturação / Luminosidade (HSV)
    BrightnessContrast = 1, // Brilho / Contraste / Gama
    GaussianBlur = 2,       // Desfoque Gaussiano / Movimento
    ColorBalance = 3,       // Balanço de Cores / Níveis RGB
    SharpenVignette = 4,    // Nitidez & Vinheta
    InvertThreshold = 5,    // Inversão & Limiar
    Pixelate = 6            // Pixelizar (Mosaico procedural)
};

struct FilterSettings {
    FilterType type{FilterType::HueSat};
    const std::vector<float>* params{nullptr};  // vive na camada durante a chamada
    double opacity{1.0};

    [[nodiscard]] float getParam(size_t index, float defaultVal = 0.0f) const noexcept {
        return (params && index < params->size()) ? (*params)[index] : defaultVal;
    }
};

} // namespace aladyn::engine::document::filters

#endif // ALADYN_ENGINE_FILTER_SETTINGS_HPP
