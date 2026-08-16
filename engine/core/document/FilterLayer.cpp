#include "FilterLayer.hpp"

namespace aladyn::engine::document {

FilterLayer::FilterLayer(const std::string& name, FilterType type, int width, int height)
    : Layer(name, LayerNodeType::FilterLayer, width, height), m_filterType(type), m_params(8, 0.0f) {
    
    // Define valores padrão de inicialização baseados no tipo do filtro
    switch (type) {
        case FilterType::HueSat:
            m_params[0] = 0.0f;  // Hue shift (-180 a +180)
            m_params[1] = 0.0f;  // Saturation (-100 a +100)
            m_params[2] = 0.0f;  // Lightness (-100 a +100)
            m_params[3] = 0.0f;  // Colorize flag (0 ou 1)
            break;
        case FilterType::BrightnessContrast:
            m_params[0] = 0.0f;  // Brightness (-100 a +100)
            m_params[1] = 0.0f;  // Contrast (-100 a +100)
            m_params[2] = 1.0f;  // Gamma (0.1 a 5.0)
            break;
        case FilterType::GaussianBlur:
            m_params[0] = 5.0f;  // Radius (0 a 100)
            m_params[1] = 0.0f;  // Angle (0 a 360)
            break;
        case FilterType::ColorBalance:
            m_params[0] = 0.0f;  // Red shift (-100 a +100)
            m_params[1] = 0.0f;  // Green shift (-100 a +100)
            m_params[2] = 0.0f;  // Blue shift (-100 a +100)
            break;
        case FilterType::SharpenVignette:
            m_params[0] = 0.0f;  // Sharpen (0 a 100)
            m_params[1] = 0.0f;  // Vignette intensity (0 a 100)
            break;
        case FilterType::InvertThreshold:
            m_params[0] = 1.0f;  // Invert flag (0 ou 1)
            m_params[1] = 128.0f;// Threshold (0 a 255)
            break;
        case FilterType::Pixelate:
            m_params[0] = 8.0f;  // Block Size (2 a 64 px)
            break;
    }
}

} // namespace aladyn::engine::document
