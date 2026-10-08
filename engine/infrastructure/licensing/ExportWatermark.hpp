#ifndef ALADYN_ENGINE_LICENSING_EXPORT_WATERMARK_HPP
#define ALADYN_ENGINE_LICENSING_EXPORT_WATERMARK_HPP

#include <cstddef>
#include <cstdint>

namespace aladyn::engine::licensing {

// Stamps "LUMENIA FREE" in a staggered grid over an RGBA8 image (straight alpha,
// rows contiguous): a light glyph over a dark shadow, so it reads on any
// background. The letter size follows the image, so a crop keeps several stamps.
// This is what an export without a license looks like; the painting itself and
// the .lmn file are never touched.
void stampUnlicensedWatermark(uint8_t* rgba, int width, int height);

} // namespace aladyn::engine::licensing

#endif // ALADYN_ENGINE_LICENSING_EXPORT_WATERMARK_HPP
