// Scenes for the 16-bit compositor harnesses (S5): one description, applied to an 8-bit stack and to a 16-bit stack
// with the same content (every 8-bit pixel widened by x257), so the two documents can be compared.
#ifndef ALADYN_TESTS_NATIVE_COMPOSITOR16_SCENE_HPP
#define ALADYN_TESTS_NATIVE_COMPOSITOR16_SCENE_HPP

#include "engine/core/canvas/PixelFormat.hpp"
#include "engine/core/document/Compositor.hpp"
#include "engine/core/document/FilterLayer.hpp"
#include "engine/core/document/LayerStack.hpp"

#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <memory>
#include <random>
#include <vector>

namespace scene16 {

namespace doc = aladyn::engine::document;
using aladyn::engine::canvas::PixelFormat;
using aladyn::engine::utils::ColorRGBA;

constexpr int kWidth = 300;   // 3 x 3 tiles
constexpr int kHeight = 260;
constexpr ColorRGBA kBackground{255, 255, 255, 255};

enum class Kind { Paint, Group, Filter };

struct Block {
    int x0, y0, x1, y1;
    uint32_t seed;
    int alphaMode;  // 0 opaque, 1 one soft alpha, 2 alpha ramp, 3 alpha noise
    uint8_t softAlpha;
};

struct LayerPlan {
    Kind kind{Kind::Paint};
    doc::LayerBlendMode mode{doc::LayerBlendMode::Normal};
    double opacity{1.0};
    bool visible{true};
    bool clip{false};
    int parent{-1};
    bool isolated{false};  // groups: false is Pass Through
    doc::FilterType filter{doc::FilterType::GaussianBlur};
    float params[3]{0.0f, 0.0f, 0.0f};
    std::vector<Block> blocks;
};

inline uint32_t hash(uint32_t a, uint32_t b, uint32_t c) {
    uint32_t h = a * 0x9E3779B1u ^ (b + 0x7F4A7C15u) * 0x85EBCA6Bu ^ (c + 0x165667B1u) * 0xC2B2AE35u;
    h ^= h >> 15;
    h *= 0x2C1B3C6Du;
    h ^= h >> 12;
    return h;
}

// The pixel a block puts at (x, y): colour noise everywhere, alpha by the block's mode.
inline ColorRGBA blockPixel(const Block& block, int x, int y) {
    const uint32_t h = hash(block.seed, static_cast<uint32_t>(x), static_cast<uint32_t>(y));
    ColorRGBA pixel{static_cast<uint8_t>(h), static_cast<uint8_t>(h >> 8), static_cast<uint8_t>(h >> 16), 255};
    switch (block.alphaMode) {
        case 1: pixel.a = block.softAlpha; break;
        case 2: pixel.a = static_cast<uint8_t>(1 + (x - block.x0) * 254 / std::max(1, block.x1 - block.x0 - 1)); break;
        case 3: pixel.a = static_cast<uint8_t>(h >> 24); break;
        default: break;
    }
    return pixel;
}

inline void paintBlock(doc::Layer& layer, const Block& block, bool wide) {
    auto& grid = layer.getTileGrid();
    for (int y = std::max(0, block.y0); y < std::min(kHeight, block.y1); ++y) {
        for (int x = std::max(0, block.x0); x < std::min(kWidth, block.x1); ++x) {
            const ColorRGBA pixel = blockPixel(block, x, y);
            auto& buffer = grid.getOrCreateTile(x / 128, y / 128)->getBuffer();
            if (wide) buffer.setPixel16(x % 128, y % 128, aladyn::engine::canvas::widen(pixel));
            else buffer.setPixel(x % 128, y % 128, pixel);
        }
    }
}

inline Block randomBlock(std::mt19937& rng, bool opaque) {
    const int x0 = static_cast<int>(rng() % 220), y0 = static_cast<int>(rng() % 190);
    Block block{x0, y0, x0 + 40 + static_cast<int>(rng() % 200), y0 + 40 + static_cast<int>(rng() % 170), static_cast<uint32_t>(rng()),
                opaque ? 0 : static_cast<int>(rng() % 4), static_cast<uint8_t>(30 + rng() % 220)};
    return block;
}

// Builds the stack the plan describes, with `format` pixels and the plan's content widened when 16-bit.
inline std::unique_ptr<doc::LayerStack> build(const std::vector<LayerPlan>& plan, PixelFormat format) {
    auto stack = std::make_unique<doc::LayerStack>(kWidth, kHeight, format);
    const bool wide = format == PixelFormat::RGBA16;
    // A new stack already holds one empty drawing layer: the plan's layer i is the stack's layer i + offset.
    const int offset = static_cast<int>(stack->getDrawingLayerCount());
    std::vector<int> parents(static_cast<size_t>(offset), -1);
    for (size_t i = 0; i < plan.size(); ++i) {
        const LayerPlan& item = plan[i];
        const int index = item.kind == Kind::Group ? stack->addGroup("g")
                          : item.kind == Kind::Filter ? stack->addFilterLayer("f", item.filter)
                                                      : stack->addLayer("p");
        doc::Layer* layer = stack->getDrawingLayer(index);
        layer->setBlendMode(item.mode);
        layer->setOpacity(item.opacity);
        layer->setVisible(item.visible);
        layer->setClippingMask(item.clip);
        parents.push_back(item.parent < 0 ? -1 : item.parent + offset);
        if (item.kind == Kind::Group) stack->setGroupPassThrough(index, !item.isolated);
        if (item.kind == Kind::Filter) {
            auto* filter = dynamic_cast<doc::FilterLayer*>(layer);
            for (size_t p = 0; p < 3; ++p) filter->setParam(p, item.params[p]);
        }
        for (const Block& block : item.blocks) paintBlock(*layer, block, wide);
    }
    stack->setLayerParents(parents);
    return stack;
}


// ─── plans ───────────────────────────────────────────────────────────────────

inline LayerPlan paint(std::mt19937& rng, doc::LayerBlendMode mode, double opacity, bool opaque) {
    LayerPlan plan;
    plan.mode = mode;
    plan.opacity = opacity;
    for (int i = 0, n = 1 + static_cast<int>(rng() % 3); i < n; ++i) plan.blocks.push_back(randomBlock(rng, opaque));
    return plan;
}

inline LayerPlan base(std::mt19937& rng) {
    LayerPlan plan = paint(rng, doc::LayerBlendMode::Normal, 1.0, true);
    plan.blocks.push_back(Block{0, 0, kWidth, kHeight, static_cast<uint32_t>(rng()), 0, 255});
    return plan;
}

inline double randomOpacity(std::mt19937& rng) {
    const double choices[] = {1.0, 0.85, 0.6, 0.35, 0.1};
    return choices[rng() % 5];
}

inline std::vector<LayerPlan> normalPlan(std::mt19937& rng) {
    std::vector<LayerPlan> plan{base(rng)};
    for (int i = 0, n = 2 + static_cast<int>(rng() % 3); i < n; ++i) {
        plan.push_back(paint(rng, doc::LayerBlendMode::Normal, randomOpacity(rng), false));
        plan.back().visible = rng() % 6 != 0;
    }
    return plan;
}

inline std::vector<LayerPlan> modesPlan(std::mt19937& rng, int firstMode) {
    std::vector<LayerPlan> plan{base(rng)};
    for (int i = 0, n = 2 + static_cast<int>(rng() % 3); i < n; ++i) {
        int mode = 1 + (firstMode + i * 5) % 12;
        if (mode == static_cast<int>(doc::LayerBlendMode::PassThrough)) mode = static_cast<int>(doc::LayerBlendMode::Add);
        plan.push_back(paint(rng, static_cast<doc::LayerBlendMode>(mode), randomOpacity(rng), false));
    }
    return plan;
}

// base, an isolated group of two or three layers, a clipped layer, a Pass Through group, a hidden layer.
inline std::vector<LayerPlan> structurePlan(std::mt19937& rng) {
    std::vector<LayerPlan> plan{base(rng)};
    LayerPlan group;
    group.kind = Kind::Group;
    group.isolated = true;
    group.opacity = randomOpacity(rng);
    group.mode = rng() % 2 ? doc::LayerBlendMode::Normal : doc::LayerBlendMode::Multiply;
    plan.push_back(group);
    const int groupIndex = static_cast<int>(plan.size()) - 1;
    for (int i = 0, n = 2 + static_cast<int>(rng() % 2); i < n; ++i) {
        plan.push_back(paint(rng, doc::LayerBlendMode::Normal, randomOpacity(rng), false));
        plan.back().parent = groupIndex;
    }
    plan.push_back(paint(rng, doc::LayerBlendMode::Normal, randomOpacity(rng), false));
    plan.push_back(paint(rng, doc::LayerBlendMode::Normal, randomOpacity(rng), false));
    plan.back().clip = true;
    LayerPlan passThrough;
    passThrough.kind = Kind::Group;
    passThrough.opacity = randomOpacity(rng);
    plan.push_back(passThrough);
    const int passIndex = static_cast<int>(plan.size()) - 1;
    for (int i = 0; i < 2; ++i) {
        plan.push_back(paint(rng, doc::LayerBlendMode::Normal, randomOpacity(rng), false));
        plan.back().parent = passIndex;
    }
    plan.back().visible = rng() % 3 != 0;
    return plan;
}

inline LayerPlan filterPlan(doc::FilterType type, std::mt19937& rng) {
    LayerPlan plan;
    plan.kind = Kind::Filter;
    plan.filter = type;
    plan.opacity = rng() % 2 ? 1.0 : 0.6;
    const auto pick = [&](float lo, float hi) { return lo + (hi - lo) * static_cast<float>(rng() % 1000) / 1000.0f; };
    switch (type) {
        case doc::FilterType::BrightnessContrast: plan.params[0] = pick(-50, 50); plan.params[1] = pick(-50, 50); plan.params[2] = pick(0.5f, 2.0f); break;
        case doc::FilterType::ColorBalance: for (float& p : plan.params) p = pick(-40, 40); break;
        case doc::FilterType::InvertThreshold: plan.params[0] = rng() % 2; plan.params[1] = pick(60, 200); break;
        case doc::FilterType::HueSat: plan.params[0] = pick(-180, 180); plan.params[1] = pick(-50, 50); plan.params[2] = pick(-30, 30); break;
        case doc::FilterType::Pixelate: plan.params[0] = pick(4, 20); break;
        case doc::FilterType::GaussianBlur: plan.params[0] = pick(2, 12); break;
        case doc::FilterType::SharpenVignette: plan.params[0] = pick(10, 80); plan.params[1] = pick(0, 60); plan.params[2] = pick(30, 80); break;
    }
    return plan;
}

inline std::vector<LayerPlan> filtersPlan(std::mt19937& rng, doc::FilterType type) {
    std::vector<LayerPlan> plan{base(rng), paint(rng, doc::LayerBlendMode::Normal, 1.0, false)};
    plan.push_back(filterPlan(type, rng));
    plan.push_back(paint(rng, doc::LayerBlendMode::Normal, randomOpacity(rng), false));
    return plan;
}

// ─── composing and comparing ─────────────────────────────────────────────────

struct Spread {
    int worst{0};
    long long channels{0};
    long long differing{0};
    long long beyondFour{0};  // channels more than 4 levels apart
    void add(int diff) { worst = std::max(worst, diff); ++channels; differing += diff != 0; beyondFour += diff > 4; }
    void merge(const Spread& other) {
        worst = std::max(worst, other.worst);
        channels += other.channels;
        differing += other.differing;
        beyondFour += other.beyondFour;
    }
    [[nodiscard]] double percent() const { return channels ? 100.0 * static_cast<double>(differing) / static_cast<double>(channels) : 0.0; }
    [[nodiscard]] double percentBeyondFour() const { return channels ? 100.0 * static_cast<double>(beyondFour) / static_cast<double>(channels) : 0.0; }
};

struct Composed {
    aladyn::engine::canvas::PixelBuffer screen;
    std::unique_ptr<doc::Compositor> compositor;
};

inline Composed compose(doc::LayerStack& stack, bool linear, bool deep) {
    auto compositor = std::make_unique<doc::Compositor>(kWidth, kHeight, stack.getPixelFormat());
    compositor->setLinearGamma(linear);
    compositor->setDeepColor(deep);
    aladyn::engine::canvas::PixelBuffer screen(kWidth, kHeight, kBackground);
    compositor->composite(stack.getAllLayersForComposition(), screen, kBackground);
    return Composed{std::move(screen), std::move(compositor)};
}

inline void spreadOfScreens(const aladyn::engine::canvas::PixelBuffer& a, const aladyn::engine::canvas::PixelBuffer& b, Spread& spread) {
    for (int y = 0; y < kHeight; ++y) {
        for (int x = 0; x < kWidth; ++x) {
            const ColorRGBA p = a.getPixel(x, y), q = b.getPixel(x, y);
            spread.add(std::abs(p.r - q.r));
            spread.add(std::abs(p.g - q.g));
            spread.add(std::abs(p.b - q.b));
            spread.add(std::abs(p.a - q.a));
        }
    }
}

} // namespace scene16

#endif // ALADYN_TESTS_NATIVE_COMPOSITOR16_SCENE_HPP
