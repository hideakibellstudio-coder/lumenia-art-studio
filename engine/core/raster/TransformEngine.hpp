#ifndef ALADYN_ENGINE_TRANSFORM_ENGINE_HPP
#define ALADYN_ENGINE_TRANSFORM_ENGINE_HPP

#include "../../utils/ColorRGBA.hpp"
#include "../selection/SelectionMask.hpp"
#include "../canvas/PixelBuffer.hpp"
#include "../canvas/TileGrid.hpp"
#include "../history/TileUndoManager.hpp"
#include "../document/Layer.hpp"
#include "../../utils/Rect2D.hpp"
#include <array>
#include <vector>
#include <memory>
#include <cmath>
#include <algorithm>

namespace aladyn::engine::raster {

enum class InterpolationMode : int {
    Nearest = 0,
    Bilinear = 1,
    Bicubic = 2
};

struct TransformState {
    bool active{false};
    bool isFromSelection{false};
    utils::Rect2D sourceBounds{0, 0, 0, 0};
    double pivotX{0.0};
    double pivotY{0.0};
    double currentDx{0.0};
    double currentDy{0.0};
    double currentScaleX{1.0};
    double currentScaleY{1.0};
    double currentRotationDeg{0.0};
    bool flipH{false};
    bool flipV{false};
    int interpolationMode{static_cast<int>(InterpolationMode::Bicubic)};
};

class TransformEngine {
public:
    TransformEngine() = default;

    /// Inicia o processo de transformação extraindo os pixels da camada ativa ou da seleção
    bool beginTransform(
        document::Layer* activeLayer,
        const selection::SelectionMask* selectionMask,
        int canvasWidth,
        int canvasHeight,
        history::TileUndoManager& undoManager,
        int activeLayerIndex
    );

    [[nodiscard]] bool isActive() const noexcept { return m_state.active; }
    [[nodiscard]] const TransformState& getState() const noexcept { return m_state; }
    [[nodiscard]] const canvas::PixelBuffer* getSourceBuffer() const noexcept { return m_sourceBuffer.get(); }
    [[nodiscard]] utils::Rect2D getSourceBounds() const noexcept { return m_state.sourceBounds; }

    /// Calcula o Bounding Box transformado resultante
    [[nodiscard]] utils::Rect2D calculateDestBounds(
        double dx, double dy,
        double scaleX, double scaleY,
        double rotationDeg,
        double pivotX, double pivotY,
        bool flipH, bool flipV
    ) const noexcept;

    /// Aplica definitivamente a transformação na camada ativa gravando nos tiles e no UndoManager
    bool commitTransform(
        document::Layer* activeLayer,
        double dx, double dy,
        double scaleX, double scaleY,
        double rotationDeg,
        double pivotX, double pivotY,
        bool flipH, bool flipV,
        int interpMode,
        int canvasWidth,
        int canvasHeight,
        history::TileUndoManager& undoManager,
        int activeLayerIndex,
        utils::Rect2D& outDirtyBounds
    );

    /// Distorcer: grava a fonte no quadrilátero `corners` (TL, TR, BR, BL em
    /// coordenadas da tela). false sem mexer em nada se o quad não for convexo
    /// -- o chamador decide se cancela. Implementado em TransformEngineDistort.cpp.
    bool commitTransformDistort(
        document::Layer* activeLayer,
        const std::array<double, 8>& corners,
        int interpMode,
        int canvasWidth,
        int canvasHeight,
        history::TileUndoManager& undoManager,
        int activeLayerIndex,
        utils::Rect2D& outDirtyBounds
    );

    /// Cancela a transformação restaurando os pixels originais
    bool cancelTransform(
        document::Layer* activeLayer,
        utils::Rect2D& outDirtyBounds
    );

    /// Operações diretas de 1 clique
    bool flipLayer(
        document::Layer* activeLayer,
        bool horizontal,
        int canvasWidth,
        int canvasHeight,
        history::TileUndoManager& undoManager,
        int activeLayerIndex,
        utils::Rect2D& outDirtyBounds
    );

    bool rotateLayer90(
        document::Layer* activeLayer,
        bool clockwise,
        int canvasWidth,
        int canvasHeight,
        history::TileUndoManager& undoManager,
        int activeLayerIndex,
        utils::Rect2D& outDirtyBounds
    );

    void reset() noexcept;

    // Métodos estáticos de interpolação
    static utils::ColorRGBA sampleNearest(const canvas::PixelBuffer& src, double u, double v) noexcept;
    static utils::ColorRGBA sampleBilinear(const canvas::PixelBuffer& src, double u, double v) noexcept;
    static utils::ColorRGBA sampleBicubic(const canvas::PixelBuffer& src, double u, double v) noexcept;

private:
    TransformState m_state;
    std::unique_ptr<canvas::PixelBuffer> m_sourceBuffer;
    std::vector<uint8_t> m_originalSelectionMask;
};

} // namespace aladyn::engine::raster

#endif // ALADYN_ENGINE_TRANSFORM_ENGINE_HPP
