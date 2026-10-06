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
        .def("set_layer_document_uid",  &boundary::PaintEngineFacade::setLayerDocumentUid)
        .def("set_layer_name",          &boundary::PaintEngineFacade::setLayerName)
        .def("get_layer_name",          &boundary::PaintEngineFacade::getLayerName)
        .def("begin_layer_transaction", &boundary::PaintEngineFacade::beginLayerTransaction)
        .def("apply_prepared_geometry", &boundary::PaintEngineFacade::applyPreparedGeometry)
        .def("commit_layer_transaction", &boundary::PaintEngineFacade::commitLayerTransaction)
        .def("cancel_layer_transaction", &boundary::PaintEngineFacade::cancelLayerTransaction)
        .def("get_undo_step_id", &boundary::PaintEngineFacade::getUndoStepId)
        .def("get_redo_step_id", &boundary::PaintEngineFacade::getRedoStepId)
        .def("get_history_step_ids", &boundary::PaintEngineFacade::getHistoryStepIds)
        .def("set_layer_opacity",       &boundary::PaintEngineFacade::setLayerOpacity)
        .def("set_layer_blend_mode",    &boundary::PaintEngineFacade::setLayerBlendMode)
        .def("set_layer_visibility",    &boundary::PaintEngineFacade::setLayerVisibility)
        .def("set_layer_lock",          &boundary::PaintEngineFacade::setLayerLock)
        .def("set_layer_alpha_lock",    &boundary::PaintEngineFacade::setLayerAlphaLock)
        .def("is_layer_alpha_locked",   &boundary::PaintEngineFacade::isLayerAlphaLocked)
        .def("set_layer_clipping_mask", &boundary::PaintEngineFacade::setLayerClippingMask)
        .def("is_layer_clipping_mask",  &boundary::PaintEngineFacade::isLayerClippingMask)
        .def("add_layer_mask",            &boundary::PaintEngineFacade::addLayerMask)
        .def("remove_layer_mask",         &boundary::PaintEngineFacade::removeLayerMask)
        .def("has_layer_mask",            &boundary::PaintEngineFacade::hasLayerMask)
        .def("set_layer_mask_enabled",    &boundary::PaintEngineFacade::setLayerMaskEnabled)
        .def("is_layer_mask_enabled",     &boundary::PaintEngineFacade::isLayerMaskEnabled)
        .def("set_layer_mask_edit_target",&boundary::PaintEngineFacade::setLayerMaskEditTarget)
        .def("is_layer_mask_edit_target", &boundary::PaintEngineFacade::isLayerMaskEditTarget)
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
                d["document_uid"] = l->getDocumentUid();
                d["opacity"] = l->getOpacity();
                d["visible"] = l->isVisible();
                d["locked"] = l->isLocked();
                d["alpha_locked"] = l->isAlphaLocked();
                d["clipping_mask"] = l->isClippingMask();
                d["has_mask"] = l->hasMask();
                d["mask_enabled"] = l->isMaskEnabled();
                d["mask_edit_target"] = l->isMaskEditTarget();
                d["blend_mode"] = static_cast<int>(l->getBlendMode());
                d["is_group"] = l->isGroup();
                d["is_filter"] = l->isFilter();
                int parentIndex = -1;
                if (const auto* parent = l->getParent()) {
                    for (int i = 0; i < static_cast<int>(self.getLayerStack().getDrawingLayerCount()); ++i) {
                        if (self.getLayerStack().getDrawingLayer(i) == parent) { parentIndex = i; break; }
                    }
                }
                d["parent_index"] = parentIndex;
            }
            return d;
        });
}

} // namespace aladyn::bridge
