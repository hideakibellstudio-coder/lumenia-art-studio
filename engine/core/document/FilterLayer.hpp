#ifndef ALADYN_ENGINE_FILTER_LAYER_HPP
#define ALADYN_ENGINE_FILTER_LAYER_HPP

#include "Layer.hpp"
#include <vector>
#include <string>

namespace aladyn::engine::document {

enum class FilterType {
    HueSat = 0,             // Matiz / Saturação / Luminosidade (HSV)
    BrightnessContrast = 1, // Brilho / Contraste / Gama
    GaussianBlur = 2,       // Desfoque Gaussiano / Movimento
    ColorBalance = 3,       // Balanço de Cores / Níveis RGB
    SharpenVignette = 4,    // Nitidez & Vinheta
    InvertThreshold = 5,    // Inversão & Limiar
    Pixelate = 6            // Pixelizar (Mosaico procedural)
};

class FilterLayer : public Layer {
public:
    FilterLayer(const std::string& name, FilterType type, int width = 1, int height = 1);

    [[nodiscard]] FilterType getFilterType() const noexcept { return m_filterType; }
    void setFilterType(FilterType type) noexcept { m_filterType = type; }

    [[nodiscard]] const std::vector<float>& getParams() const noexcept { return m_params; }
    void setParams(const std::vector<float>& params) { m_params = params; }
    void setParam(size_t index, float val) {
        if (index >= m_params.size()) m_params.resize(index + 1, 0.0f);
        m_params[index] = val;
    }
    [[nodiscard]] float getParam(size_t index, float defaultVal = 0.0f) const noexcept {
        return (index < m_params.size()) ? m_params[index] : defaultVal;
    }

private:
    FilterType m_filterType;
    std::vector<float> m_params;
};

} // namespace aladyn::engine::document

#endif // ALADYN_ENGINE_FILTER_LAYER_HPP
