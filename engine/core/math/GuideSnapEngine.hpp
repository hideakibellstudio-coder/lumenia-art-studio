#ifndef ALADYN_ENGINE_GUIDE_SNAP_ENGINE_HPP
#define ALADYN_ENGINE_GUIDE_SNAP_ENGINE_HPP

#include "Point2D.hpp"
#include <vector>

namespace aladyn::engine::math {

enum class GuideType {
    None        = 0,
    Straight    = 1,
    CurveRuler  = 2,
    Curvilinear = 3,
    OnePoint    = 4,
    TwoPoint    = 5,
    ThreePoint  = 6,
    Isometric   = 7
};

struct GuideConfig {
    GuideType type{GuideType::None};
    Point2D p0{0.0, 0.0};
    Point2D p1{100.0, 100.0};
    Point2D p2{200.0, 200.0};
    Point2D p3{300.0, 300.0};
    Point2D vpA{400.0, 300.0};
    Point2D vpB{-1000.0, 300.0};
    Point2D vpC{400.0, -2000.0};
    double cx{0.0};
    double cy{0.0};
    double fov{130.0};
    double pitch{0.0};
    double yaw{0.0};
    double snapRadius{32.0};
};

class GuideSnapEngine {
public:
    static Point2D snapPoint(
        const GuideConfig& config,
        const Point2D& rawPoint,
        const Point2D* lastPoint = nullptr
    ) noexcept;

private:
    static Point2D projectToLine(const Point2D& p0, const Point2D& p1, const Point2D& q) noexcept;
    static Point2D projectToBezier(const Point2D& p0, const Point2D& p1, const Point2D& p2, const Point2D& p3, const Point2D& q) noexcept;
};

} // namespace aladyn::engine::math

#endif // ALADYN_ENGINE_GUIDE_SNAP_ENGINE_HPP
