#include "CompositeProjection.hpp"

#include <algorithm>

namespace aladyn::engine::document::projection {

CompositeProjection::CompositeProjection(int width, int height)
    : m_width(std::max(0, width)),
      m_height(std::max(0, height)),
      m_tilesX((m_width + kTileSize - 1) / kTileSize),
      m_tilesY((m_height + kTileSize - 1) / kTileSize),
      m_stale(static_cast<size_t>(m_tilesX) * static_cast<size_t>(m_tilesY), 1),
      m_staleCount(m_stale.size()) {}

void CompositeProjection::markAllStale() noexcept {
    std::fill(m_stale.begin(), m_stale.end(), static_cast<uint8_t>(1));
    m_staleCount = m_stale.size();
}

bool CompositeProjection::touchedTiles(const PixelRect& rect, TileSpan& span) const noexcept {
    const int x0 = std::max(rect.x0, 0);
    const int y0 = std::max(rect.y0, 0);
    const int x1 = std::min(rect.x1, m_width);
    const int y1 = std::min(rect.y1, m_height);
    if (x0 >= x1 || y0 >= y1) return false;
    span = TileSpan{x0 / kTileSize, y0 / kTileSize, (x1 - 1) / kTileSize, (y1 - 1) / kTileSize};
    return true;
}

PixelRect CompositeProjection::tileExtent(int tx, int ty) const noexcept {
    return PixelRect{tx * kTileSize, ty * kTileSize, std::min((tx + 1) * kTileSize, m_width),
                     std::min((ty + 1) * kTileSize, m_height)};
}

void CompositeProjection::setTile(int tx, int ty, bool stale) noexcept {
    uint8_t& cell = m_stale[static_cast<size_t>(ty) * static_cast<size_t>(m_tilesX) + static_cast<size_t>(tx)];
    if ((cell != 0) == stale) return;
    cell = stale ? 1 : 0;
    if (stale) {
        ++m_staleCount;
    } else {
        --m_staleCount;
    }
}

void CompositeProjection::markStale(const PixelRect& rect) {
    TileSpan span{};
    if (!touchedTiles(rect, span)) return;
    for (int ty = span.ty0; ty <= span.ty1; ++ty) {
        for (int tx = span.tx0; tx <= span.tx1; ++tx) setTile(tx, ty, true);
    }
}

void CompositeProjection::markFresh(const PixelRect& rect) {
    if (m_staleCount == 0) return;
    TileSpan span{};
    if (!touchedTiles(rect, span)) return;
    for (int ty = span.ty0; ty <= span.ty1; ++ty) {
        for (int tx = span.tx0; tx <= span.tx1; ++tx) {
            const PixelRect extent = tileExtent(tx, ty);
            if (extent.x0 >= rect.x0 && extent.x1 <= rect.x1 && extent.y0 >= rect.y0 && extent.y1 <= rect.y1) {
                setTile(tx, ty, false);
            }
        }
    }
}

PixelRect CompositeProjection::expandToStale(const PixelRect& rect) const {
    TileSpan span{};
    if (m_staleCount == 0 || !touchedTiles(rect, span)) return rect;
    PixelRect box = rect;
    for (int ty = span.ty0; ty <= span.ty1; ++ty) {
        for (int tx = span.tx0; tx <= span.tx1; ++tx) {
            if (m_stale[static_cast<size_t>(ty) * static_cast<size_t>(m_tilesX) + static_cast<size_t>(tx)] == 0) continue;
            const PixelRect extent = tileExtent(tx, ty);
            box = PixelRect{std::min(box.x0, extent.x0), std::min(box.y0, extent.y0), std::max(box.x1, extent.x1),
                            std::max(box.y1, extent.y1)};
        }
    }
    return box;
}

std::vector<PixelRect> CompositeProjection::staleRects(const PixelRect& rect) const {
    std::vector<PixelRect> boxes;
    TileSpan span{};
    if (m_staleCount == 0 || !touchedTiles(rect, span)) return boxes;

    // Uma caixa em construção: as colunas [tx0, tx1] e as linhas de `ty0` até a última que a estendeu.
    struct Open {
        int tx0, tx1, ty0, lastRow;
    };
    std::vector<Open> open;
    const auto close = [&](const Open& box) {
        boxes.push_back(PixelRect{box.tx0 * kTileSize, box.ty0 * kTileSize, std::min((box.tx1 + 1) * kTileSize, m_width),
                                  std::min((box.lastRow + 1) * kTileSize, m_height)});
    };
    for (int ty = span.ty0; ty <= span.ty1; ++ty) {
        std::vector<Open> next;
        int tx = span.tx0;
        while (tx <= span.tx1) {
            if (m_stale[static_cast<size_t>(ty) * static_cast<size_t>(m_tilesX) + static_cast<size_t>(tx)] == 0) {
                ++tx;
                continue;
            }
            const int runStart = tx;
            while (tx <= span.tx1 &&
                   m_stale[static_cast<size_t>(ty) * static_cast<size_t>(m_tilesX) + static_cast<size_t>(tx)] != 0) {
                ++tx;
            }
            const int runEnd = tx - 1;
            const auto same = std::find_if(open.begin(), open.end(), [&](const Open& box) {
                return box.tx0 == runStart && box.tx1 == runEnd && box.lastRow == ty - 1;
            });
            if (same != open.end()) {
                same->lastRow = ty;
                next.push_back(*same);
                open.erase(same);
            } else {
                next.push_back(Open{runStart, runEnd, ty, ty});
            }
        }
        for (const Open& box : open) close(box);  // não foram estendidas por esta linha
        open = std::move(next);
    }
    for (const Open& box : open) close(box);
    return boxes;
}

} // namespace aladyn::engine::document::projection
