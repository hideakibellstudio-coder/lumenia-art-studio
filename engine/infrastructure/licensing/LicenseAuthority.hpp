#ifndef ALADYN_ENGINE_LICENSING_LICENSE_AUTHORITY_HPP
#define ALADYN_ENGINE_LICENSING_LICENSE_AUTHORITY_HPP

#include "LicenseToken.hpp"
#include "SignatureVerifier.hpp"

#include <mutex>
#include <string>
#include <string_view>

namespace aladyn::engine::licensing {

enum class LicenseState {
    Unlicensed,      // no license applied in this process
    Licensed,
    Malformed,       // not a token, or a payload the engine does not understand
    BadSignature,    // not signed by the key this build trusts
    Expired,         // past "exp"
    Revoked,         // its id is in RevokedLicenses.hpp
    UpdatesExpired,  // this build is newer than "upd": the license covers older builds only
    Unsupported,     // no signature verifier on this platform, or a machine-bound license (phase 2)
};

std::string_view licenseStateName(LicenseState state);

struct LicenseStatus {
    LicenseState state = LicenseState::Unlicensed;
    LicenseClaims claims;  // filled whenever the signature was valid
};

// Evaluates a token against `publicKey` without touching any state. `today` and
// `buildDate` are "YYYY-MM-DD". Pure: tests pass their own key and dates.
LicenseStatus evaluateLicense(std::string_view token, const PublicKey& publicKey,
                              std::string_view today, std::string_view buildDate);

// Today in UTC and the day this binary was compiled, both "YYYY-MM-DD".
std::string todayIsoDate();
std::string buildIsoDate();

// The license of this process, checked against the key compiled into the engine
// (LicensePublicKey.hpp). One per process: the license belongs to the user, not
// to a document. Thread-safe.
class LicenseAuthority {
public:
    static LicenseAuthority& instance();

    // Evaluates `token`; only a valid license replaces the active one, so pasting
    // a bad key never takes away a good one.
    LicenseStatus apply(std::string_view token);
    LicenseStatus current() const;
    bool isLicensed() const;
    void clear();

private:
    LicenseAuthority() = default;
    mutable std::mutex m_mutex;
    LicenseStatus m_active;
};

} // namespace aladyn::engine::licensing

#endif // ALADYN_ENGINE_LICENSING_LICENSE_AUTHORITY_HPP
