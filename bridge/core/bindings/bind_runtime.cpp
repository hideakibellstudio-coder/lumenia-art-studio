#include "BindingsCommon.hpp"
#include "../../infrastructure/BufferContract.hpp"

#include <cstring>
#include <string>

namespace aladyn::bridge {

using namespace aladyn::engine;

namespace {

py::dict statusDict(const licensing::LicenseStatus& status) {
    py::dict out;
    out["state"] = std::string(licensing::licenseStateName(status.state));
    out["license_id"] = status.claims.licenseId;
    out["sku"] = status.claims.sku;
    out["holder_name"] = status.claims.holderName;
    out["issued_on"] = status.claims.issuedOn;
    out["updates_until"] = status.claims.updatesUntil;
    out["expires_on"] = status.claims.expiresOn;
    return out;
}

licensing::PublicKey checkedPublicKey(const std::string& raw) {
    licensing::PublicKey key{};
    if (raw.size() != key.size()) throw py::value_error("public key must be 64 bytes (X || Y)");
    std::memcpy(key.data(), raw.data(), key.size());
    return key;
}

} // namespace

// Process-wide services that belong to the user, not to a document: the license
// and the crash dump. Module-level functions, no facade involved.
void bind_runtime(py::module_& m) {
    m.def("license_apply", [](const std::string& token) {
        return statusDict(licensing::LicenseAuthority::instance().apply(token));
    }, py::arg("token"));
    m.def("license_status", []() {
        return statusDict(licensing::LicenseAuthority::instance().current());
    });
    m.def("license_clear", []() { licensing::LicenseAuthority::instance().clear(); });
    m.def("license_evaluate", [](const std::string& token, const std::string& today,
                                 const std::string& buildDate, py::bytes publicKey) {
        return statusDict(licensing::evaluateLicense(token, checkedPublicKey(publicKey), today, buildDate));
    }, py::arg("token"), py::arg("today"), py::arg("build_date"), py::arg("public_key"));
    m.def("license_build_date", []() { return licensing::buildIsoDate(); });
    m.def("license_key_id", []() { return std::string(licensing::kLicenseKeyId); });

    m.def("apply_export_policy", [](py::bytes rgba, int width, int height) -> py::bytes {
        const auto size = static_cast<size_t>(PyBytes_GET_SIZE(rgba.ptr()));
        if (size != checkedRasterBytes(width, height, 4)) {
            throw py::value_error("Buffer length does not match raster dimensions");
        }
        if (licensing::LicenseAuthority::instance().isLicensed()) return rgba;
        const auto* source = reinterpret_cast<const uint8_t*>(PyBytes_AS_STRING(rgba.ptr()));
        return filledBytes(size, [&](uint8_t* dst, size_t n) {
            std::memcpy(dst, source, n);
            licensing::stampUnlicensedWatermark(dst, width, height);
        });
    }, py::arg("rgba"), py::arg("width"), py::arg("height"));

    m.def("install_crash_handler", &crash::installCrashHandler, py::arg("directory"));
    m.def("write_diagnostic_dump", &crash::writeDiagnosticDump, py::arg("path"));
}

} // namespace aladyn::bridge
