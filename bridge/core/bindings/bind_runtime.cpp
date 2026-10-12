#include "BindingsCommon.hpp"

namespace aladyn::bridge {

using namespace aladyn::engine;

// Process-wide services that belong to the user, not to a document: the crash
// dump. Module-level functions, no facade involved.
void bind_runtime(py::module_& m) {
    m.def("install_crash_handler", &crash::installCrashHandler, py::arg("directory"));
    m.def("write_diagnostic_dump", &crash::writeDiagnosticDump, py::arg("path"));
}

} // namespace aladyn::bridge
