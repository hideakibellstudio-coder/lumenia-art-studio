#ifndef ALADYN_ENGINE_LICENSING_SIGNATURE_VERIFIER_HPP
#define ALADYN_ENGINE_LICENSING_SIGNATURE_VERIFIER_HPP

#include <array>
#include <cstddef>
#include <cstdint>

namespace aladyn::engine::licensing {

// An ECDSA P-256 public key as X || Y, 32 bytes each, big-endian.
using PublicKey = std::array<uint8_t, 64>;

// True on platforms where the operating system verifies signatures for us
// (Windows CNG, bcrypt.dll). Elsewhere every license is "unsupported": there is
// no hand-written cryptography in the engine.
bool signatureVerificationAvailable();

// ECDSA P-256 over SHA-256 of `message`; `signature` is r || s (64 bytes, big-endian).
bool verifyEcdsaP256Sha256(const PublicKey& publicKey, const uint8_t* message, size_t messageSize,
                           const uint8_t* signature, size_t signatureSize);

} // namespace aladyn::engine::licensing

#endif // ALADYN_ENGINE_LICENSING_SIGNATURE_VERIFIER_HPP
