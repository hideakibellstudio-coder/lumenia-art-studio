#pragma once

#include "../../../core/brush/BrushProfile.hpp"
#include "../../../core/engines/IBrushEngine.hpp"
#include "../../../core/engines/PencilEngine.hpp"
#include "../../../core/engines/InkerEngine.hpp"
#include "../../../core/engines/EraserEngine.hpp"
#include "../../../core/engines/MarkerEngine.hpp"
#include "../../../core/engines/BlurEngine.hpp"
#include "../../../core/engines/SmudgeEngine.hpp"
#include "../../../core/engines/WatercolorEngine.hpp"
#include "../../../core/engines/OilImpastoEngine.hpp"
#include <memory>

namespace aladyn::engine::boundary::internal {

// Unico lugar que conhece a lista concreta de motores de pincel.
//
// Extraido de PaintEngineFacade::initEngine (Achado #6). Alem de tirar ~35
// linhas do facade, tira de la os oito includes de motores concretos: o facade
// volta a depender so da interface IBrushEngine, e adicionar um motor novo
// passa a tocar um arquivo, nao dois.
class BrushEngineFactory {
public:
    static std::unique_ptr<engines::IBrushEngine> create(brush::EngineType type) {
        switch (type) {
            case brush::EngineType::Pencil:     return std::make_unique<engines::PencilEngine>();
            case brush::EngineType::Inker:      return std::make_unique<engines::InkerEngine>();
            case brush::EngineType::Eraser:     return std::make_unique<engines::EraserEngine>();
            case brush::EngineType::Marker:     return std::make_unique<engines::MarkerEngine>();
            case brush::EngineType::Blur:       return std::make_unique<engines::BlurEngine>();
            case brush::EngineType::Smudge:     return std::make_unique<engines::SmudgeEngine>();
            case brush::EngineType::Watercolor: return std::make_unique<engines::WatercolorEngine>();
            case brush::EngineType::OilImpasto: return std::make_unique<engines::OilImpastoEngine>();
            default:                            return nullptr;
        }
    }
};

} // namespace aladyn::engine::boundary::internal
