#ifndef ALADYN_ENGINE_CURVILINEAR_SNAP_ENGINE_HPP
#define ALADYN_ENGINE_CURVILINEAR_SNAP_ENGINE_HPP

#include "../../utils/Point2D.hpp"
#include "GuideSnapEngine.hpp"
#include <vector>

namespace aladyn::engine::math {

// Curva analítica candidata para snap curvilíneo (linha ou círculo), resultado
// da projeção estereográfica de um plano-normal 3D. Espelha os dicts
// {"type": "line"/"circle", "family": ..., ...} de geometry_snapping_engine.py
// e camera_3d_projector.py. Apenas Line/Circle existem na prática — o caso
// "polyline" do lado Python nunca é produzido pelos geradores de curva usados
// no snap (create_curve_from_normal só emite line ou circle), então não tem
// equivalente aqui.
enum class CurveFamily { GroundV = 0, GroundX = 1, GroundZ = 2 };
enum class CurveKind { Line = 0, Circle = 1 };

struct CurvilinearCurve {
    CurveKind   kind{CurveKind::Line};
    CurveFamily family{CurveFamily::GroundV};
    // Line:
    utils::Point2D p1{0.0, 0.0};
    utils::Point2D p2{0.0, 0.0};
    utils::Point2D dir{1.0, 0.0};
    // Circle:
    utils::Point2D center{0.0, 0.0};
    double  radius{0.0};
};

// Snap para guias curvilíneas (6P fisheye) — Fase C2b. Separado de
// GuideSnapEngine (que cobre Straight/Bezier/Isometric/1P/2P/3P) para manter
// cada arquivo nativo abaixo do teto de LOC da Zona Vermelha ARCcC (450).
// Porta fiel de camera_3d_projector.py + geometry_snapping_engine.py.
//
// API sem estado: o motor não guarda curva travada nem ponto de início de
// traço — quem chama (GeometryToolController) continua dono do ciclo de vida
// da interação, exatamente como já faz hoje em Python. O motor só executa a
// matemática, recebendo o estado necessário a cada chamada e devolvendo o que
// deve ser persistido pelo chamador — mesmo padrão já usado em
// GuideSnapEngine::snapPoint(rawPoint, lastPoint).
class CurvilinearSnapEngine {
public:
    // Candidatas curvilíneas (V/H/D) passando por clickPt — espelha
    // get_dynamic_curves_at_point(). Puro: o chamador decide quando invocar
    // (tipicamente uma vez, no início do traço) e congela o resultado.
    static std::vector<CurvilinearCurve> candidates(
        const GuideConfig& config,
        const utils::Point2D& clickPt
    ) noexcept;

    // Curva primária (meridiano/paralelo) da grade completa mais próxima de
    // pt, dentro de maxDist — espelha find_nearest_primary_grid_curve().
    // Retorna false se nenhuma curva estiver dentro de maxDist.
    static bool nearestPrimaryGridCurve(
        const GuideConfig& config,
        const utils::Point2D& pt,
        double maxDist,
        CurvilinearCurve& out
    ) noexcept;

    static utils::Point2D closestPointOnCurve(const CurvilinearCurve& curve, const utils::Point2D& pt) noexcept;

    // Snap curvilíneo sem estado — espelha snap_curvilinear(). candidates é a
    // lista já congelada pelo chamador; lockedIndex é o índice da curva
    // travada na chamada anterior (-1 = nenhuma). outLockedIndex recebe o que
    // deve ser persistido para a próxima chamada (-1 = destravar).
    static utils::Point2D snap(
        const GuideConfig& config,
        const utils::Point2D& rawPoint,
        const utils::Point2D& strokeStart,
        const std::vector<CurvilinearCurve>& candidates,
        int lockedIndex,
        bool isStroking,
        double zoom,
        int& outLockedIndex
    ) noexcept;

private:
    // Primitivas 3D puras — espelham rotate_3d_forward/backward de camera_3d_projector.py.
    static void rotate3DForward(double x, double y, double z, double yawRad, double pitchRad, double& outX, double& outY, double& outZ) noexcept;
    static void rotate3DBackward(double x, double y, double z, double yawRad, double pitchRad, double& outX, double& outY, double& outZ) noexcept;
    static double curvilinearCameraRadius(double fov, double baseRadius) noexcept;
    static bool curveFromNormal(double a, double b, double c, double R, double cx, double cy, CurveFamily family, CurvilinearCurve& out) noexcept;
};

} // namespace aladyn::engine::math

#endif // ALADYN_ENGINE_CURVILINEAR_SNAP_ENGINE_HPP
