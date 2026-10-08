#include "LicenseToken.hpp"

#include <cctype>
#include <set>

namespace aladyn::engine::licensing {
namespace {

constexpr std::string_view kPrefix = "LUMENIA1-";
constexpr size_t kSignatureBytes = 64;
constexpr size_t kMaxPayloadBytes = 4096;

int base32Value(char c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    if (c >= 'a' && c <= 'z') return c - 'a';
    if (c >= '2' && c <= '7') return 26 + (c - '2');
    return -1;
}

std::string withoutWhitespace(std::string_view text) {
    std::string out;
    out.reserve(text.size());
    for (char c : text) {
        if (!std::isspace(static_cast<unsigned char>(c))) out.push_back(c);
    }
    return out;
}

bool assignField(LicenseClaims& claims, std::string_view key, const std::string& value) {
    if (key == "v") {
        if (value != "1") return false;
        claims.version = 1;
    } else if (key == "id") {
        claims.licenseId = value;
    } else if (key == "sku") {
        claims.sku = value;
    } else if (key == "name") {
        claims.holderName = value;
    } else if (key == "mail") {
        claims.emailSha256 = value;
    } else if (key == "iat") {
        claims.issuedOn = value;
    } else if (key == "upd") {
        claims.updatesUntil = value;
    } else if (key == "exp") {
        claims.expiresOn = value;
    } else if (key == "mid") {
        claims.machineId = value;
    } else {
        return false;
    }
    return true;
}

bool optionalDate(const std::string& value) {
    return value.empty() || isIsoDate(value);
}

} // namespace

bool isIsoDate(std::string_view text) {
    if (text.size() != 10 || text[4] != '-' || text[7] != '-') return false;
    for (size_t i : {0u, 1u, 2u, 3u, 5u, 6u, 8u, 9u}) {
        if (text[i] < '0' || text[i] > '9') return false;
    }
    const int month = (text[5] - '0') * 10 + (text[6] - '0');
    const int day = (text[8] - '0') * 10 + (text[9] - '0');
    return month >= 1 && month <= 12 && day >= 1 && day <= 31;
}

std::optional<std::vector<uint8_t>> decodeBase32(std::string_view text) {
    std::vector<uint8_t> out;
    out.reserve(text.size() * 5 / 8);
    uint32_t buffer = 0;
    int bits = 0;
    for (char c : text) {
        const int value = base32Value(c);
        if (value < 0) return std::nullopt;
        buffer = (buffer << 5) | static_cast<uint32_t>(value);
        bits += 5;
        if (bits >= 8) {
            bits -= 8;
            out.push_back(static_cast<uint8_t>((buffer >> bits) & 0xFFu));
            buffer &= (1u << bits) - 1u;
        }
    }
    // What is left must be the zero padding of the last character.
    if (bits >= 5 || buffer != 0) return std::nullopt;
    return out;
}

std::optional<EncodedLicense> splitToken(std::string_view token) {
    const std::string compact = withoutWhitespace(token);
    if (compact.size() <= kPrefix.size() || compact.compare(0, kPrefix.size(), kPrefix) != 0) {
        return std::nullopt;
    }
    const std::string_view body = std::string_view(compact).substr(kPrefix.size());
    const size_t dot = body.find('.');
    if (dot == std::string_view::npos || body.find('.', dot + 1) != std::string_view::npos) {
        return std::nullopt;
    }
    auto payload = decodeBase32(body.substr(0, dot));
    auto signature = decodeBase32(body.substr(dot + 1));
    if (!payload || !signature || payload->empty() || payload->size() > kMaxPayloadBytes ||
        signature->size() != kSignatureBytes) {
        return std::nullopt;
    }
    return EncodedLicense{std::move(*payload), std::move(*signature)};
}

std::optional<LicenseClaims> parseClaims(const std::vector<uint8_t>& payload) {
    LicenseClaims claims;
    std::set<std::string, std::less<>> seen;
    const std::string text(payload.begin(), payload.end());
    size_t start = 0;
    while (start < text.size()) {
        size_t end = text.find('\n', start);
        if (end == std::string::npos) end = text.size();
        const std::string_view line = std::string_view(text).substr(start, end - start);
        start = end + 1;
        if (line.empty()) continue;
        const size_t eq = line.find('=');
        if (eq == std::string_view::npos || eq == 0) return std::nullopt;
        const std::string key(line.substr(0, eq));
        const std::string value(line.substr(eq + 1));
        if (value.find('\r') != std::string::npos || value.find('\0') != std::string::npos) return std::nullopt;
        if (!seen.insert(key).second || !assignField(claims, key, value)) return std::nullopt;
    }
    const bool complete = claims.version == 1 && !claims.licenseId.empty() && !claims.sku.empty() &&
                          isIsoDate(claims.issuedOn) && optionalDate(claims.updatesUntil) &&
                          optionalDate(claims.expiresOn);
    if (!complete) return std::nullopt;
    return claims;
}

} // namespace aladyn::engine::licensing
