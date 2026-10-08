#ifndef ALADYN_ENGINE_LICENSING_LICENSE_TOKEN_HPP
#define ALADYN_ENGINE_LICENSING_LICENSE_TOKEN_HPP

#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace aladyn::engine::licensing {

// What a license says, exactly as the generator signed it. Dates are "YYYY-MM-DD";
// an empty date means "no limit". Only version 1 exists.
struct LicenseClaims {
    int version = 0;
    std::string licenseId;     // "L-000123": unique, the key of the revocation list
    std::string sku;           // the product edition ("pro")
    std::string holderName;    // shown as "Licensed to ..."
    std::string emailSha256;   // the buyer's e-mail only as a hash
    std::string issuedOn;
    std::string updatesUntil;  // builds dated after this day do not accept the license
    std::string expiresOn;     // a subscription or a trial; empty for a perpetual license
    std::string machineId;     // reserved for online activation (phase 2); must be empty today
};

// The two signed halves of "LUMENIA1-<base32 payload>.<base32 signature>".
struct EncodedLicense {
    std::vector<uint8_t> payload;
    std::vector<uint8_t> signature;
};

// RFC 4648 base32 without padding, either case. Anything else (or non-zero
// trailing bits) is not a license: std::nullopt.
std::optional<std::vector<uint8_t>> decodeBase32(std::string_view text);

// Splits a pasted token. Whitespace and line breaks are ignored, so a token
// wrapped by an e-mail client still reads. The signature is always 64 bytes.
std::optional<EncodedLicense> splitToken(std::string_view token);

// The payload is UTF-8 "key=value" lines. Unknown keys, repeated keys, a missing
// required key or a malformed date make the whole payload invalid.
std::optional<LicenseClaims> parseClaims(const std::vector<uint8_t>& payload);

bool isIsoDate(std::string_view text);

} // namespace aladyn::engine::licensing

#endif // ALADYN_ENGINE_LICENSING_LICENSE_TOKEN_HPP
