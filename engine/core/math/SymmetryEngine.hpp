#ifndef ALADYN_ENGINE_SYMMETRY_ENGINE_HPP
#define ALADYN_ENGINE_SYMMETRY_ENGINE_HPP

#include "../raster/Dab.hpp"
#include "Point2D.hpp"
#include <vector>

namespace aladyn::engine::math {

enum class SymmetryMode {
    None         = 0,
    Mirror       = 1,
    DoubleMirror = 2,
    Radial       = 3,
    Kaleidoscope = 4
};

struct SymmetryConfig {
    SymmetryMode mode{SymmetryMode::None};
    double cx{0.0};
    double cy{0.0};
    double angleRad{0.0};
    int segments{6};
    bool stopAtCenter{false};
};

class SymmetryEngine {
public:
    static void apply(
        const SymmetryConfig& config,
        const raster::Dab& dab,
        const Point2D* strokeStart,
        std::vector<raster::Dab>& outDabs
    );

    static Point2D mirrorPoint(double x, double y, double cx, double cy, double cosA, double sinA) noexcept;
};

} // namespace aladyn::engine::math

#endif // ALADYN_ENGINE_SYMMETRY_ENGINE_HPP
