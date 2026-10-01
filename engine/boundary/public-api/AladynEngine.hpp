#ifndef ALADYN_ENGINE_PUBLIC_API_HPP
#define ALADYN_ENGINE_PUBLIC_API_HPP

// Porta de entrada única do motor: a ponte (bridge/core/bindings) inclui só
// este arquivo. Ele reúne a fachada, as prévias do pincel e os tipos de valor
// que a ponte expõe ao Python; tipo novo exposto entra nesta lista (é contrato).

#include "PaintEngineFacade.hpp"   // fachada; traz BrushProfile, CanvasTexture, enums de camada, seleção e guias
#include "BrushPreviews.hpp"
#include "DecodedLayer.hpp"        // pixels de uma camada decodificados fora do documento (abrir sem travar)
#include "LayerSnapshot.hpp"      // instantaneo das camadas: a gravacao em segundo plano le dele

#include "../../utils/Point2D.hpp"
#include "../../utils/ColorRGBA.hpp"
#include "../../utils/Dab.hpp"                       // DabBlendMode
#include "../../core/math/BezierCurve.hpp"
#include "../../core/math/ViewportTransform.hpp"
#include "../../core/color/ColorProfile.hpp"         // ColorProfileManager (lista de perfis)
#include "../../core/stroke/PointerEvent.hpp"
#include "../../core/stroke/DynamicStabilizer.hpp"
#include "../../infrastructure/telemetry/EngineTelemetry.hpp"

#endif // ALADYN_ENGINE_PUBLIC_API_HPP
