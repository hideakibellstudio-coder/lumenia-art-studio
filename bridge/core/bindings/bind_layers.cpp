#include "BindingsCommon.hpp"

namespace aladyn::bridge {

using namespace aladyn::engine;

void bind_layers(py::module_& /*m*/, FacadeClass& facade) {
    facade
        .def("add_layer",               &boundary::PaintEngineFacade::addLayer, py::arg("name") = "", py::arg("insert_index") = -1)
        .def("add_group",               &boundary::PaintEngineFacade::addGroup, py::arg("name") = "Novo Grupo", py::arg("insert_index") = -1)
        .def("add_filter_layer",        &boundary::PaintEngineFacade::addFilterLayer, py::arg("name"), py::arg("filter_type_id"), py::arg("insert_index") = -1)
        .def("set_filter_params",       &boundary::PaintEngineFacade::setFilterParams)
        .def("get_filter_params",       &boundary::PaintEngineFacade::getFilterParams)
        .def("get_filter_type",         &boundary::PaintEngineFacade::getFilterType)
        .def("is_filter_layer",         &boundary::PaintEngineFacade::isFilterLayer)
        .def("is_group",                &boundary::PaintEngineFacade::isGroup)
        .def("set_group_pass_through",  &boundary::PaintEngineFacade::setGroupPassThrough)
        .def("remove_layer",            &boundary::PaintEngineFacade::removeLayer)
        .def("duplicate_layer",         &boundary::PaintEngineFacade::duplicateLayer)
        .def("select_layer",            &boundary::PaintEngineFacade::selectLayer)
        .def("reorder_layer",           &boundary::PaintEngineFacade::reorderLayer)
        .def("reorder_layers",          &boundary::PaintEngineFacade::reorderLayers)
        .def("set_layer_parents",       &boundary::PaintEngineFacade::setLayerParents)
        .def("set_layer_name",          &boundary::PaintEngineFacade::setLayerName)
        .def("set_layer_opacity",       &boundary::PaintEngineFacade::setLayerOpacity)
        .def("set_layer_blend_mode",    &boundary::PaintEngineFacade::setLayerBlendMode)
        .def("set_layer_visibility",    &boundary::PaintEngineFacade::setLayerVisibility)
        .def("set_layer_lock",          &boundary::PaintEngineFacade::setLayerLock)
        .def("set_layer_alpha_lock",    &boundary::PaintEngineFacade::setLayerAlphaLock)
        .def("is_layer_alpha_locked",   &boundary::PaintEngineFacade::isLayerAlphaLocked)
        .def("set_layer_clipping_mask", &boundary::PaintEngineFacade::setLayerClippingMask)
        .def("is_layer_clipping_mask",  &boundary::PaintEngineFacade::isLayerClippingMask)
        .def("flatten_group",           &boundary::PaintEngineFacade::flattenGroup)
        .def("merge_layer_down",        &boundary::PaintEngineFacade::mergeLayerDown)
        .def("clear_layer",             &boundary::PaintEngineFacade::clearLayer)
        .def("set_background_visibility", &boundary::PaintEngineFacade::setBackgroundVisibility)
        .def("is_background_visible",     &boundary::PaintEngineFacade::isBackgroundVisible)
        .def("set_background_color",      &boundary::PaintEngineFacade::setBackgroundColor, py::arg("r"), py::arg("g"), py::arg("b"), py::arg("a") = 255)
        .def("get_active_layer_index",    &boundary::PaintEngineFacade::getActiveLayerIndex)
        .def("get_drawing_layer_count",   &boundary::PaintEngineFacade::getDrawingLayerCount)
        .def("get_layer_info", [](boundary::PaintEngineFacade& self, int index) -> py::dict {
            py::dict d;
            if (const auto* l = self.getLayerStack().getDrawingLayer(index)) {
                d["name"] = l->getName();
                d["opacity"] = l->getOpacity();
                d["visible"] = l->isVisible();
                d["locked"] = l->isLocked();
                d["alpha_locked"] = l->isAlphaLocked();
                d["clipping_mask"] = l->isClippingMask();
                d["blend_mode"] = static_cast<int>(l->getBlendMode());
                d["is_group"] = l->isGroup();
                d["is_filter"] = l->isFilter();
            }
            return d;
        });
}

} // namespace aladyn::bridge
