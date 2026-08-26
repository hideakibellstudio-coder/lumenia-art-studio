#ifndef ALADYN_ENGINE_SELECTION_MASK_HPP
#define ALADYN_ENGINE_SELECTION_MASK_HPP

#include <vector>
#include <cstdint>
#include <algorithm>
#include <unordered_map>
#include <unordered_set>
#include "../math/Rect2D.hpp"

namespace aladyn::engine::raster {

enum class SelectionMode {
    New = 0,       // Substitui seleção existente
    Add = 1,       // União (+)
    Subtract = 2,  // Diferença (-)
    Intersect = 3  // Interseção (&)
};

class SelectionMask {
public:
    SelectionMask() : m_width(0), m_height(0), m_hasSelection(false) {}

    SelectionMask(int width, int height)
        : m_width(width), m_height(height), m_hasSelection(false),
          m_mask(static_cast<size_t>(width * height), 0) {}

    void resize(int width, int height) {
        m_width = width;
        m_height = height;
        m_hasSelection = false;
        m_mask.assign(static_cast<size_t>(width * height), 0);
    }

    [[nodiscard]] int getWidth() const noexcept { return m_width; }
    [[nodiscard]] int getHeight() const noexcept { return m_height; }
    [[nodiscard]] bool hasSelection() const noexcept { return m_hasSelection; }
    [[nodiscard]] const uint8_t* getData() const noexcept { return m_mask.data(); }
    [[nodiscard]] uint8_t* getData() noexcept { return m_mask.data(); }
    [[nodiscard]] size_t getSizeInBytes() const noexcept { return m_mask.size(); }

    [[nodiscard]] inline uint8_t getValue(int x, int y) const noexcept {
        if (!m_hasSelection || x < 0 || x >= m_width || y < 0 || y >= m_height) return 0;
        return m_mask[static_cast<size_t>(y * m_width + x)];
    }

    inline void setValue(int x, int y, uint8_t val) noexcept {
        if (x >= 0 && x < m_width && y >= 0 && y < m_height) {
            m_mask[static_cast<size_t>(y * m_width + x)] = val;
        }
    }

    void clear() noexcept {
        std::fill(m_mask.begin(), m_mask.end(), 0);
        m_hasSelection = false;
    }

    void selectAll() noexcept {
        std::fill(m_mask.begin(), m_mask.end(), 255);
        m_hasSelection = true;
    }

    void invert() noexcept {
        if (!m_hasSelection) {
            selectAll();
            return;
        }
        bool anySelected = false;
        for (auto& v : m_mask) {
            v = static_cast<uint8_t>(255 - v);
            if (v > 0) anySelected = true;
        }
        m_hasSelection = anySelected;
    }

    void combine(const std::vector<uint8_t>& incoming, SelectionMode mode) noexcept {
        if (incoming.size() != m_mask.size()) return;

        const size_t total = m_mask.size();
        bool anySelected = false;

        switch (mode) {
            case SelectionMode::New:
                std::copy(incoming.begin(), incoming.end(), m_mask.begin());
                break;

            case SelectionMode::Add:
                for (size_t i = 0; i < total; ++i) {
                    m_mask[i] = static_cast<uint8_t>(std::min(255, static_cast<int>(m_mask[i]) + static_cast<int>(incoming[i])));
                }
                break;

            case SelectionMode::Subtract:
                for (size_t i = 0; i < total; ++i) {
                    m_mask[i] = static_cast<uint8_t>(std::max(0, static_cast<int>(m_mask[i]) - static_cast<int>(incoming[i])));
                }
                break;

            case SelectionMode::Intersect:
                for (size_t i = 0; i < total; ++i) {
                    m_mask[i] = static_cast<uint8_t>((static_cast<int>(m_mask[i]) * static_cast<int>(incoming[i])) / 255);
                }
                break;
        }

        for (size_t i = 0; i < total; ++i) {
            if (m_mask[i] > 0) {
                anySelected = true;
                break;
            }
        }
        m_hasSelection = anySelected;
    }

    [[nodiscard]] math::Rect2D getBounds() const noexcept {
        if (!m_hasSelection || m_width <= 0 || m_height <= 0) {
            return math::Rect2D{0, 0, 0, 0};
        }

        int minX = m_width, maxX = -1;
        int minY = m_height, maxY = -1;

        for (int y = 0; y < m_height; ++y) {
            const size_t rowOff = static_cast<size_t>(y * m_width);
            for (int x = 0; x < m_width; ++x) {
                if (m_mask[rowOff + x] > 0) {
                    if (x < minX) minX = x;
                    if (x > maxX) maxX = x;
                    if (y < minY) minY = y;
                    if (y > maxY) maxY = y;
                }
            }
        }

        if (maxX < minX || maxY < minY) {
            return math::Rect2D{0, 0, 0, 0};
        }

        return math::Rect2D{
            static_cast<double>(minX),
            static_cast<double>(minY),
            static_cast<double>(maxX - minX + 1),
            static_cast<double>(maxY - minY + 1)
        };
    }

    [[nodiscard]] std::vector<int> getContourSegments() const noexcept {
        if (!m_hasSelection || m_width <= 0 || m_height <= 0) return {};
        std::vector<int> lines;

        auto bounds = getBounds();
        int minX = std::max(0, static_cast<int>(bounds.x) - 1);
        int maxX = std::min(m_width - 1, static_cast<int>(bounds.x + bounds.width) + 1);
        int minY = std::max(0, static_cast<int>(bounds.y) - 1);
        int maxY = std::min(m_height - 1, static_cast<int>(bounds.y + bounds.height) + 1);

        for (int y = minY; y <= maxY; ++y) {
            const size_t rowOff = static_cast<size_t>(y * m_width);
            for (int x = minX; x <= maxX; ++x) {
                bool cur = (m_mask[rowOff + x] >= 128);

                // Borda Direita
                if (x + 1 < m_width) {
                    bool right = (m_mask[rowOff + (x + 1)] >= 128);
                    if (cur != right) {
                        lines.push_back(x + 1); lines.push_back(y);
                        lines.push_back(x + 1); lines.push_back(y + 1);
                    }
                }
                // Borda Inferior
                if (y + 1 < m_height) {
                    bool bottom = (m_mask[static_cast<size_t>((y + 1) * m_width + x)] >= 128);
                    if (cur != bottom) {
                        lines.push_back(x); lines.push_back(y + 1);
                        lines.push_back(x + 1); lines.push_back(y + 1);
                    }
                }
            }
        }
        return lines;
    }

    [[nodiscard]] std::vector<std::vector<int>> getContourLoops() const noexcept {
        if (!m_hasSelection || m_width <= 0 || m_height <= 0) return {};

        auto bounds = getBounds();
        int minX = std::max(0, static_cast<int>(bounds.x) - 1);
        int maxX = std::min(m_width - 1, static_cast<int>(bounds.x + bounds.width) + 1);
        int minY = std::max(0, static_cast<int>(bounds.y) - 1);
        int maxY = std::min(m_height - 1, static_cast<int>(bounds.y + bounds.height) + 1);

        struct Point {
            int x, y;
            bool operator==(const Point& o) const { return x == o.x && y == o.y; }
            bool operator<(const Point& o) const { return y < o.y || (y == o.y && x < o.x); }
        };

        struct PointHash {
            size_t operator()(const Point& p) const {
                return (static_cast<size_t>(p.y) << 16) ^ static_cast<size_t>(p.x);
            }
        };

        std::unordered_map<Point, std::vector<Point>, PointHash> adj;

        for (int y = minY; y <= maxY; ++y) {
            const size_t rowOff = static_cast<size_t>(y * m_width);
            for (int x = minX; x <= maxX; ++x) {
                bool cur = (m_mask[rowOff + x] >= 128);

                // Aresta vertical direita
                if (x + 1 < m_width) {
                    bool right = (m_mask[rowOff + (x + 1)] >= 128);
                    if (cur != right) {
                        Point p1{x + 1, y};
                        Point p2{x + 1, y + 1};
                        adj[p1].push_back(p2);
                        adj[p2].push_back(p1);
                    }
                }
                // Aresta horizontal inferior
                if (y + 1 < m_height) {
                    bool bottom = (m_mask[static_cast<size_t>((y + 1) * m_width + x)] >= 128);
                    if (cur != bottom) {
                        Point p1{x, y + 1};
                        Point p2{x + 1, y + 1};
                        adj[p1].push_back(p2);
                        adj[p2].push_back(p1);
                    }
                }
            }
        }

        std::vector<std::vector<int>> loops;
        std::unordered_set<uint64_t> visitedEdges;

        auto edgeKey = [](const Point& a, const Point& b) -> uint64_t {
            Point p1 = std::min(a, b);
            Point p2 = std::max(a, b);
            return (static_cast<uint64_t>(p1.y) << 48) |
                   (static_cast<uint64_t>(p1.x) << 32) |
                   (static_cast<uint64_t>(p2.y) << 16) |
                   (static_cast<uint64_t>(p2.x));
        };

        for (const auto& [startPt, neighbors] : adj) {
            for (const auto& nextPt : neighbors) {
                uint64_t key = edgeKey(startPt, nextPt);
                if (visitedEdges.count(key)) continue;

                std::vector<int> currentLoop;
                currentLoop.push_back(startPt.x);
                currentLoop.push_back(startPt.y);

                Point curr = nextPt;
                visitedEdges.insert(key);

                while (true) {
                    currentLoop.push_back(curr.x);
                    currentLoop.push_back(curr.y);
                    if (curr == startPt) break;

                    Point nextChoice{ -1, -1 };
                    auto it = adj.find(curr);
                    if (it != adj.end()) {
                        for (const auto& candidate : it->second) {
                            uint64_t candidateKey = edgeKey(curr, candidate);
                            if (!visitedEdges.count(candidateKey)) {
                                nextChoice = candidate;
                                visitedEdges.insert(candidateKey);
                                break;
                            }
                        }
                    }

                    if (nextChoice.x == -1) break;
                    curr = nextChoice;
                }

                if (currentLoop.size() >= 6) {
                    loops.push_back(std::move(currentLoop));
                }
            }
        }

        return loops;
    }

private:
    int m_width{0};
    int m_height{0};
    bool m_hasSelection{false};
    std::vector<uint8_t> m_mask;
};

} // namespace aladyn::engine::raster

#endif // ALADYN_ENGINE_SELECTION_MASK_HPP
