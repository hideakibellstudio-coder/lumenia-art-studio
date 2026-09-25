#include "SnapCandidate.hpp"
#include <cmath>

namespace aladyn::engine::math {

utils::Point2D SnapCandidateMath::closestPoint(const SnapCandidate& candidate, const utils::Point2D& pt) noexcept {
    if (candidate.kind == CandidateKind::Line) {
        // dir já é unitário por contrato de quem monta a candidata — projeção
        // sem precisar dividir por |dir|^2 (mesma simplificação já usada em
        // CurvilinearSnapEngine::closestPointOnCurve para o caso de reta
        // definida por ponto+direção).
        const double dx = pt.x - candidate.p1.x;
        const double dy = pt.y - candidate.p1.y;
        const double t = dx * candidate.dir.x + dy * candidate.dir.y;
        return utils::Point2D{ candidate.p1.x + t * candidate.dir.x, candidate.p1.y + t * candidate.dir.y };
    }

    const double dx = pt.x - candidate.center.x;
    const double dy = pt.y - candidate.center.y;
    const double dist = std::sqrt(dx * dx + dy * dy);
    if (dist > 1e-9) {
        return utils::Point2D{ candidate.center.x + (dx / dist) * candidate.radius, candidate.center.y + (dy / dist) * candidate.radius };
    }
    return utils::Point2D{ candidate.center.x + candidate.radius, candidate.center.y };
}

utils::Point2D SnapCandidateMath::tangentAt(const SnapCandidate& candidate, const utils::Point2D& pt) noexcept {
    if (candidate.kind == CandidateKind::Line) {
        return candidate.dir;
    }

    const utils::Point2D closest = closestPoint(candidate, pt);
    const double rx = closest.x - candidate.center.x;
    const double ry = closest.y - candidate.center.y;
    const double rlen = std::sqrt(rx * rx + ry * ry);
    if (rlen < 1e-9) {
        return utils::Point2D{ 1.0, 0.0 };
    }
    // Perpendicular ao raio (90 graus anti-horário) — mesma convenção já
    // usada no loop de pontuação de CurvilinearSnapEngine::snap().
    return utils::Point2D{ -ry / rlen, rx / rlen };
}

} // namespace aladyn::engine::math
