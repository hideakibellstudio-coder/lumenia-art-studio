#ifndef ALADYN_ENGINE_PROCEDURAL_TEXTURES_HPP
#define ALADYN_ENGINE_PROCEDURAL_TEXTURES_HPP

#include "Texture2D.hpp"
#include <memory>

namespace aladyn::engine::texture {

enum class ShapePreset {
    SoftCircle = 0,
    HardCircle = 1,
    DryBristles = 2,
    Square = 3
};

enum class HeightPreset {
    FinePaper = 0,
    WatercolorPaper = 1,
    CanvasOil = 2,
    NoiseGrain = 3
};

class ProceduralTextures {
public:
    static std::shared_ptr<Texture2D> createShapePreset(ShapePreset preset, int size = 256);
    static std::shared_ptr<Texture2D> createHeightPreset(HeightPreset preset, int width = 512, int height = 512);

    static std::shared_ptr<Texture2D> createRadialShapeMask(int size = 256);
    static std::shared_ptr<Texture2D> createPaperGrain(int width = 512, int height = 512);
};

} // namespace aladyn::engine::texture

#endif // ALADYN_ENGINE_PROCEDURAL_TEXTURES_HPP
