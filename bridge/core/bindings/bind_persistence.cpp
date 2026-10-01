#include "BindingsCommon.hpp"

#include <cstring>
#include <memory>
#include <vector>

namespace aladyn::bridge {

using namespace aladyn::engine;

void bind_persistence(py::module_& m, FacadeClass& facade) {
    // The layers of a document frozen at one instant (S1.2). Taken on the thread that owns
    // the document at the cost of the tile count; read from any thread afterwards.
    py::class_<boundary::LayerSnapshot, std::shared_ptr<boundary::LayerSnapshot>>(m, "LayerSnapshot")
        .def_property_readonly("width", &boundary::LayerSnapshot::width)
        .def_property_readonly("height", &boundary::LayerSnapshot::height)
        .def_property_readonly("layer_count", &boundary::LayerSnapshot::layerCount)
        .def("has_pixels", &boundary::LayerSnapshot::hasPixels, py::arg("index"))
        .def("encode_layer", [](const boundary::LayerSnapshot& self, int index) {
            // The compression and the copy of its result run without the GIL, so the interface
            // keeps running while a document is being saved: the bytes object is created with it
            // (nobody else can see it yet) and filled without it. Copying 30 MB into fresh memory
            // while holding the GIL froze the interface for tens of milliseconds.
            std::vector<uint8_t> encoded;
            {
                py::gil_scoped_release release;
                encoded = self.encodeLayer(index);
            }
            PyObject* raw = PyBytes_FromStringAndSize(nullptr, static_cast<Py_ssize_t>(encoded.size()));
            if (!raw) throw py::error_already_set();
            py::bytes out = py::reinterpret_steal<py::bytes>(raw);
            {
                py::gil_scoped_release release;
                std::memcpy(PyBytes_AS_STRING(raw), encoded.data(), encoded.size());
            }
            return out;
        }, py::arg("index"));

    facade
        .def("snapshot_layers", &boundary::PaintEngineFacade::snapshotLayers)
        .def("restore_layer_tiles", [](boundary::PaintEngineFacade& self, int index, py::bytes data) {
            // Straight from the Python bytes, no copy; the decode validates every field.
            self.restoreLayerTiles(index, reinterpret_cast<const uint8_t*>(PyBytes_AS_STRING(data.ptr())),
                                   static_cast<size_t>(PyBytes_GET_SIZE(data.ptr())));
        }, py::arg("layer_index"), py::arg("data"))
        .def("begin_batch", &boundary::PaintEngineFacade::beginBatch)
        .def("end_batch", &boundary::PaintEngineFacade::endBatch);
}

} // namespace aladyn::bridge
