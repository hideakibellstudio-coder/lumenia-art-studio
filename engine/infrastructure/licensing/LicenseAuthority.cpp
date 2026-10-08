#include "LicenseAuthority.hpp"

#include "LicensePublicKey.hpp"
#include "RevokedLicenses.hpp"

#include <chrono>
#include <cstdio>
#include <cstring>

namespace aladyn::engine::licensing {
namespace {

std::string isoDate(long long year, unsigned month, unsigned day) {
    char text[48] = {};  // room for any long long: -Wformat-truncation stays quiet
    std::snprintf(text, sizeof(text), "%04lld-%02u-%02u", year, month, day);
    return text;
}

bool isRevoked(std::string_view licenseId) {
    for (std::string_view revoked : kRevokedLicenseIds) {
        if (revoked == licenseId) return true;
    }
    return false;
}

} // namespace

std::string_view licenseStateName(LicenseState state) {
    switch (state) {
        case LicenseState::Unlicensed: return "unlicensed";
        case LicenseState::Licensed: return "licensed";
        case LicenseState::Malformed: return "malformed";
        case LicenseState::BadSignature: return "bad_signature";
        case LicenseState::Expired: return "expired";
        case LicenseState::Revoked: return "revoked";
        case LicenseState::UpdatesExpired: return "updates_expired";
        case LicenseState::Unsupported: return "unsupported";
    }
    return "unlicensed";
}

LicenseStatus evaluateLicense(std::string_view token, const PublicKey& publicKey,
                              std::string_view today, std::string_view buildDate) {
    LicenseStatus status;
    const auto encoded = splitToken(token);
    if (!encoded) {
        status.state = LicenseState::Malformed;
        return status;
    }
    if (!signatureVerificationAvailable()) {
        status.state = LicenseState::Unsupported;
        return status;
    }
    if (!verifyEcdsaP256Sha256(publicKey, encoded->payload.data(), encoded->payload.size(),
                               encoded->signature.data(), encoded->signature.size())) {
        status.state = LicenseState::BadSignature;
        return status;
    }
    const auto claims = parseClaims(encoded->payload);
    if (!claims) {
        status.state = LicenseState::Malformed;
        return status;
    }
    status.claims = *claims;
    // ISO dates compare as text.
    if (!claims->machineId.empty()) {
        status.state = LicenseState::Unsupported;
    } else if (isRevoked(claims->licenseId)) {
        status.state = LicenseState::Revoked;
    } else if (!claims->expiresOn.empty() && today > claims->expiresOn) {
        status.state = LicenseState::Expired;
    } else if (!claims->updatesUntil.empty() && buildDate > claims->updatesUntil) {
        status.state = LicenseState::UpdatesExpired;
    } else {
        status.state = LicenseState::Licensed;
    }
    return status;
}

std::string todayIsoDate() {
    // Days since 1970-01-01 to a civil date (H. Hinnant's algorithm): no locale, no time zone.
    using namespace std::chrono;
    long long z = duration_cast<seconds>(system_clock::now().time_since_epoch()).count() / 86400;
    z += 719468;
    const long long era = (z >= 0 ? z : z - 146096) / 146097;
    const long long doe = z - era * 146097;
    const long long yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    const long long doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    const long long mp = (5 * doy + 2) / 153;
    const auto day = static_cast<unsigned>(doy - (153 * mp + 2) / 5 + 1);
    const auto month = static_cast<unsigned>(mp < 10 ? mp + 3 : mp - 9);
    const long long year = yoe + era * 400 + (month <= 2 ? 1 : 0);
    return isoDate(year, month, day);
}

std::string buildIsoDate() {
    // __DATE__ is "Mmm dd yyyy" (day padded with a space).
    static constexpr char kCompiled[] = __DATE__;
    static constexpr const char* kMonths = "JanFebMarAprMayJunJulAugSepOctNovDec";
    unsigned month = 1;
    for (unsigned i = 0; i < 12; ++i) {
        if (std::strncmp(kCompiled, kMonths + i * 3, 3) == 0) month = i + 1;
    }
    const unsigned day = (kCompiled[4] == ' ' ? 0u : static_cast<unsigned>(kCompiled[4] - '0')) * 10u +
                         static_cast<unsigned>(kCompiled[5] - '0');
    const long long year = (kCompiled[7] - '0') * 1000LL + (kCompiled[8] - '0') * 100LL +
                           (kCompiled[9] - '0') * 10LL + (kCompiled[10] - '0');
    return isoDate(year, month, day);
}

LicenseAuthority& LicenseAuthority::instance() {
    static LicenseAuthority authority;
    return authority;
}

LicenseStatus LicenseAuthority::apply(std::string_view token) {
    LicenseStatus status = evaluateLicense(token, kLicensePublicKey, todayIsoDate(), buildIsoDate());
    if (status.state == LicenseState::Licensed) {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_active = status;
    }
    return status;
}

LicenseStatus LicenseAuthority::current() const {
    std::lock_guard<std::mutex> lock(m_mutex);
    return m_active;
}

bool LicenseAuthority::isLicensed() const {
    std::lock_guard<std::mutex> lock(m_mutex);
    return m_active.state == LicenseState::Licensed;
}

void LicenseAuthority::clear() {
    std::lock_guard<std::mutex> lock(m_mutex);
    m_active = LicenseStatus{};
}

} // namespace aladyn::engine::licensing
