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

// A Python bytes of `size` bytes filled in place by `fill(uint8_t* dst, size_t size)`: one
// copy, with no std::vector in between. If `fill` throws, the bytes are released.
template <typename Fill>
inline pybind11::bytes filledBytes(size_t size, Fill&& fill) {
    PyObject* raw = PyBytes_FromStringAndSize(nullptr, static_cast<Py_ssize_t>(size));
    if (!raw) throw pybind11::error_already_set();
    pybind11::bytes out = pybind11::reinterpret_steal<pybind11::bytes>(raw);
    fill(reinterpret_cast<uint8_t*>(PyBytes_AS_STRING(raw)), size);
    return out;
}

// The pixel format a Python integer names (0 = 8 bits per channel, 1 = 16); anything else is a ValueError.
inline uint8_t checkedPixelFormatId(int id) {
    if (id < 0 || id > 1) throw pybind11::value_error("Unknown pixel format id (0 = RGBA8, 1 = RGBA16)");
    return static_cast<uint8_t>(id);
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
