#ifndef ALADYN_ENGINE_SNAP_CANDIDATE_HPP
#define ALADYN_ENGINE_SNAP_CANDIDATE_HPP

#include "Point2D.hpp"

namespace aladyn::engine::math {

// Representação genérica de uma "trilha" candidata de snap — reta ou
// círculo — comum a qualquer tipo de guia (Curvilinear, Perspectiva,
// Straight, CurveRuler). Fase D0 (redesign do motor de snap, ver
// claude/proposta-redesign-motor-snap-guias.md no projeto): antes desta
// fase, cada tipo de guia tinha sua própria estrutura de candidata
// (CurvilinearCurve; Perspectiva nem reificava a reta candidata como valor,
// reconstruía tudo dentro do próprio snapPerspective()). Unificar num único
// tipo permite um único motor de pontuação/trava (SnapLockStateMachine) em
// vez de um por tipo de guia — a causa raiz da duplicação que o C3.0 já
// teve que corrigir em dois lugares (Python e nativo) por falta disso.
//
// `family` é opaco para este módulo: cada adaptador de guia decide o que
// significa (CurveFamily do Curvilinear, tipo de raio da Perspectiva etc.);
// serve só para filtros como snap_mode v/h/d, nunca é lido pela matemática
// de closestPoint/tangentAt abaixo.
enum class CandidateKind { Line = 0, Circle = 1 };

struct SnapCandidate {
    CandidateKind kind{CandidateKind::Line};
    int family{0};
    // Line: p1 é um ponto qualquer sobre a reta; dir é a direção unitária.
    Point2D p1{0.0, 0.0};
    Point2D dir{1.0, 0.0};
    // Circle:
    Point2D center{0.0, 0.0};
    double radius{0.0};
};

class SnapCandidateMath {
public:
    // Ponto de `candidate` mais próximo de `pt`.
    static Point2D closestPoint(const SnapCandidate& candidate, const Point2D& pt) noexcept;

    // Direção tangente unitária de `candidate` no ponto mais próximo de
    // `pt` — constante para Line; perpendicular ao raio (sentido arbitrário
    // mas consistente) para Circle.
    static Point2D tangentAt(const SnapCandidate& candidate, const Point2D& pt) noexcept;
};

} // namespace aladyn::engine::math

#endif // ALADYN_ENGINE_SNAP_CANDIDATE_HPP
