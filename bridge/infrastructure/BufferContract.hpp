#ifndef ALADYN_BRIDGE_BUFFER_CONTRACT_HPP
#define ALADYN_BRIDGE_BUFFER_CONTRACT_HPP

#include <pybind11/pybind11.h>
#include <cstdint>
#include <limits>
#include <string>

namespace aladyn::bridge {

// Native raster offsets use signed ints. Check before multiplying or allocating.
inline size_t checkedRasterBytes(int width, int height, size_t channels) {
    const size_t limit = static_cast<size_t>(std::numeric_limits<int>::max());
    if (width <= 0 || height <= 0 || channels == 0 || channels > limit ||
        static_cast<size_t>(width) > limit / channels / static_cast<size_t>(height)) {
        throw pybind11::value_error("Invalid raster dimensions or byte size");
    }
    return static_cast<size_t>(width) * static_cast<size_t>(height) * channels;
}

inline void validateRasterInput(const std::string& data, int width, int height, size_t channels) {
    if (data.size() != checkedRasterBytes(width, height, channels)) {
        throw pybind11::value_error("Buffer length does not match raster dimensions");
    }
}

// Python owns the immutable copy; no facade pointer can escape through a view.
inline pybind11::bytes pixelSnapshot(const uint8_t* data, size_t size) {
    if (size == 0) return pybind11::bytes();
    if (!data || size > static_cast<size_t>(PY_SSIZE_T_MAX)) {
        throw pybind11::value_error("Invalid native pixel buffer");
    }
    return pybind11::bytes(reinterpret_cast<const char*>(data), size);
}

} // namespace aladyn::bridge
#endif
