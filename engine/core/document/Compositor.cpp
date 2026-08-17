#include "Compositor.hpp"
#include "FilterLayer.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::document {

static void rgbToHsv(float r, float g, float b, float& h, float& s, float& v) {
    float minVal = std::min({r, g, b});
    float maxVal = std::max({r, g, b});
    float delta = maxVal - minVal;
    v = maxVal;
    if (maxVal == 0.0f || delta == 0.0f) {
        s = 0.0f;
        h = 0.0f;
        return;
    }
    s = delta / maxVal;
    if (r == maxVal) h = (g - b) / delta;
    else if (g == maxVal) h = 2.0f + (b - r) / delta;
    else h = 4.0f + (r - g) / delta;
    h *= 60.0f;
    if (h < 0.0f) h += 360.0f;
}

static void hsvToRgb(float h, float s, float v, float& r, float& g, float& b) {
    if (s == 0.0f) {
        r = g = b = v;
        return;
    }
    h = std::fmod(h, 360.0f);
    if (h < 0.0f) h += 360.0f;
    float c = v * s;
    float x = c * (1.0f - std::abs(std::fmod(h / 60.0f, 2.0f) - 1.0f));
    float m = v - c;
    float r1 = 0, g1 = 0, b1 = 0;
    if (h < 60.0f) { r1 = c; g1 = x; b1 = 0; }
    else if (h < 120.0f) { r1 = x; g1 = c; b1 = 0; }
    else if (h < 180.0f) { r1 = 0; g1 = c; b1 = x; }
    else if (h < 240.0f) { r1 = 0; g1 = x; b1 = c; }
    else if (h < 300.0f) { r1 = x; g1 = 0; b1 = c; }
    else { r1 = c; g1 = 0; b1 = x; }
    r = r1 + m;
    g = g1 + m;
    b = b1 + m;
}

static void applyFilterToBuffer(const FilterLayer& filter, canvas::PixelBuffer& buffer, int minX = 0, int maxX = -1, int minY = 0, int maxY = -1) {
    const double opacity = filter.getEffectiveOpacity();
    if (opacity <= 0.0) return;

    const FilterType type = filter.getFilterType();
    const int w = buffer.getWidth();
    const int h = buffer.getHeight();

    int startX = std::max(0, minX);
    int endX   = (maxX < 0) ? (w - 1) : std::min(w - 1, maxX);
    int startY = std::max(0, minY);
    int endY   = (maxY < 0) ? (h - 1) : std::min(h - 1, maxY);

    if (startX > endX || startY > endY) return;

    uint8_t* ptr = buffer.getData();
    const size_t totalPixels = static_cast<size_t>(w * h);

    if (type == FilterType::HueSat) {
        const float hueShift = filter.getParam(0, 0.0f);
        const float satDelta = filter.getParam(1, 0.0f) / 100.0f;
        const float lightDelta = filter.getParam(2, 0.0f) / 100.0f;
        const bool colorize = filter.getParam(3, 0.0f) > 0.5f;

        for (int y = startY; y <= endY; ++y) {
            for (int x = startX; x <= endX; ++x) {
                size_t i = static_cast<size_t>(y * w + x);
                uint8_t a = ptr[i * 4 + 3];
                if (a == 0) continue;

                float r = ptr[i * 4 + 0] / 255.0f;
                float g = ptr[i * 4 + 1] / 255.0f;
                float b = ptr[i * 4 + 2] / 255.0f;

                float fh, fs, fv;
                rgbToHsv(r, g, b, fh, fs, fv);

                if (colorize) {
                    fh = std::fmod(std::abs(hueShift), 360.0f);
                    fs = std::clamp(0.5f + satDelta, 0.0f, 1.0f);
                } else {
                    fh = std::fmod(fh + hueShift + 360.0f, 360.0f);
                    fs = std::clamp(fs + satDelta, 0.0f, 1.0f);
                }
                fv = std::clamp(fv + lightDelta, 0.0f, 1.0f);

                float outR, outG, outB;
                hsvToRgb(fh, fs, fv, outR, outG, outB);

                uint8_t finalR = static_cast<uint8_t>(std::clamp(outR * 255.0f, 0.0f, 255.0f));
                uint8_t finalG = static_cast<uint8_t>(std::clamp(outG * 255.0f, 0.0f, 255.0f));
                uint8_t finalB = static_cast<uint8_t>(std::clamp(outB * 255.0f, 0.0f, 255.0f));

                if (opacity < 1.0) {
                    ptr[i * 4 + 0] = static_cast<uint8_t>(ptr[i * 4 + 0] * (1.0 - opacity) + finalR * opacity);
                    ptr[i * 4 + 1] = static_cast<uint8_t>(ptr[i * 4 + 1] * (1.0 - opacity) + finalG * opacity);
                    ptr[i * 4 + 2] = static_cast<uint8_t>(ptr[i * 4 + 2] * (1.0 - opacity) + finalB * opacity);
                } else {
                    ptr[i * 4 + 0] = finalR;
                    ptr[i * 4 + 1] = finalG;
                    ptr[i * 4 + 2] = finalB;
                }
            }
        }
    } else if (type == FilterType::BrightnessContrast) {
        const float bright = filter.getParam(0, 0.0f) / 100.0f;
        const float contrast = filter.getParam(1, 0.0f) / 100.0f;
        const float gamma = std::max(0.1f, filter.getParam(2, 1.0f));
        const float contrastFactor = contrast + 1.0f;

        for (int y = startY; y <= endY; ++y) {
            for (int x = startX; x <= endX; ++x) {
                size_t i = static_cast<size_t>(y * w + x);
                uint8_t a = ptr[i * 4 + 3];
                if (a == 0) continue;

                float r = ptr[i * 4 + 0] / 255.0f + bright;
                float g = ptr[i * 4 + 1] / 255.0f + bright;
                float b = ptr[i * 4 + 2] / 255.0f + bright;

                r = (r - 0.5f) * contrastFactor + 0.5f;
                g = (g - 0.5f) * contrastFactor + 0.5f;
                b = (b - 0.5f) * contrastFactor + 0.5f;

                if (gamma != 1.0f) {
                    r = std::pow(std::clamp(r, 0.0f, 1.0f), 1.0f / gamma);
                    g = std::pow(std::clamp(g, 0.0f, 1.0f), 1.0f / gamma);
                    b = std::pow(std::clamp(b, 0.0f, 1.0f), 1.0f / gamma);
                }

                uint8_t finalR = static_cast<uint8_t>(std::clamp(r * 255.0f, 0.0f, 255.0f));
                uint8_t finalG = static_cast<uint8_t>(std::clamp(g * 255.0f, 0.0f, 255.0f));
                uint8_t finalB = static_cast<uint8_t>(std::clamp(b * 255.0f, 0.0f, 255.0f));

                if (opacity < 1.0) {
                    ptr[i * 4 + 0] = static_cast<uint8_t>(ptr[i * 4 + 0] * (1.0 - opacity) + finalR * opacity);
                    ptr[i * 4 + 1] = static_cast<uint8_t>(ptr[i * 4 + 1] * (1.0 - opacity) + finalG * opacity);
                    ptr[i * 4 + 2] = static_cast<uint8_t>(ptr[i * 4 + 2] * (1.0 - opacity) + finalB * opacity);
                } else {
                    ptr[i * 4 + 0] = finalR;
                    ptr[i * 4 + 1] = finalG;
                    ptr[i * 4 + 2] = finalB;
                }
            }
        }
    } else if (type == FilterType::InvertThreshold) {
        const bool isInvert = filter.getParam(0, 1.0f) > 0.5f;
        const float threshold = filter.getParam(1, 128.0f);

        for (int y = startY; y <= endY; ++y) {
            for (int x = startX; x <= endX; ++x) {
                size_t i = static_cast<size_t>(y * w + x);
                uint8_t a = ptr[i * 4 + 3];
                if (a == 0) continue;

                uint8_t r = ptr[i * 4 + 0];
                uint8_t g = ptr[i * 4 + 1];
                uint8_t b = ptr[i * 4 + 2];

                uint8_t finalR, finalG, finalB;
                if (isInvert) {
                    finalR = 255 - r;
                    finalG = 255 - g;
                    finalB = 255 - b;
                } else {
                    float lum = 0.299f * r + 0.587f * g + 0.114f * b;
                    uint8_t v = (lum >= threshold) ? 255 : 0;
                    finalR = finalG = finalB = v;
                }

                if (opacity < 1.0) {
                    ptr[i * 4 + 0] = static_cast<uint8_t>(r * (1.0 - opacity) + finalR * opacity);
                    ptr[i * 4 + 1] = static_cast<uint8_t>(g * (1.0 - opacity) + finalG * opacity);
                    ptr[i * 4 + 2] = static_cast<uint8_t>(b * (1.0 - opacity) + finalB * opacity);
                } else {
                    ptr[i * 4 + 0] = finalR;
                    ptr[i * 4 + 1] = finalG;
                    ptr[i * 4 + 2] = finalB;
                }
            }
        }
    } else if (type == FilterType::ColorBalance) {
        const float rShift = filter.getParam(0, 0.0f) * 2.55f;
        const float gShift = filter.getParam(1, 0.0f) * 2.55f;
        const float bShift = filter.getParam(2, 0.0f) * 2.55f;

        for (int y = startY; y <= endY; ++y) {
            for (int x = startX; x <= endX; ++x) {
                size_t i = static_cast<size_t>(y * w + x);
                uint8_t a = ptr[i * 4 + 3];
                if (a == 0) continue;

                uint8_t r = ptr[i * 4 + 0];
                uint8_t g = ptr[i * 4 + 1];
                uint8_t b = ptr[i * 4 + 2];

                uint8_t finalR = static_cast<uint8_t>(std::clamp(r + rShift, 0.0f, 255.0f));
                uint8_t finalG = static_cast<uint8_t>(std::clamp(g + gShift, 0.0f, 255.0f));
                uint8_t finalB = static_cast<uint8_t>(std::clamp(b + bShift, 0.0f, 255.0f));

                if (opacity < 1.0) {
                    ptr[i * 4 + 0] = static_cast<uint8_t>(r * (1.0 - opacity) + finalR * opacity);
                    ptr[i * 4 + 1] = static_cast<uint8_t>(g * (1.0 - opacity) + finalG * opacity);
                    ptr[i * 4 + 2] = static_cast<uint8_t>(b * (1.0 - opacity) + finalB * opacity);
                } else {
                    ptr[i * 4 + 0] = finalR;
                    ptr[i * 4 + 1] = finalG;
                    ptr[i * 4 + 2] = finalB;
                }
            }
        }
    } else if (type == FilterType::Pixelate) {
        const int blockSize = std::clamp(static_cast<int>(filter.getParam(0, 8.0f)), 2, 64);
        std::vector<uint8_t> origBuffer(ptr, ptr + totalPixels * 4);

        int alignStartY = (startY / blockSize) * blockSize;
        int alignEndY   = std::min(h - 1, ((endY / blockSize) + 1) * blockSize - 1);
        int alignStartX = (startX / blockSize) * blockSize;
        int alignEndX   = std::min(w - 1, ((endX / blockSize) + 1) * blockSize - 1);

        for (int y = alignStartY; y <= alignEndY; y += blockSize) {
            for (int x = alignStartX; x <= alignEndX; x += blockSize) {
                int sampleX = std::min(x + blockSize / 2, w - 1);
                int sampleY = std::min(y + blockSize / 2, h - 1);
                size_t sampleIdx = static_cast<size_t>(sampleY * w + sampleX);

                uint8_t sr = origBuffer[sampleIdx * 4 + 0];
                uint8_t sg = origBuffer[sampleIdx * 4 + 1];
                uint8_t sb = origBuffer[sampleIdx * 4 + 2];
                uint8_t sa = origBuffer[sampleIdx * 4 + 3];

                if (sa == 0) continue;

                int blockMaxY = std::min(y + blockSize, h);
                int blockMaxX = std::min(x + blockSize, w);

                for (int by = y; by < blockMaxY; ++by) {
                    for (int bx = x; bx < blockMaxX; ++bx) {
                        size_t pxIdx = static_cast<size_t>(by * w + bx);
                        uint8_t a = ptr[pxIdx * 4 + 3];
                        if (a == 0) continue;

                        if (opacity < 1.0) {
                            ptr[pxIdx * 4 + 0] = static_cast<uint8_t>(ptr[pxIdx * 4 + 0] * (1.0 - opacity) + sr * opacity);
                            ptr[pxIdx * 4 + 1] = static_cast<uint8_t>(ptr[pxIdx * 4 + 1] * (1.0 - opacity) + sg * opacity);
                            ptr[pxIdx * 4 + 2] = static_cast<uint8_t>(ptr[pxIdx * 4 + 2] * (1.0 - opacity) + sb * opacity);
                        } else {
                            ptr[pxIdx * 4 + 0] = sr;
                            ptr[pxIdx * 4 + 1] = sg;
                            ptr[pxIdx * 4 + 2] = sb;
                        }
                    }
                }
            }
        }
    }
}

Compositor::Compositor(int width, int height)
    : m_width(width), m_height(height) {}

raster::ColorRGBA Compositor::blendPixel(
    raster::ColorRGBA src,
    double layerOpacity,
    raster::ColorRGBA dst,
    LayerBlendMode mode
) {
    if (src.a == 0) return dst;

    if (mode == LayerBlendMode::Normal && layerOpacity == 1.0) {
        if (src.a == 255) return src;
        if (dst.a == 255) {
            const uint32_t sA = src.a;
            const uint32_t invA = 255 - sA;
            return raster::ColorRGBA{
                static_cast<uint8_t>((src.r * sA + dst.r * invA) / 255),
                static_cast<uint8_t>((src.g * sA + dst.g * invA) / 255),
                static_cast<uint8_t>((src.b * sA + dst.b * invA) / 255),
                255
            };
        }
    }

    const double srcA = (static_cast<double>(src.a) / 255.0) * layerOpacity;
    if (srcA <= 0.0) return dst;

    if (mode == LayerBlendMode::Erase) {
        const double dstA = static_cast<double>(dst.a) / 255.0;
        const double newA = std::max(0.0, dstA * (1.0 - srcA));
        return raster::ColorRGBA{dst.r, dst.g, dst.b, static_cast<uint8_t>(std::clamp(newA * 255.0, 0.0, 255.0))};
    }

    const double dstA = static_cast<double>(dst.a) / 255.0;
    const double outA = srcA + dstA * (1.0 - srcA);
    if (outA <= 0.0) return raster::ColorRGBA{0, 0, 0, 0};

    const double sR = static_cast<double>(src.r) / 255.0;
    const double sG = static_cast<double>(src.g) / 255.0;
    const double sB = static_cast<double>(src.b) / 255.0;

    const double dR = static_cast<double>(dst.r) / 255.0;
    const double dG = static_cast<double>(dst.g) / 255.0;
    const double dB = static_cast<double>(dst.b) / 255.0;

    double blendR = sR, blendG = sG, blendB = sB;

    switch (mode) {
        case LayerBlendMode::Multiply:
            blendR = sR * dR;
            blendG = sG * dG;
            blendB = sB * dB;
            break;
        case LayerBlendMode::Screen:
            blendR = 1.0 - (1.0 - sR) * (1.0 - dR);
            blendG = 1.0 - (1.0 - sG) * (1.0 - dG);
            blendB = 1.0 - (1.0 - sB) * (1.0 - dB);
            break;
        case LayerBlendMode::Overlay:
            blendR = (dR < 0.5) ? (2.0 * dR * sR) : (1.0 - 2.0 * (1.0 - dR) * (1.0 - sR));
            blendG = (dG < 0.5) ? (2.0 * dG * sG) : (1.0 - 2.0 * (1.0 - dG) * (1.0 - sG));
            blendB = (dB < 0.5) ? (2.0 * dB * sB) : (1.0 - 2.0 * (1.0 - dB) * (1.0 - sB));
            break;
        case LayerBlendMode::Darken:
            blendR = std::min(sR, dR);
            blendG = std::min(sG, dG);
            blendB = std::min(sB, dB);
            break;
        case LayerBlendMode::Lighten:
            blendR = std::max(sR, dR);
            blendG = std::max(sG, dG);
            blendB = std::max(sB, dB);
            break;
        case LayerBlendMode::ColorDodge:
            blendR = std::min(1.0, dR / (1.0 - sR + 1e-5));
            blendG = std::min(1.0, dG / (1.0 - sG + 1e-5));
            blendB = std::min(1.0, dB / (1.0 - sB + 1e-5));
            break;
        case LayerBlendMode::ColorBurn:
            blendR = 1.0 - std::min(1.0, (1.0 - dR) / (sR + 1e-5));
            blendG = 1.0 - std::min(1.0, (1.0 - dG) / (sG + 1e-5));
            blendB = 1.0 - std::min(1.0, (1.0 - dB) / (sB + 1e-5));
            break;
        case LayerBlendMode::Difference:
            blendR = std::abs(dR - sR);
            blendG = std::abs(dG - sG);
            blendB = std::abs(dB - sB);
            break;
        case LayerBlendMode::Exclusion:
            blendR = dR + sR - 2.0 * dR * sR;
            blendG = dG + sG - 2.0 * dG * sG;
            blendB = dB + sB - 2.0 * dB * sB;
            break;
        case LayerBlendMode::Add:
            blendR = std::min(1.0, dR + sR);
            blendG = std::min(1.0, dG + sG);
            blendB = std::min(1.0, dB + sB);
            break;
        case LayerBlendMode::Normal:
        default:
            blendR = sR; blendG = sG; blendB = sB;
            break;
    }

    // Interpolação Alpha Over com blend mode ativado
    const double outR = (blendR * srcA + dR * dstA * (1.0 - srcA)) / outA;
    const double outG = (blendG * srcA + dG * dstA * (1.0 - srcA)) / outA;
    const double outB = (blendB * srcA + dB * dstA * (1.0 - srcA)) / outA;

    return raster::ColorRGBA{
        static_cast<uint8_t>(std::clamp(outR * 255.0, 0.0, 255.0)),
        static_cast<uint8_t>(std::clamp(outG * 255.0, 0.0, 255.0)),
        static_cast<uint8_t>(std::clamp(outB * 255.0, 0.0, 255.0)),
        static_cast<uint8_t>(std::clamp(outA * 255.0, 0.0, 255.0))
    };
}

void Compositor::composite(const std::vector<const Layer*>& layers, canvas::PixelBuffer& outputBuffer, const raster::ColorRGBA& bgColor) {
    bool hasBackground = false;
    for (const Layer* l : layers) {
        if (l && l->isBackground() && l->isVisible()) {
            hasBackground = true;
            break;
        }
    }

    if (hasBackground) {
        outputBuffer.fill(bgColor);
    } else {
        outputBuffer.fill({0, 0, 0, 0});
    }

    for (const Layer* layerPtr : layers) {
        if (!layerPtr || !layerPtr->isVisible() || layerPtr->getEffectiveOpacity() <= 0.0) {
            continue;
        }

        if (layerPtr->isFilter()) {
            const FilterLayer* filterLayer = dynamic_cast<const FilterLayer*>(layerPtr);
            if (filterLayer) {
                applyFilterToBuffer(*filterLayer, outputBuffer);
            }
            continue;
        }

        const Layer& layer = *layerPtr;
        const double layerOpacity = layer.getEffectiveOpacity();
        const LayerBlendMode blendMode = layer.getBlendMode();
        const canvas::TileGrid& grid = layer.getTileGrid();

        // Suporte a Clipping Mask (Máscara de Recorte)
        const Layer* clipBaseLayer = nullptr;
        if (layer.isClippingMask()) {
            auto it = std::find(layers.begin(), layers.end(), layerPtr);
            if (it != layers.begin()) {
                for (auto prevIt = it - 1; ; --prevIt) {
                    if (*prevIt && !(*prevIt)->isBackground() && !(*prevIt)->isClippingMask() && (*prevIt)->isVisible()) {
                        clipBaseLayer = *prevIt;
                        break;
                    }
                    if (prevIt == layers.begin()) break;
                }
            }
        }

        const int tilesX = grid.getTilesCountX();
        const int tilesY = grid.getTilesCountY();

        for (int ty = 0; ty < tilesY; ++ty) {
            for (int tx = 0; tx < tilesX; ++tx) {
                const canvas::Tile* tile = const_cast<canvas::TileGrid&>(grid).getTile(tx, ty);
                if (!tile) continue;

                const canvas::PixelBuffer& tileBuf = tile->getBuffer();
                const int tilePixelX = tile->getPixelX();
                const int tilePixelY = tile->getPixelY();

                for (int py = 0; py < canvas::Tile::TILE_SIZE; ++py) {
                    const int globalY = tilePixelY + py;
                    if (globalY >= m_height) break;

                    for (int px = 0; px < canvas::Tile::TILE_SIZE; ++px) {
                        const int globalX = tilePixelX + px;
                        if (globalX >= m_width) break;

                        const raster::ColorRGBA src = tileBuf.getPixel(px, py);
                        if (src.a == 0) continue;

                        double curOpacity = layerOpacity;
                        if (clipBaseLayer) {
                            const int bTx = globalX / canvas::Tile::TILE_SIZE;
                            const int bTy = globalY / canvas::Tile::TILE_SIZE;
                            const int bPx = globalX % canvas::Tile::TILE_SIZE;
                            const int bPy = globalY % canvas::Tile::TILE_SIZE;
                            const canvas::Tile* bTile = const_cast<canvas::TileGrid&>(clipBaseLayer->getTileGrid()).getTile(bTx, bTy);
                            if (!bTile) continue;
                            const double baseA = static_cast<double>(bTile->getBuffer().getPixel(bPx, bPy).a) / 255.0;
                            if (baseA <= 0.0) continue;
                            curOpacity *= baseA;
                        }

                        const raster::ColorRGBA dst = outputBuffer.getPixel(globalX, globalY);
                        const raster::ColorRGBA blended = blendPixel(src, curOpacity, dst, blendMode);

                        outputBuffer.setPixel(globalX, globalY, blended);
                    }
                }
            }
        }
    }
}

void Compositor::composite(const std::vector<std::unique_ptr<Layer>>& layers, canvas::PixelBuffer& outputBuffer, const raster::ColorRGBA& bgColor) {
    std::vector<const Layer*> rawPtrs;
    rawPtrs.reserve(layers.size());
    for (const auto& l : layers) {
        if (l) rawPtrs.push_back(l.get());
    }
    composite(rawPtrs, outputBuffer, bgColor);
}

void Compositor::compositeRegion(
    const std::vector<const Layer*>& layers,
    const math::Rect2D& region,
    canvas::PixelBuffer& outputBuffer,
    const raster::ColorRGBA& bgColor
) {
    if (layers.empty()) return;

    bool hasBackground = false;
    for (const Layer* l : layers) {
        if (l && l->isBackground() && l->isVisible()) {
            hasBackground = true;
            break;
        }
    }

    const raster::ColorRGBA bgFill = hasBackground ? bgColor : raster::ColorRGBA{0, 0, 0, 0};

    const int minX = std::max(0, static_cast<int>(std::floor(region.getLeft())) - 2);
    const int maxX = std::min(m_width - 1, static_cast<int>(std::ceil(region.getRight())) + 2);
    const int minY = std::max(0, static_cast<int>(std::floor(region.getTop())) - 2);
    const int maxY = std::min(m_height - 1, static_cast<int>(std::ceil(region.getBottom())) + 2);

    if (minX > maxX || minY > maxY) return;

    const int startTileX = minX / canvas::Tile::TILE_SIZE;
    const int endTileX   = maxX / canvas::Tile::TILE_SIZE;
    const int startTileY = minY / canvas::Tile::TILE_SIZE;
    const int endTileY   = maxY / canvas::Tile::TILE_SIZE;

    // Reseta a área APENAS na bounding box da região afetada
    for (int y = minY; y <= maxY; ++y) {
        for (int x = minX; x <= maxX; ++x) {
            outputBuffer.setPixel(x, y, bgFill);
        }
    }

    for (const Layer* layerPtr : layers) {
        if (!layerPtr || !layerPtr->isVisible() || layerPtr->getOpacity() <= 0.0) {
            continue;
        }

        if (layerPtr->isFilter()) {
            const FilterLayer* filterLayer = dynamic_cast<const FilterLayer*>(layerPtr);
            if (filterLayer) {
                applyFilterToBuffer(*filterLayer, outputBuffer, minX, maxX, minY, maxY);
            }
            continue;
        }

        const Layer& layer = *layerPtr;
        const double layerOpacity = layer.getOpacity();
        const LayerBlendMode blendMode = layer.getBlendMode();
        const canvas::TileGrid& grid = layer.getTileGrid();

        // Suporte a Clipping Mask (Máscara de Recorte)
        const Layer* clipBaseLayer = nullptr;
        if (layer.isClippingMask()) {
            auto it = std::find(layers.begin(), layers.end(), layerPtr);
            if (it != layers.begin()) {
                for (auto prevIt = it - 1; ; --prevIt) {
                    if (*prevIt && !(*prevIt)->isBackground() && !(*prevIt)->isClippingMask() && (*prevIt)->isVisible()) {
                        clipBaseLayer = *prevIt;
                        break;
                    }
                    if (prevIt == layers.begin()) break;
                }
            }
        }

        const int maxTilesX = grid.getTilesCountX();
        const int maxTilesY = grid.getTilesCountY();

        const int clampStartTx = std::clamp(startTileX, 0, maxTilesX - 1);
        const int clampEndTx   = std::clamp(endTileX, 0, maxTilesX - 1);
        const int clampStartTy = std::clamp(startTileY, 0, maxTilesY - 1);
        const int clampEndTy   = std::clamp(endTileY, 0, maxTilesY - 1);

        for (int ty = clampStartTy; ty <= clampEndTy; ++ty) {
            for (int tx = clampStartTx; tx <= clampEndTx; ++tx) {
                const canvas::Tile* tile = const_cast<canvas::TileGrid&>(grid).getTile(tx, ty);
                if (!tile) continue;

                const canvas::PixelBuffer& tileBuf = tile->getBuffer();
                const int tilePixelX = tile->getPixelX();
                const int tilePixelY = tile->getPixelY();

                const int tileMinX = std::max(minX, tilePixelX);
                const int tileMaxX = std::min(maxX, tilePixelX + canvas::Tile::TILE_SIZE - 1);
                const int tileMinY = std::max(minY, tilePixelY);
                const int tileMaxY = std::min(maxY, tilePixelY + canvas::Tile::TILE_SIZE - 1);

                for (int globalY = tileMinY; globalY <= tileMaxY; ++globalY) {
                    const int localY = globalY - tilePixelY;

                    for (int globalX = tileMinX; globalX <= tileMaxX; ++globalX) {
                        const int localX = globalX - tilePixelX;

                        const raster::ColorRGBA src = tileBuf.getPixel(localX, localY);
                        if (src.a == 0) continue;

                        double curOpacity = layerOpacity;
                        if (clipBaseLayer) {
                            const int bTx = globalX / canvas::Tile::TILE_SIZE;
                            const int bTy = globalY / canvas::Tile::TILE_SIZE;
                            const int bPx = globalX % canvas::Tile::TILE_SIZE;
                            const int bPy = globalY % canvas::Tile::TILE_SIZE;
                            const canvas::Tile* bTile = const_cast<canvas::TileGrid&>(clipBaseLayer->getTileGrid()).getTile(bTx, bTy);
                            if (!bTile) continue;
                            const double baseA = static_cast<double>(bTile->getBuffer().getPixel(bPx, bPy).a) / 255.0;
                            if (baseA <= 0.0) continue;
                            curOpacity *= baseA;
                        }

                        const raster::ColorRGBA dst = outputBuffer.getPixel(globalX, globalY);
                        const raster::ColorRGBA blended = blendPixel(src, curOpacity, dst, blendMode);

                        outputBuffer.setPixel(globalX, globalY, blended);
                    }
                }
            }
        }
    }
}

void Compositor::compositeRegion(
    const std::vector<std::unique_ptr<Layer>>& layers,
    const math::Rect2D& region,
    canvas::PixelBuffer& outputBuffer,
    const raster::ColorRGBA& bgColor
) {
    std::vector<const Layer*> rawPtrs;
    rawPtrs.reserve(layers.size());
    for (const auto& l : layers) {
        if (l) rawPtrs.push_back(l.get());
    }
    compositeRegion(rawPtrs, region, outputBuffer, bgColor);
}

} // namespace aladyn::engine::document
