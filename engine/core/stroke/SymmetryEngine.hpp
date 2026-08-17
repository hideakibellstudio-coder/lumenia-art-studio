#ifndef ALADYN_ENGINE_SYMMETRY_ENGINE_HPP
#define ALADYN_ENGINE_SYMMETRY_ENGINE_HPP

#include "PointerEvent.hpp"
#include <vector>
#include <cmath>

namespace aladyn::engine::stroke {

enum class SymmetryMode {
    None         = 0,
    Vertical     = 1, // Espelho Y em x = cx
    Horizontal   = 2, // Espelho X em y = cy
    Dual         = 3, // Espelho Quádruplo (X + Y)
    Radial       = 4, // Rotação Radial de N setores
    Kaleidoscope = 5  // Caleidoscópio (Setores alternados invertidos)
};

struct SymmetryConfig {
    SymmetryMode mode{SymmetryMode::None};
    double centerX{400.0};
    double centerY{300.0};
    int sectors{4};
};

class SymmetryEngine {
public:
    static std::vector<PointerEvent> processEvent(
        const PointerEvent& event,
        const SymmetryConfig& config
    ) {
        if (config.mode == SymmetryMode::None) {
            return { event };
        }

        std::vector<PointerEvent> events;
        events.push_back(event);

        const double cx = config.centerX;
        const double cy = config.centerY;
        const double px = event.position.x;
        const double py = event.position.y;

        switch (config.mode) {
            case SymmetryMode::Vertical: {
                PointerEvent e = event;
                e.position.x = 2.0 * cx - px;
                events.push_back(e);
                break;
            }
            case SymmetryMode::Horizontal: {
                PointerEvent e = event;
                e.position.y = 2.0 * cy - py;
                events.push_back(e);
                break;
            }
            case SymmetryMode::Dual: {
                PointerEvent eV = event;
                eV.position.x = 2.0 * cx - px;
                events.push_back(eV);

                PointerEvent eH = event;
                eH.position.y = 2.0 * cy - py;
                events.push_back(eH);

                PointerEvent eHV = event;
                eHV.position.x = 2.0 * cx - px;
                eHV.position.y = 2.0 * cy - py;
                events.push_back(eHV);
                break;
            }
            case SymmetryMode::Radial: {
                int N = std::max(2, config.sectors);
                double dx = px - cx;
                double dy = py - cy;
                double r = std::sqrt(dx * dx + dy * dy);
                double theta = std::atan2(dy, dx);

                for (int k = 1; k < N; ++k) {
                    double thetaK = theta + (2.0 * 3.14159265358979323846 * k) / N;
                    PointerEvent e = event;
                    e.position.x = cx + r * std::cos(thetaK);
                    e.position.y = cy + r * std::sin(thetaK);
                    events.push_back(e);
                }
                break;
            }
            case SymmetryMode::Kaleidoscope: {
                int N = std::max(2, config.sectors);
                double dx = px - cx;
                double dy = py - cy;
                double r = std::sqrt(dx * dx + dy * dy);
                double theta = std::atan2(dy, dx);

                for (int k = 1; k < N; ++k) {
                    double angleShift = (2.0 * 3.14159265358979323846 * k) / N;
                    double thetaK = (k % 2 == 0) ? (theta + angleShift) : (-theta + angleShift);
                    PointerEvent e = event;
                    e.position.x = cx + r * std::cos(thetaK);
                    e.position.y = cy + r * std::sin(thetaK);
                    events.push_back(e);
                }
                break;
            }
            default:
                break;
        }

        return events;
    }
};

} // namespace aladyn::engine::stroke

#endif // ALADYN_ENGINE_SYMMETRY_ENGINE_HPP
