#include "BindingsCommon.hpp"

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
            // The compression runs without the GIL, so the interface keeps running while a
            // document is being saved. Only the final copy into Python bytes needs it.
            std::vector<uint8_t> encoded;
            {
                py::gil_scoped_release release;
                encoded = self.encodeLayer(index);
            }
            return py::bytes(reinterpret_cast<const char*>(encoded.data()), encoded.size());
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
