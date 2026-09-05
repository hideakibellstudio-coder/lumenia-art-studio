#include "BindingsCommon.hpp"

PYBIND11_MODULE(aladyn_engine_native, m) {
    m.doc() = "ALADYN ENGINE — Mini-Motores, Categorias de Receitas e UI Dinâmica";

    auto facade = py::class_<aladyn::engine::boundary::PaintEngineFacade>(m, "PaintEngineFacade");
    facade.def(py::init<int, int>(), py::arg("width") = 1920, py::arg("height") = 1080);

    aladyn::bridge::bind_math_brush(m, facade);
    aladyn::bridge::bind_canvas(m, facade);
    aladyn::bridge::bind_layers(m, facade);
    aladyn::bridge::bind_stroke(m, facade);
    aladyn::bridge::bind_tools(m, facade);
}
