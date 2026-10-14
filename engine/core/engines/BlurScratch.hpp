#ifndef ALADYN_ENGINE_BLUR_SCRATCH_HPP
#define ALADYN_ENGINE_BLUR_SCRATCH_HPP

#include <cstddef>
#include <vector>

namespace aladyn::engine::engines {

// ─── A MEMÓRIA DE TRABALHO DO DESFOQUE ──────────────────────────────────────
//
// Cada carimbo do Desfoque precisa de três campos de pontos flutuantes do tamanho da área (a cópia da camada, o
// passe horizontal e o resultado). Alocá-los e zerá-los a cada carimbo custava mais que a conta num pincel de 48 px
// (um traço tem centenas de carimbos), então o motor guarda os vetores entre carimbos: só crescem, e `BlurredRegion`
// escreve cada elemento antes de lê-lo, de modo que o conteúdo antigo nunca aparece.
//
// Pertence a um `BlurEngine` e é usado por uma thread por vez (o laço paralelo está dentro do carimbo).
class BlurScratch {
public:
    std::vector<float> source;      // cinco planos da área da camada, na ordem de `BlurPlane`
    std::vector<float> horizontal;  // os mesmos planos depois do passe horizontal
    std::vector<float> blurred;     // os planos da região pintada depois do passe vertical

    // Um pincel gigante pediria dezenas de megabytes por carimbo; esses não ficam guardados.
    void releaseIfLarge(std::size_t maxFloats) noexcept {
        releaseIfLarge(source, maxFloats);
        releaseIfLarge(horizontal, maxFloats);
        releaseIfLarge(blurred, maxFloats);
    }

private:
    static void releaseIfLarge(std::vector<float>& buffer, std::size_t maxFloats) noexcept {
        if (buffer.capacity() > maxFloats) std::vector<float>().swap(buffer);
    }
};

} // namespace aladyn::engine::engines

#endif // ALADYN_ENGINE_BLUR_SCRATCH_HPP
