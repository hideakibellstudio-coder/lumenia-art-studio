#include "BindingsCommon.hpp"
#include "BufferContract.hpp"

namespace aladyn::bridge {

using namespace aladyn::engine;

void bind_tools(py::module_& /*m*/, FacadeClass& facade) {
    facade
        // Preenchimento (Flood Fill / Balde de Tinta Nativo)
        .def("flood_fill", [](boundary::PaintEngineFacade& self, int seedX, int seedY, const raster::ColorRGBA& fillColor,
                              int tolerance, bool contiguous, int expandPx, int gapClosingPx, bool antiAliasing, bool sampleAllLayers) {
            return self.floodFill(seedX, seedY, fillColor, tolerance, contiguous, expandPx, gapClosingPx, antiAliasing, sampleAllLayers);
        }, py::arg("seed_x"), py::arg("seed_y"), py::arg("fill_color"),
           py::arg("tolerance") = 20, py::arg("contiguous") = true,
           py::arg("expand_px") = 1, py::arg("gap_closing_px") = 0,
           py::arg("anti_aliasing") = true, py::arg("sample_all_layers") = true)
        // Desfazer / Refazer
        .def("undo", &boundary::PaintEngineFacade::undo)
        .def("redo", &boundary::PaintEngineFacade::redo)
        .def("can_undo", &boundary::PaintEngineFacade::canUndo)
        .def("can_redo", &boundary::PaintEngineFacade::canRedo)
        .def("get_undo_count", &boundary::PaintEngineFacade::getUndoCount)
        .def("get_history_error", &boundary::PaintEngineFacade::getHistoryError)
        .def("get_redo_count", &boundary::PaintEngineFacade::getRedoCount)
        .def("set_undo_memory_limit_mb", &boundary::PaintEngineFacade::setUndoMemoryLimitMB)
        .def("get_undo_memory_limit_mb", &boundary::PaintEngineFacade::getUndoMemoryLimitMB)
        .def("set_undo_max_steps", &boundary::PaintEngineFacade::setUndoMaxSteps)
        .def("get_undo_max_steps", &boundary::PaintEngineFacade::getUndoMaxSteps)
        // Seleção & Varinha Mágica
        .def("magic_wand_select", &boundary::PaintEngineFacade::magicWandSelect,
             py::arg("seed_x"), py::arg("seed_y"),
             py::arg("tolerance") = 20, py::arg("contiguous") = true,
             py::arg("expand_px") = 0, py::arg("anti_aliasing") = true,
             py::arg("mode") = 0, py::arg("sample_all_layers") = true)
        .def("select_rect", &boundary::PaintEngineFacade::selectRect,
             py::arg("x"), py::arg("y"), py::arg("w"), py::arg("h"),
             py::arg("mode") = 0, py::arg("feather_px") = 0, py::arg("corner_radius_px") = 0)
        .def("select_ellipse", &boundary::PaintEngineFacade::selectEllipse,
             py::arg("cx"), py::arg("cy"), py::arg("rx"), py::arg("ry"),
             py::arg("mode") = 0, py::arg("anti_aliasing") = true, py::arg("feather_px") = 0)
        .def("select_polygon", &boundary::PaintEngineFacade::selectPolygon,
             py::arg("flat_points"), py::arg("mode") = 0,
             py::arg("anti_aliasing") = true, py::arg("feather_px") = 0)
        .def("clear_selection", &boundary::PaintEngineFacade::clearSelection)
        .def("invert_selection", &boundary::PaintEngineFacade::invertSelection)
        .def("select_all", &boundary::PaintEngineFacade::selectAll)
        .def("has_selection", &boundary::PaintEngineFacade::hasSelection)
        .def("delete_selection_on_active_layer", &boundary::PaintEngineFacade::deleteSelectionOnActiveLayer)
        .def("fill_selection_on_active_layer", &boundary::PaintEngineFacade::fillSelectionOnActiveLayer, py::arg("fill_color"))
        .def("get_selection_mask_buffer", [](boundary::PaintEngineFacade& self) -> py::object {
            if (!self.hasSelection()) return py::none();
            return pixelSnapshot(self.getSelectionMaskData(), self.getSelectionMaskSize());
        })
        .def("get_selection_bounds", &boundary::PaintEngineFacade::getSelectionBounds)
        .def("set_selection_mask_buffer", [](boundary::PaintEngineFacade& self, py::bytes buffer) {
            std::string data = buffer;
            validateRasterInput(data, self.getWidth(), self.getHeight(), 1);
            return self.setSelectionMaskBuffer(std::vector<uint8_t>(data.begin(), data.end()));
        })
        .def("get_selection_contour_segments", &boundary::PaintEngineFacade::getSelectionContourSegments)
        .def("get_selection_contour_loops", &boundary::PaintEngineFacade::getSelectionContourLoops)
        // Transform Tool bindings
        .def("begin_transform", &boundary::PaintEngineFacade::beginTransform)
        .def("is_transform_active", &boundary::PaintEngineFacade::isTransformActive)
        .def("get_transform_source_bounds", &boundary::PaintEngineFacade::getTransformSourceBounds)
        .def("get_transform_pivot", &boundary::PaintEngineFacade::getTransformPivot)
        .def("commit_transform", &boundary::PaintEngineFacade::commitTransform,
             py::arg("dx"), py::arg("dy"), py::arg("scale_x"), py::arg("scale_y"),
             py::arg("rotation_deg"), py::arg("pivot_x"), py::arg("pivot_y"),
             py::arg("flip_h") = false, py::arg("flip_v") = false, py::arg("interp_mode") = 2)
        .def("cancel_transform", &boundary::PaintEngineFacade::cancelTransform)
        .def("flip_active_layer", &boundary::PaintEngineFacade::flipActiveLayer, py::arg("horizontal"))
        .def("rotate_active_layer_90", &boundary::PaintEngineFacade::rotateActiveLayer90, py::arg("clockwise"))
        .def("get_transform_source_buffer_size", &boundary::PaintEngineFacade::getTransformSourceBufferSize)
        .def("get_transform_source_buffer", [](boundary::PaintEngineFacade& self) -> py::object {
            uint8_t* ptr = self.getTransformSourceBufferData();
            if (!ptr) return py::none();
            auto sz = self.getTransformSourceBufferSize();
            if (sz[0] <= 0 || sz[1] <= 0) return py::none();
            return pixelSnapshot(ptr, checkedRasterBytes(sz[0], sz[1], 4));
        })
        // Métodos de Simetria & Guias
        .def("set_symmetry_config", &boundary::PaintEngineFacade::setSymmetryConfig,
             py::arg("mode"), py::arg("cx"), py::arg("cy"), py::arg("angle_rad"),
             py::arg("segments") = 6, py::arg("stop_at_center") = false)
        .def("clear_symmetry", &boundary::PaintEngineFacade::clearSymmetry)
        .def("set_guide_config", &boundary::PaintEngineFacade::setGuideConfig,
             py::arg("type"),
             py::arg("p0x") = 0.0, py::arg("p0y") = 0.0,
             py::arg("p1x") = 100.0, py::arg("p1y") = 100.0,
             py::arg("p2x") = 200.0, py::arg("p2y") = 200.0,
             py::arg("p3x") = 300.0, py::arg("p3y") = 300.0,
             py::arg("vp_ax") = 400.0, py::arg("vp_ay") = 300.0,
             py::arg("vp_bx") = -1000.0, py::arg("vp_by") = 300.0,
             py::arg("vp_cx") = 400.0, py::arg("vp_cy") = -2000.0,
             py::arg("cx") = 0.0, py::arg("cy") = 0.0,
             py::arg("fov") = 130.0, py::arg("pitch") = 0.0, py::arg("yaw") = 0.0,
             py::arg("snap_radius") = 32.0)
        .def("clear_guide", &boundary::PaintEngineFacade::clearGuide)
        .def("snap_point", &boundary::PaintEngineFacade::snapPoint,
             py::arg("raw_x"), py::arg("raw_y"),
             py::arg("last_x") = 0.0, py::arg("last_y") = 0.0,
             py::arg("has_last") = false)
        // Curvilinear (6P fisheye) — Fase C2b
        .def("set_curvilinear_guide_config", &boundary::PaintEngineFacade::setCurvilinearGuideConfig,
             py::arg("base_radius") = 400.0, py::arg("density") = 30.0,
             py::arg("show_v") = true, py::arg("show_h") = true, py::arg("show_d") = true,
             py::arg("show_ground") = false, py::arg("show_ceiling") = false,
             py::arg("show_ground_verticals") = false, py::arg("show_ceiling_verticals") = false,
             py::arg("show_straight_verticals") = false,
             py::arg("snap_mode") = 0, py::arg("snap_sensitivity") = 3.0)
        .def("get_curvilinear_candidates", &boundary::PaintEngineFacade::getCurvilinearCandidates,
             py::arg("click_x"), py::arg("click_y"))
        .def("get_nearest_primary_grid_curve", &boundary::PaintEngineFacade::getNearestPrimaryGridCurve,
             py::arg("x"), py::arg("y"), py::arg("max_dist") = 24.0)
        .def("snap_curvilinear", &boundary::PaintEngineFacade::snapCurvilinear,
             py::arg("raw_x"), py::arg("raw_y"), py::arg("start_x"), py::arg("start_y"),
             py::arg("candidates"), py::arg("locked_index") = -1,
             py::arg("is_stroking") = false, py::arg("zoom") = 1.0)
        // Perspectiva (1P/2P/3P/Isometric) -- Fase C3.1
        .def("snap_perspective", &boundary::PaintEngineFacade::snapPerspective,
             py::arg("raw_x"), py::arg("raw_y"), py::arg("start_x"), py::arg("start_y"),
             py::arg("has_locked_dir") = false, py::arg("locked_dir_x") = 0.0, py::arg("locked_dir_y") = 0.0,
             py::arg("zoom") = 1.0)
        // -- Fase D0 (redesign do motor de snap) -- ver
        // claude/proposta-redesign-motor-snap-guias.md no projeto. Componentes
        // genericos ainda nao ligados a nenhum tipo de guia real (D1-D3);
        // expostos so para testar TrajectoryEstimator/SnapLockStateMachine
        // isoladamente via pytest, mesma convencao de snap_curvilinear/snap_perspective.
        .def("estimate_trajectory", &boundary::PaintEngineFacade::estimateTrajectory,
             py::arg("recent_points"), py::arg("zoom") = 1.0)
        .def("step_snap_lock", &boundary::PaintEngineFacade::stepSnapLock,
             py::arg("raw_x"), py::arg("raw_y"),
             py::arg("traj_dir_x"), py::arg("traj_dir_y"), py::arg("traj_confidence"),
             py::arg("candidates"),
             py::arg("prev_state") = 0, py::arg("prev_candidate_index") = -1, py::arg("prev_streak") = 0,
             py::arg("attraction_radius") = 32.0, py::arg("breakaway_radius") = 32.0,
             py::arg("commit_frames") = 3, py::arg("score_sharpness") = 2.0);
}

} // namespace aladyn::bridge
