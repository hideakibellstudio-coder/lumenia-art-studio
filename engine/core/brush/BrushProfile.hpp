#ifndef ALADYN_ENGINE_BRUSH_PROFILE_HPP
#define ALADYN_ENGINE_BRUSH_PROFILE_HPP

#include "BrushTip.hpp"
#include "../math/BezierCurve.hpp"
#include "../raster/Dab.hpp"
#include "../texture/Texture2D.hpp"
#include "../texture/ProceduralTextures.hpp"
#include <memory>

namespace aladyn::engine::brush {

// ─── TIPO DO MOTOR ATIVO ────────────────────────────────────────────────────
enum class EngineType {
    Brush     = 0,   // Motor padrão (pincel básico)
    Pencil    = 1,   // Lápis / Grafite / Giz
    Inker     = 2,   // Caneta / Nanquim / G-Pen
    Eraser    = 3,   // Borracha
    Marker    = 4,   // Marcador / Feltro (Fase 2)
    Blur      = 5,   // Blur / Desfoque (Fase 2)
    Smudge    = 6,   // Smudge / Arrasto (Fase 3)
    Watercolor= 7,   // Aquarela (Fase 4 — requer LayerStack)
    OilImpasto= 8    // Óleo 3D (Fase 5 — requer LayerStack + NormalMap)
};

// ─── PARÂMETROS EXCLUSIVOS — LÁPIS & CARVÃO ────────────────────────────────
struct PencilParams {
    // graphiteHardness: 0.0 = 6B ultra mole (deposita muito com pouca pressão)
    //                   1.0 = 2H duro (requer alta pressão para depositar)
    double graphiteHardness{0.5};
    bool   tiltShadingEnabled{false}; // Expansão lateral por inclinação da caneta
};

// ─── PARÂMETROS EXCLUSIVOS — CANETA & NANQUIM ──────────────────────────────
struct InkerParams {
    double inkFlowRate{1.0};      // Taxa de vazão de tinta (0-1: seco a cheio)
    double taperSmoothing{0.5};   // Suavização do afunilamento de entrada/saída
};

// ─── PARÂMETROS EXCLUSIVOS — MARCADOR (Fase 2) ────────────────────────────
struct MarkerParams {
    double solventWetness{0.5};  // Umidade do solvente (fusão de sobreposições)
    double edgeDarkening{0.3};   // Escurecimento de borda por secagem
};

// ─── PARÂMETROS EXCLUSIVOS — BLUR (Fase 2) ────────────────────────────────
struct BlurParams {
    int    blurRadius{2};         // Raio do kernel Gaussiano (1-5)
    double blurStrength{0.7};     // Intensidade da mistura (0-1)
};

// ─── PARÂMETROS EXCLUSIVOS — SMUDGE (Fase 3) ──────────────────────────────
struct SmudgeParams {
    double colorPickup{0.7};      // Quantidade de cor coletada da tela (0-1)
    double mixRatio{0.5};         // Razão de mistura cor nova vs cor coletada
    double smudgeStretch{1.0};    // Fator de alongamento/arrasto
};

// ─── PARÂMETROS EXCLUSIVOS — AQUARELA (Fase 4) ─────────────────────────────
struct WatercolorParams {
    double waterLevel{0.6};       // Quantidade de água/umidade depositada (0-1)
    double pigmentBleed{0.5};     // Taxa de sangramento/difusão em áreas úmidas (0-1)
    double fringeIntensity{0.4};  // Intensidade do anel de borda escura de secagem (Coffee Ring Effect)
    double granulation{0.3};      // Deposição de pigmento nos vales da textura do papel
    double wetMixFactor{0.4};     // Fator de mistura com tinta molhada existente no canvas (0-1)
    double paintDepletion{0.0};   // Taxa de depleção do reservatório de cerda (0-1)
};

// ─── PARÂMETROS EXCLUSIVOS — ÓLEO & IMPASTO (Fase 5) ───────────────────────
struct OilParams {
    double impastoDepth{0.6};       // Espessura do acúmulo 3D de matéria de tinta (0-1)
    double bristleGrooves{0.5};     // Profundidade das ranhuras de cerda paralelas ao traço (0-1)
    double viscosity{0.7};          // Viscosidade da tinta (resistência à fusão/arrasto)
    double specularBrilliance{0.5}; // Brilho especular úmido da tinta fresca a óleo
    double wetMixFactor{0.5};       // Fator de fusão com a cor existente do canvas (0-1)
    double paintDepletion{0.0};     // Taxa de esgotamento de tinta da cerda ao longo do traço (0-1)
};

// ─── PERFIL COMPLETO DO PINCEL ──────────────────────────────────────────────
class BrushProfile {
public:
    // ─── MOTOR ATIVO ─────────────────────────────────────────────────────────
    EngineType engineType{EngineType::Brush};

    // ─── 1. TAMANHO MASTER E PERCENTUAL MÍNIMO (ESTILO SAI 2) ───────────────
    double brushSize{24.0};         // Tamanho master nominal em pixels (1 a 250px)
    double minSizePercent{0.0};     // Tamanho mínimo em % a 0% de pressão (0.0 a 1.0)

    // ─── 2. FLUXO, OPACIDADE E MODO DE MESCLAGEM ─────────────────────────────
    double opacity{1.0};            // Opacidade máxima nominal (0.0 a 1.0)
    double minOpacityPercent{0.0};  // Opacidade mínima em % a 0% de pressão
    double hardness{1.0};           // Dureza da borda procedural (0.0=macio, 1.0=duro)
    raster::DabBlendMode blendMode{raster::DabBlendMode::Normal};

    double spacingFactor{0.15};
    raster::ColorRGBA baseColor{10, 10, 14, 255};

    bool pressureSizeEnabled{true};
    bool pressureFlowEnabled{true};
    bool velocitySizeEnabled{false};

    math::BezierCurve pressureSizeCurve{math::CurvePreset::Linear};
    math::BezierCurve pressureFlowCurve{math::CurvePreset::Linear};
    math::BezierCurve velocitySizeCurve{math::CurvePreset::Linear};

    // ─── 3. GEOMETRIA DA PONTA E DINÂMICAS ───────────────────────────────────
    BrushTip tip;
    double pressureToAngle{0.0};
    double pressureToAspect{0.0};
    int    scatterCount{1};

    // ─── 4. EMISSÃO TEMPORAL (AIRBRUSH) ──────────────────────────────────────
    bool   timeSpacingEnabled{false};
    double dabsPerSecond{60.0};

    // ─── 5. TEXTURA INTERNA DO PINCEL (BRUSH HEIGHTMAP) ─────────────────────
    bool   brushGrainEnabled{true};
    double brushGrainScale{1.0};
    double brushGrainContrast{1.0};
    bool   brushGrainInvert{false};
    math::BezierCurve brushTextureCurve{math::CurvePreset::Linear};

    std::shared_ptr<texture::Texture2D> shapeTexture{
        texture::ProceduralTextures::createRadialShapeMask(256)};
    std::shared_ptr<texture::Texture2D> brushHeightTexture{
        texture::ProceduralTextures::createHeightPreset(texture::HeightPreset::NoiseGrain, 512, 512)};

    // ─── 6. PARÂMETROS EXCLUSIVOS POR MINI-MOTOR ─────────────────────────────
    PencilParams     pencilParams;
    InkerParams      inkerParams;
    MarkerParams     markerParams;
    BlurParams       blurParams;
    SmudgeParams     smudgeParams;
    WatercolorParams watercolorParams;
    OilParams        oilParams;
};

} // namespace aladyn::engine::brush

#endif // ALADYN_ENGINE_BRUSH_PROFILE_HPP
