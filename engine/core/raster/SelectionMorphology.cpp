// Seleção -> Modificar. Ver SelectionMorphology.hpp para o porquê de cada escolha.
#include "SelectionMorphology.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <limits>
#include <vector>

namespace aladyn::engine::raster::SelectionMorphology {
namespace {

struct Roi {
    int x0, y0, x1, y1;  // [x0, x1) x [y0, y1)
    [[nodiscard]] int w() const noexcept { return x1 - x0; }
    [[nodiscard]] int h() const noexcept { return y1 - y0; }
};

Roi roiAround(const SelectionMask& mask, int margin) {
    const auto b = mask.getBounds();
    const int bx = static_cast<int>(b.x), by = static_cast<int>(b.y);
    const int bw = static_cast<int>(b.width), bh = static_cast<int>(b.height);
    return Roi{std::max(0, bx - margin), std::max(0, by - margin),
               std::min(mask.getWidth(), bx + bw + margin), std::min(mask.getHeight(), by + bh + margin)};
}

// ── Transformada de distância ────────────────────────────────────────────

constexpr uint16_t kNoSource = std::numeric_limits<uint16_t>::max();
constexpr double kInf = std::numeric_limits<double>::infinity();

// Envelope inferior de parábolas (1D). f[i] = distância² já conhecida em i.
void edt1d(const std::vector<double>& f, std::vector<double>& out,
           std::vector<int>& v, std::vector<double>& z) {
    const int n = static_cast<int>(f.size());
    int k = 0;
    v[0] = 0;
    z[0] = -kInf;
    z[1] = kInf;
    for (int q = 1; q < n; ++q) {
        double s;
        while (true) {
            const int p = v[k];
            s = ((f[q] + double(q) * q) - (f[p] + double(p) * p)) / (2.0 * q - 2.0 * p);
            if (s > z[k]) break;
            --k;
        }
        ++k;
        v[k] = q;
        z[k] = s;
        z[k + 1] = kInf;
    }
    k = 0;
    for (int q = 0; q < n; ++q) {
        while (z[k + 1] < q) ++k;
        const double dq = double(q - v[k]);
        out[q] = dq * dq + f[v[k]];
    }
}

// Chama fn(x, y, d) para cada pixel do ROI, com d = distância euclidiana (em
// pixels, centro a centro) até o pixel-fonte mais próximo dentro do ROI.
// Fonte = selecionado (>= 128) se fonteSelecionada, senão não selecionado.
template <class Fn>
void scanDistances(const SelectionMask& mask, const Roi& r, bool sourceIsSelected, Fn&& fn) {
    const int W = mask.getWidth();
    const uint8_t* pixels = mask.getData();
    const int rw = r.w(), rh = r.h();
    std::vector<uint16_t> g(static_cast<size_t>(rw) * rh, kNoSource);

    // 1) Coluna a coluna: distância vertical exata (duas varreduras lineares).
    for (int x = 0; x < rw; ++x) {
        int dist = kNoSource;
        for (int y = 0; y < rh; ++y) {
            const bool sel = pixels[static_cast<size_t>(r.y0 + y) * W + (r.x0 + x)] >= 128;
            if (sel == sourceIsSelected) dist = 0;
            else if (dist < kNoSource - 1) ++dist;
            g[static_cast<size_t>(y) * rw + x] = static_cast<uint16_t>(dist);
        }
        dist = kNoSource;
        for (int y = rh - 1; y >= 0; --y) {
            uint16_t& cell = g[static_cast<size_t>(y) * rw + x];
            if (cell == 0) dist = 0;
            else if (dist < kNoSource - 1) ++dist;
            if (dist < cell) cell = static_cast<uint16_t>(dist);
        }
    }

    // 2) Linha a linha: envelope de parábolas sobre g².
    std::vector<double> f(rw), d2(rw), z(rw + 1);
    std::vector<int> v(rw);
    for (int y = 0; y < rh; ++y) {
        for (int x = 0; x < rw; ++x) {
            const double gv = g[static_cast<size_t>(y) * rw + x];
            f[x] = gv * gv;
        }
        edt1d(f, d2, v, z);
        for (int x = 0; x < rw; ++x) fn(r.x0 + x, r.y0 + y, std::sqrt(d2[x]));
    }
}

uint8_t toByte(double coverage) {
    return static_cast<uint8_t>(std::lround(std::clamp(coverage, 0.0, 1.0) * 255.0));
}

// ── Desfoque separável com a regra de borda da seleção ───────────────────

// Uma linha (ou coluna) do ROI: [lo, hi) dentro da tela [0, n). Fora da tela
// repete o pixel da borda; dentro da tela e fora do ROI vale 0 (sem seleção).
struct Row {
    const float* v;
    int lo, hi, n;
    [[nodiscard]] float em(int i) const noexcept {
        const int c = std::clamp(i, 0, n - 1);
        return (c < lo || c >= hi) ? 0.0f : v[c - lo];
    }
};

void boxPass(const Row& in, float* out, int radius) {
    const int len = in.hi - in.lo;
    if (radius <= 0) {
        std::copy(in.v, in.v + len, out);
        return;
    }
    double sum = 0.0;
    for (int k = -radius; k <= radius; ++k) sum += in.em(in.lo + k);
    const double inv = 1.0 / (2.0 * radius + 1.0);
    for (int j = 0; j < len; ++j) {
        out[j] = static_cast<float>(sum * inv);
        const int i = in.lo + j;
        sum += double(in.em(i + radius + 1)) - double(in.em(i - radius));
    }
}

void kernelPass(const Row& in, float* out, const std::vector<float>& kernel) {
    const int len = in.hi - in.lo;
    const int R = static_cast<int>(kernel.size() / 2);
    for (int j = 0; j < len; ++j) {
        double s = 0.0;
        for (int t = -R; t <= R; ++t) s += kernel[t + R] * in.em(in.lo + j + t);
        out[j] = static_cast<float>(s);
    }
}

// Raios das 3 caixas que aproximam uma gaussiana de desvio sigma.
std::array<int, 3> boxRadii(double sigma) {
    constexpr int n = 3;
    const double wIdeal = std::sqrt(12.0 * sigma * sigma / n + 1.0);
    int wl = static_cast<int>(std::floor(wIdeal));
    if (wl % 2 == 0) --wl;
    const int wu = wl + 2;
    const double mIdeal = (12.0 * sigma * sigma - n * wl * wl - 4.0 * n * wl - 3.0 * n) / (-4.0 * wl - 4.0);
    const int m = static_cast<int>(std::lround(mIdeal));
    std::array<int, 3> radii{};
    for (int i = 0; i < n; ++i) radii[i] = ((i < m ? wl : wu) - 1) / 2;
    return radii;
}

struct BoxBlur {
    bool useKernel{false};
    std::vector<float> kernel;
    std::array<int, 3> boxes{};
    int reach{0};  // quantos px o desfoque espalha para cada lado

    explicit BoxBlur(double sigma) {
        if (sigma < 2.0) {
            useKernel = true;
            const int R = std::max(1, static_cast<int>(std::ceil(3.0 * sigma)));
            kernel.resize(2 * R + 1);
            double sum = 0.0;
            for (int t = -R; t <= R; ++t) sum += kernel[t + R] = static_cast<float>(std::exp(-(t * t) / (2.0 * sigma * sigma)));
            for (auto& k : kernel) k = static_cast<float>(k / sum);
            reach = R;
        } else {
            boxes = boxRadii(sigma);
            reach = boxes[0] + boxes[1] + boxes[2];
        }
    }

    // Aplica na linha: a entrada chega em a (tamanho len), o resultado sai em a.
    void apply(std::vector<float>& a, std::vector<float>& b, int lo, int hi, int n) const {
        if (useKernel) {
            kernelPass(Row{a.data(), lo, hi, n}, b.data(), kernel);
            std::swap(a, b);
            return;
        }
        for (int radius : boxes) {
            boxPass(Row{a.data(), lo, hi, n}, b.data(), radius);
            std::swap(a, b);
        }
    }
};

std::vector<uint8_t> maskCopy(const SelectionMask& mask) {
    return std::vector<uint8_t>(mask.getData(), mask.getData() + mask.getSizeInBytes());
}

} // namespace

bool expand(SelectionMask& mask, int radiusPx) {
    if (!mask.hasSelection() || radiusPx <= 0) return false;
    const int r = std::min(radiusPx, kMaxRadiusPx);
    const int W = mask.getWidth();
    const Roi roi = roiAround(mask, r + 1);
    std::vector<uint8_t> output = maskCopy(mask);
    // Borda original a 0,5 px do centro do pixel-fonte; a nova fica r px além.
    scanDistances(mask, roi, true, [&](int x, int y, double d) {
        uint8_t& px = output[static_cast<size_t>(y) * W + x];
        px = std::max(px, toByte(r + 1.0 - d));
    });
    mask.combine(output, SelectionMode::New);
    return true;
}

bool contract(SelectionMask& mask, int radiusPx) {
    if (!mask.hasSelection() || radiusPx <= 0) return false;
    const int r = std::min(radiusPx, kMaxRadiusPx);
    const int W = mask.getWidth();
    // Anel de 1 px fora dos limites garante as fontes (não selecionado) mais
    // próximas; fora da tela não é fonte, então a borda da tela não contrai.
    const Roi roi = roiAround(mask, 1);
    std::vector<uint8_t> output = maskCopy(mask);
    scanDistances(mask, roi, false, [&](int x, int y, double d) {
        uint8_t& px = output[static_cast<size_t>(y) * W + x];
        px = std::min(px, toByte(d - r));
    });
    mask.combine(output, SelectionMode::New);
    return true;
}

bool feather(SelectionMask& mask, int radiusPx) {
    if (!mask.hasSelection() || radiusPx <= 0) return false;
    const int r = std::min(radiusPx, kMaxRadiusPx);
    const BoxBlur blur(r / 2.0);
    const int W = mask.getWidth(), H = mask.getHeight();
    const Roi roi = roiAround(mask, blur.reach + 1);
    const int rw = roi.w(), rh = roi.h();
    const uint8_t* pixels = mask.getData();

    // Passada horizontal -> buffer intermediário (float, só o ROI).
    std::vector<float> half(static_cast<size_t>(rw) * rh);
    std::vector<float> a(std::max(rw, rh)), b(std::max(rw, rh));
    for (int y = 0; y < rh; ++y) {
        a.resize(rw); b.resize(rw);
        const uint8_t* row = pixels + static_cast<size_t>(roi.y0 + y) * W + roi.x0;
        for (int x = 0; x < rw; ++x) a[x] = row[x];
        blur.apply(a, b, roi.x0, roi.x1, W);
        std::copy(a.begin(), a.begin() + rw, half.begin() + static_cast<size_t>(y) * rw);
    }

    // Passada vertical -> máscara final.
    std::vector<uint8_t> output = maskCopy(mask);
    for (int x = 0; x < rw; ++x) {
        a.resize(rh); b.resize(rh);
        for (int y = 0; y < rh; ++y) a[y] = half[static_cast<size_t>(y) * rw + x];
        blur.apply(a, b, roi.y0, roi.y1, H);
        for (int y = 0; y < rh; ++y) {
            output[static_cast<size_t>(roi.y0 + y) * W + (roi.x0 + x)] =
                static_cast<uint8_t>(std::lround(std::clamp(a[y], 0.0f, 255.0f)));
        }
    }
    mask.combine(output, SelectionMode::New);
    return true;
}

} // namespace aladyn::engine::raster::SelectionMorphology
