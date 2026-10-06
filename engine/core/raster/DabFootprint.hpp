#ifndef ALADYN_ENGINE_DAB_FOOTPRINT_HPP
#define ALADYN_ENGINE_DAB_FOOTPRINT_HPP

#include "../canvas/PixelFormat.hpp"
#include "../canvas/TileGrid.hpp"
#include "../../utils/Dab.hpp"
#include "../../utils/ColorRGBA.hpp"
#include "../../utils/Rect2D.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <vector>

namespace aladyn::engine::raster {

// Um pixel do dab com a geometria já calculada: onde ele está no tile e no canvas, e a posição
// relativa ao centro do dab depois de girar e achatar a ponta.
struct DabPixel {
    int px, py;         // dentro do tile
    int gx, gy;         // no canvas
    double rotX, rotY;  // relativo ao centro, girado pelo ângulo do dab
    double scaledY;     // rotY desachatado pela proporção da ponta
    double distSq;      // rotX² + scaledY²
};

// A proporção da ponta deste carimbo (eixo menor / maior, 1 = redonda): a do mapeador, que parte da ponta do
// perfil e a achata com a pressão e a inclinação da caneta. Até 2026-10-02 os mini-motores liam só a da ponta do
// perfil e esses dois controles só funcionavam no motor padrão.
[[nodiscard]] inline double tipAspect(const utils::Dab& dab) noexcept {
    return std::clamp(dab.aspectRatio, 0.05, 1.0);
}

// ─── A PEGADA DE UM DAB ─────────────────────────────────────────────────────
//
// A parte que os nove motores de pincel repetiam: quais tiles o dab pode tocar, a geometria de cada
// pixel (círculo ou elipse girada) e o laço paralelo sobre os tiles. O motor traz só o que o
// distingue: o `kernel`, que decide a cor de um pixel.
//
//   reach   o raio de influência do dab (o raio dele, ou o ampliado de um motor úmido);
//   aspect  a proporção da ponta, já limitada pelo motor.
//
// O construtor descarta os tiles que o círculo da caixa envolvente não toca e cria os que faltam,
// em série; `forEachPixel` não cria nem remove nada.
class DabFootprint {
public:
    DabFootprint(const utils::Dab& dab, double reach, double aspect, canvas::TileGrid& grid);

    [[nodiscard]] bool empty() const noexcept { return m_tiles.empty(); }

    // A caixa envolvente do dab (a elipse inteira), para quem precisa fotografar a área antes de pintar.
    [[nodiscard]] const utils::Rect2D& bounds() const noexcept { return m_bounds; }

    // Chama `kernel(dst, pixel)` para cada pixel do dab (dentro de reach + 1) e marca como suja
    // cada tile em que o kernel devolveu true ("alterei este pixel"). Os tiles rodam em paralelo
    // a partir de `parallelFromTiles`; o kernel é chamado de várias threads e não pode escrever
    // em estado compartilhado.
    //
    // `Pixel` é o pixel do formato do documento (ColorRGBA, o padrão, ou ColorRGBA16): o kernel recebe `Pixel&`
    // e, num documento de 16 bits, faz a conta em 16 bits (S6). O formato é conferido aqui, antes do laço
    // paralelo, porque uma exceção dentro de uma região OpenMP derruba o processo.
    template <class Pixel = utils::ColorRGBA, class PixelKernel>
    void forEachPixel(int parallelFromTiles, PixelKernel&& kernel) const {
        if (m_format != canvas::PixelTraits<Pixel>::kFormat)
            throw std::logic_error("DabFootprint: the kernel pixel type differs from the layer pixel format");
        const int tileCount = static_cast<int>(m_tiles.size());
        #pragma omp parallel for schedule(static) if(tileCount >= parallelFromTiles)
        for (int t = 0; t < tileCount; ++t) {
            if (paintTile<Pixel>(*m_tiles[t], kernel)) m_tiles[t]->setDirty(true);
        }
    }

private:
    template <class Pixel, class PixelKernel>
    bool paintTile(canvas::Tile& tile, PixelKernel& kernel) const {
        canvas::PixelBuffer& buffer = tile.getBuffer();
        const int tileX = tile.getPixelX();
        const int tileY = tile.getPixelY();
        const int minX = std::max(0, static_cast<int>(std::floor(m_bounds.getLeft())) - tileX);
        const int maxX = std::min(canvas::Tile::TILE_SIZE - 1, static_cast<int>(std::ceil(m_bounds.getRight())) - tileX);
        const int minY = std::max(0, static_cast<int>(std::floor(m_bounds.getTop())) - tileY);
        const int maxY = std::min(canvas::Tile::TILE_SIZE - 1, static_cast<int>(std::ceil(m_bounds.getBottom())) - tileY);

        bool modified = false;
        Pixel* base = buffer.template pixels<Pixel>();
        for (int py = minY; py <= maxY; ++py) {
            const double dy = static_cast<double>(tileY + py) + 0.5 - m_center.y;
            int rowMinX = minX;
            int rowMaxX = maxX;
            if (m_circular && !rowSpan(dy, tileX, minX, maxX, rowMinX, rowMaxX)) continue;

            Pixel* row = base + py * canvas::Tile::TILE_SIZE;
            for (int px = rowMinX; px <= rowMaxX; ++px) {
                const double dx = static_cast<double>(tileX + px) + 0.5 - m_center.x;
                const DabPixel pixel = pixelAt(px, py, tileX + px, tileY + py, dx, dy);
                if (pixel.distSq > m_maxRadiusSq) continue;
                modified |= kernel(row[px], pixel);
            }
        }
        return modified;
    }

    // Numa ponta redonda, os pixels fora do círculo de uma linha não precisam nem ser visitados.
    bool rowSpan(double dy, int tileX, int minX, int maxX, int& rowMinX, int& rowMaxX) const {
        const double dySq = dy * dy;
        if (dySq > m_maxRadiusSq) return false;
        const double dxSpan = std::sqrt(m_maxRadiusSq - dySq);
        rowMinX = std::max(minX, static_cast<int>(std::floor(m_center.x - dxSpan)) - tileX);
        rowMaxX = std::min(maxX, static_cast<int>(std::ceil(m_center.x + dxSpan)) - tileX);
        return rowMinX <= rowMaxX;
    }

    DabPixel pixelAt(int px, int py, int gx, int gy, double dx, double dy) const noexcept {
        if (m_circular) return DabPixel{px, py, gx, gy, dx, dy, dy, dx * dx + dy * dy};
        const double rotX = dx * m_cosA - dy * m_sinA;
        const double rotY = dx * m_sinA + dy * m_cosA;
        const double scaledY = rotY * m_invAspect;
        return DabPixel{px, py, gx, gy, rotX, rotY, scaledY, rotX * rotX + scaledY * scaledY};
    }

    utils::Point2D m_center;
    utils::Rect2D m_bounds;
    std::vector<canvas::Tile*> m_tiles;
    canvas::PixelFormat m_format{canvas::PixelFormat::RGBA8};  // o da grade; `forEachPixel` confere
    bool m_circular{true};
    double m_cosA{1.0};
    double m_sinA{0.0};
    double m_invAspect{1.0};
    double m_maxRadiusSq{0.0};
};

} // namespace aladyn::engine::raster

#endif // ALADYN_ENGINE_DAB_FOOTPRINT_HPP
