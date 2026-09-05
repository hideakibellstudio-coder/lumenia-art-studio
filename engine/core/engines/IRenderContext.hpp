#ifndef ALADYN_ENGINE_IRENDER_CONTEXT_HPP
#define ALADYN_ENGINE_IRENDER_CONTEXT_HPP

#include "../canvas/TileGrid.hpp"
#include "../canvas/PixelBuffer.hpp"
#include "../raster/PixelContext.hpp"

namespace aladyn::engine::engines {

// ─── CONTRATO FORMAL DE CONTEXTO DE RENDERIZAÇÃO (ARCcC REGRA 5) ────────────
// Encapsula os destinos de dados de pixel para desacoplar os mini-motores
// de estruturas internas de camadas e do document pipeline.
class IRenderContext {
public:
    virtual ~IRenderContext() = default;

    [[nodiscard]] virtual canvas::TileGrid& getTileGrid() noexcept = 0;
    [[nodiscard]] virtual const canvas::PixelBuffer* getCompositeBuffer() const noexcept = 0;
    [[nodiscard]] virtual const raster::PixelContext& getPixelContext() const noexcept = 0;
};

// Implementação padrão de envelope leve (Zero Alloc / Value Object)
class SimpleRenderContext final : public IRenderContext {
public:
    SimpleRenderContext(
        canvas::TileGrid& grid,
        const canvas::PixelBuffer* compBuffer = nullptr,
        const raster::PixelContext& ctx = {}
    ) noexcept
        : m_grid(grid), m_compBuffer(compBuffer), m_ctx(ctx) {}

    [[nodiscard]] canvas::TileGrid& getTileGrid() noexcept override { return m_grid; }
    [[nodiscard]] const canvas::PixelBuffer* getCompositeBuffer() const noexcept override { return m_compBuffer; }
    [[nodiscard]] const raster::PixelContext& getPixelContext() const noexcept override { return m_ctx; }

private:
    canvas::TileGrid& m_grid;
    const canvas::PixelBuffer* m_compBuffer{nullptr};
    const raster::PixelContext& m_ctx;
};

} // namespace aladyn::engine::engines

#endif // ALADYN_ENGINE_IRENDER_CONTEXT_HPP
