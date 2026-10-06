#ifndef ALADYN_ENGINE_TILE_GRID_HPP
#define ALADYN_ENGINE_TILE_GRID_HPP

#include "Tile.hpp"
#include "SpatialCuller.hpp"
#include <unordered_map>
#include <memory>
#include <cstdint>
#include <cstddef>

namespace aladyn::engine::canvas {

struct TileIndexHash {
    std::size_t operator()(const TileIndex& idx) const noexcept {
        const uint64_t ux = static_cast<uint32_t>(idx.x);
        const uint64_t uy = static_cast<uint32_t>(idx.y);
        return static_cast<std::size_t>((ux << 32) | uy);
    }
};

class TileGrid {
public:
    TileGrid(int width, int height, PixelFormat format = PixelFormat::RGBA8);

    // O formato dos tiles desta grade: todos os que ela cria, adota ou copia têm este formato.
    [[nodiscard]] PixelFormat getFormat() const noexcept { return m_format; }
    [[nodiscard]] int getWidth() const noexcept { return m_width; }
    [[nodiscard]] int getHeight() const noexcept { return m_height; }
    [[nodiscard]] int getTilesCountX() const noexcept { return m_tilesX; }
    [[nodiscard]] int getTilesCountY() const noexcept { return m_tilesY; }

    Tile* getTile(int tileX, int tileY);
    Tile* getOrCreateTile(int tileX, int tileY);
    // Coloca na grade um tile que já tem o buffer pronto (a abertura de um arquivo decodifica
    // os buffers em paralelo e só aqui os insere). Fora da grade, ou com buffer de outro formato:
    // nullptr, nada é inserido.
    Tile* adoptTile(int tileX, int tileY, std::shared_ptr<PixelBuffer> buffer);

    void clearAll(utils::ColorRGBA color = {0, 0, 0, 0});
    // Redimensiona preservando os pixels existentes no offset informado.
    // Usado por canvas resize/crop; nunca recria a camada silenciosamente.
    void resizePreserve(int width, int height, int offsetX = 0, int offsetY = 0);
    // Remove todos os tiles alocados (limpa o scratch sem tocar no layout)
    void clearTiles();
    // Remove tiles 100% transparentes (liberação de RAM pós-borracha)
    size_t pruneEmptyTiles();
    // Copia com Copy-on-Write (compartilha buffers imutáveis sem clonar 64KB). A grade passa a ter o formato da origem.
    void copyFrom(const TileGrid& src);
    [[nodiscard]] size_t getActiveTilesCount() const noexcept { return m_tiles.size(); }

    // ─── FASE 4: ESCALABILIDADE DE MEMÓRIA & COMPRESSÃO ─────────────────────
    size_t compressInactiveTiles();
    size_t decompressAllTiles();
    [[nodiscard]] size_t getMemoryFootprintBytes() const noexcept;
    [[nodiscard]] size_t getCompressedTilesCount() const noexcept;
    [[nodiscard]] size_t getCowSharedTilesCount() const noexcept;

    // ─── FASE 5: VIEWPORT DIRTY TILE STREAMING ──────────────────────────────
    [[nodiscard]] std::vector<std::pair<int, int>> getDirtyTileIndices() const;
    void clearDirtyFlags() noexcept;
    [[nodiscard]] const uint8_t* getTileData(int tileX, int tileY) const noexcept;
    [[nodiscard]] size_t getTileDataSize() const noexcept;

    // Itera sobre todos os tiles alocados (para commitScratch)
    template<typename Fn>
    void forEachTile(Fn&& fn) {
        for (auto& [idx, tile] : m_tiles) {
            if (tile) fn(idx, *tile);
        }
    }
    template<typename Fn>
    void forEachTile(Fn&& fn) const {
        for (const auto& [idx, tile] : m_tiles) {
            if (tile) fn(idx, *tile);
        }
    }

private:
    int m_width{0};
    int m_height{0};
    PixelFormat m_format{PixelFormat::RGBA8};
    int m_tilesX{0};
    int m_tilesY{0};
    std::unordered_map<TileIndex, std::unique_ptr<Tile>, TileIndexHash> m_tiles;
};

} // namespace aladyn::engine::canvas

#endif // ALADYN_ENGINE_TILE_GRID_HPP
