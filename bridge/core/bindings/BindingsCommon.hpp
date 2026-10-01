#ifndef ALADYN_BRIDGE_BINDINGS_COMMON_HPP
#define ALADYN_BRIDGE_BINDINGS_COMMON_HPP

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "../../../engine/boundary/public-api/AladynEngine.hpp"  // única porta para o motor

namespace py = pybind11;

namespace aladyn::bridge {

using FacadeClass = py::class_<engine::boundary::PaintEngineFacade>;

void bind_math_brush(py::module_& m, FacadeClass& facade);
void bind_canvas(py::module_& m, FacadeClass& facade);
void bind_layers(py::module_& m, FacadeClass& facade);
void bind_persistence(py::module_& m, FacadeClass& facade);
void bind_stroke(py::module_& m, FacadeClass& facade);
void bind_tools(py::module_& m, FacadeClass& facade);

} // namespace aladyn::bridge

#endif // ALADYN_BRIDGE_BINDINGS_COMMON_HPP
