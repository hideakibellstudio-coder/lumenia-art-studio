#include "TrajectoryEstimator.hpp"
#include "MathUtils.hpp"
#include <cmath>

namespace aladyn::engine::math {

namespace {
    // Peso do segmento i (do mais antigo pro mais recente) decai por este
    // fator a cada passo para trás -- segmentos recentes pesam mais, mas
    // nenhum segmento isolado pode dominar só por ser fisicamente maior
    // (diferença chave em relação ao "chord" antigo).
    constexpr double RECENCY_DECAY = 0.6;
    constexpr double MIN_SEGMENT_LENGTH = 1e-6;
}

TrajectoryEstimate TrajectoryEstimator::estimate(const std::vector<Point2D>& recentPoints, double zoom) noexcept {
    TrajectoryEstimate result;

    const size_t n = recentPoints.size();
    if (n < 2) {
        return result; // confidence 0, direcao default -- pontos insuficientes
    }

    double sumWx = 0.0, sumWy = 0.0, sumW = 0.0;
    size_t validSegments = 0;
    Point2D lastValidDir{ 1.0, 0.0 };

    const size_t numSegments = n - 1;
    double weight = 1.0;
    // Percorre do segmento mais recente para o mais antigo para atribuir o
    // peso de forma incremental (soma final independe da ordem).
    for (size_t k = 0; k < numSegments; ++k) {
        const size_t i = numSegments - 1 - k;
        const Point2D& a = recentPoints[i];
        const Point2D& b = recentPoints[i + 1];
        const double dx = b.x - a.x;
        const double dy = b.y - a.y;
        const double len = std::sqrt(dx * dx + dy * dy);
        if (len < MIN_SEGMENT_LENGTH) {
            weight *= RECENCY_DECAY;
            continue; // segmento degenerado (evento duplicado/parado) -- nao entra na media
        }
        const double ux = dx / len, uy = dy / len;
        sumWx += weight * ux;
        sumWy += weight * uy;
        sumW += weight;
        lastValidDir = Point2D{ ux, uy };
        ++validSegments;
        weight *= RECENCY_DECAY;
    }

    if (validSegments == 0 || sumW <= 0.0) {
        return result; // todos os segmentos degenerados -- sem informacao de direcao
    }

    const double avgX = sumWx / sumW;
    const double avgY = sumWy / sumW;
    // Magnitude da media de direcoes unitarias = coerencia (1.0 = todos os
    // segmentos concordam; perto de 0 = se cancelam, ex. zigue-zague/ruido).
    const double coherence = std::sqrt(avgX * avgX + avgY * avgY);

    Point2D direction;
    if (coherence > 1e-6) {
        direction = Point2D{ avgX / coherence, avgY / coherence };
    } else {
        // Sem direcao dominante -- usa o ultimo segmento valido como
        // palpite, mas a confianca (abaixo) ja fica perto de zero por causa
        // da coerencia baixa, entao quem consome isto sabe que nao deve
        // confiar nesse palpite.
        direction = lastValidDir;
    }

    // Confianca de movimento: desloc. liquido (primeiro->ultimo ponto da
    // janela) precisa superar um piso minimo -- mesmo papel historico de
    // lock_thresh (~3.9px com sensibilidade padrao) -- mas como rampa
    // continua em vez de corte rigido de um unico frame.
    const double netDx = recentPoints[n - 1].x - recentPoints[0].x;
    const double netDy = recentPoints[n - 1].y - recentPoints[0].y;
    const double netDist = std::sqrt(netDx * netDx + netDy * netDy);
    const double moveFloor = 3.9 / std::max(0.01, zoom);
    const double moveConfidence = MathUtils::smoothstep(moveFloor, moveFloor * 2.0, netDist);

    result.direction = direction;
    result.confidence = moveConfidence * coherence;
    return result;
}

} // namespace aladyn::engine::math
