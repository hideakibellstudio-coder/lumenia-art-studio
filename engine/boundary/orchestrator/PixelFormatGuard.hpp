#pragma once

#include "../../core/canvas/PixelFormat.hpp"

#include <stdexcept>
#include <string>

namespace aladyn::engine::boundary::orchestrator {

// Recusa limpa de uma operação que ainda escreve só em 8 bits quando o documento é de 16 bits.
//
// Os pincéis, o balde, a seleção, a transformação e a colagem escrevem pixels RGBA8 direto nos tiles; num tile de 16
// bits isso não daria erro, daria lixo (a escrita cairia nos 32 KiB errados). Cada uma passa por aqui no começo,
// antes de mexer em qualquer estado, e o documento fica como estava. Sai daqui conforme a S6 do plano do compositor
// ensinar cada operação a escrever nos 16 bits.
//
// std::logic_error, e não `return false`: false já significa "nada a fazer" (camada travada, fora da seleção) e a
// interface não pode confundir os dois. O pybind11 entrega como RuntimeError.
inline void requireEightBit(canvas::PixelFormat format, const char* operation) {
    if (format != canvas::PixelFormat::RGBA8) {
        throw std::logic_error(std::string(operation) + " is not available in 16-bit documents yet");
    }
}

} // namespace aladyn::engine::boundary::orchestrator
