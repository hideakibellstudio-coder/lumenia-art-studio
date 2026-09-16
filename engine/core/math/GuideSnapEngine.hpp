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

    // ── Curvilinear (6P fisheye) — Fase C2b ──────────────────────────────
    // Espelham os campos equivalentes de guide_state em geometry_tool_controller.py.
    // Antes desta fase, o motor recebia cx/cy/fov/pitch/yaw mas nunca os usava
    // (GuideType::Curvilinear caía em no-op); os campos abaixo completam o
    // que faltava para gerar e pontuar as curvas candidatas nativamente.
    double baseRadius{400.0};
    double density{30.0};
    bool showV{true};
    bool showH{true};
    bool showD{true};
    bool showGround{false};
    bool showCeiling{false};
    bool showGroundVerticals{false};
    bool showCeilingVerticals{false};
    bool showStraightVerticals{false};
    int  snapMode{0};           // 0=auto, 1=v, 2=h, 3=d — espelha snap_mode do Python
    double snapSensitivity{3.0};
};

class GuideSnapEngine {
public:
    // Straight / CurveRuler: gating puro por snapRadius, sem estado de
    // travamento. OnePoint/TwoPoint/ThreePoint/Isometric/Curvilinear
    // retornam rawPoint inalterado aqui -- ver snapPerspective() e
    // CurvilinearSnapEngine::snap() para esses tipos (Fase C3.1 / C2b).
    static Point2D snapPoint(
        const GuideConfig& config,
        const Point2D& rawPoint,
        const Point2D* lastPoint = nullptr
    ) noexcept;

    // -- Perspectiva (1P/2P/3P/Isometric) -- Fase C3.1 --------------------
    // Porte fiel de snap_ray_perspective (geometry_snapping_engine.py), o
    // algoritmo que a UI realmente usa hoje. Substitui a antiga implementacao
    // nativa desses 4 tipos dentro de snapPoint() (codigo morto ate a Fase
    // C3, nunca chamado pela UI, com um algoritmo estruturalmente diferente
    // -- reprojecao a partir de lastPoint a cada chamada, em vez de travar
    // uma direcao no inicio do traco). Mesmo contrato sem-estado ja usado no
    // Curvilinear: quem chama informa a direcao travada (se houver, via
    // lockedDir) e recebe de volta o que persistir para a proxima chamada
    // (outLockedDir/outHasLockedDir).
    static Point2D snapPerspective(
        const GuideConfig& config,
        const Point2D& rawPoint,
        const Point2D& strokeStart,
        const Point2D* lockedDir,
        double zoom,
        Point2D& outLockedDir,
        bool& outHasLockedDir
    ) noexcept;

private:
    static Point2D projectToLine(const Point2D& p0, const Point2D& p1, const Point2D& q) noexcept;
    static Point2D projectToBezier(const Point2D& p0, const Point2D& p1, const Point2D& p2, const Point2D& p3, const Point2D& q) noexcept;
};

} // namespace aladyn::engine::math

#endif // ALADYN_ENGINE_GUIDE_SNAP_ENGINE_HPP
