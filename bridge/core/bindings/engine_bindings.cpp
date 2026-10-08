#include "BindingsCommon.hpp"
#include "../../infrastructure/BufferContract.hpp"
#include "../../infrastructure/ContractVersion.hpp"

PYBIND11_MODULE(aladyn_engine_native, m) {
    m.doc() = "ALADYN ENGINE — Mini-Motores, Categorias de Receitas e UI Dinâmica";
    m.attr("CONTRACT_VERSION") = aladyn::bridge::kContractVersion;

    auto facade = py::class_<aladyn::engine::boundary::PaintEngineFacade>(m, "PaintEngineFacade");
    facade.def(py::init([](int width, int height, int pixelFormat) {
        return std::make_unique<aladyn::engine::boundary::PaintEngineFacade>(
            width, height, static_cast<aladyn::engine::canvas::PixelFormat>(aladyn::bridge::checkedPixelFormatId(pixelFormat)));
    }), py::arg("width") = 1920, py::arg("height") = 1080, py::arg("pixel_format") = 0);

    aladyn::bridge::bind_math_brush(m, facade);
    aladyn::bridge::bind_canvas(m, facade);
    aladyn::bridge::bind_layers(m, facade);
    aladyn::bridge::bind_persistence(m, facade);
    aladyn::bridge::bind_stroke(m, facade);
    aladyn::bridge::bind_tools(m, facade);
    aladyn::bridge::bind_runtime(m);
}
