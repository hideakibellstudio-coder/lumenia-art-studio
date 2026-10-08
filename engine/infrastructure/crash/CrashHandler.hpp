#ifndef ALADYN_ENGINE_CRASH_CRASH_HANDLER_HPP
#define ALADYN_ENGINE_CRASH_CRASH_HANDLER_HPP

#include <string>

namespace aladyn::engine::crash {

// Writes a Windows minidump (lumenia-YYYYMMDD-HHMMSS-<pid>.dmp) into
// `directoryUtf8` when the process dies of an unhandled exception (an invalid
// access inside the engine, a Qt fault). The Python `faulthandler` only sees the
// Python stack; the dump plus the build's PDB shows the C++ function that broke.
// The handler returns "continue search", so Windows Error Reporting and the
// faulthandler keep working. False when the directory is unusable or the
// platform is not Windows.
bool installCrashHandler(const std::string& directoryUtf8);

// A dump of the running process, on request ("save diagnostic dump"): same
// format, no exception record.
bool writeDiagnosticDump(const std::string& fileUtf8);

} // namespace aladyn::engine::crash

#endif // ALADYN_ENGINE_CRASH_CRASH_HANDLER_HPP
