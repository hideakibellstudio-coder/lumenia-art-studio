#include "SignatureVerifier.hpp"

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <bcrypt.h>
#include <cstring>
#include <vector>
#ifdef _MSC_VER
#pragma comment(lib, "bcrypt.lib")
#endif
#endif

namespace aladyn::engine::licensing {

#ifdef _WIN32
namespace {

// Closes a CNG handle on every path out of the verification.
struct AlgorithmHandle {
    BCRYPT_ALG_HANDLE handle = nullptr;
    ~AlgorithmHandle() { if (handle) BCryptCloseAlgorithmProvider(handle, 0); }
};
struct HashHandle {
    BCRYPT_HASH_HANDLE handle = nullptr;
    ~HashHandle() { if (handle) BCryptDestroyHash(handle); }
};
struct KeyHandle {
    BCRYPT_KEY_HANDLE handle = nullptr;
    ~KeyHandle() { if (handle) BCryptDestroyKey(handle); }
};

bool succeeded(NTSTATUS status) { return status >= 0; }

bool sha256(const uint8_t* message, size_t size, UCHAR (&digest)[32]) {
    AlgorithmHandle algorithm;
    HashHandle hash;
    if (!succeeded(BCryptOpenAlgorithmProvider(&algorithm.handle, BCRYPT_SHA256_ALGORITHM, nullptr, 0))) return false;
    if (!succeeded(BCryptCreateHash(algorithm.handle, &hash.handle, nullptr, 0, nullptr, 0, 0))) return false;
    if (size > 0 && !succeeded(BCryptHashData(hash.handle, const_cast<PUCHAR>(message), static_cast<ULONG>(size), 0))) {
        return false;
    }
    return succeeded(BCryptFinishHash(hash.handle, digest, sizeof(digest), 0));
}

} // namespace

bool signatureVerificationAvailable() { return true; }

bool verifyEcdsaP256Sha256(const PublicKey& publicKey, const uint8_t* message, size_t messageSize,
                           const uint8_t* signature, size_t signatureSize) {
    if (!message || !signature || signatureSize != 64 || messageSize > 0xFFFFFFu) return false;
    UCHAR digest[32] = {};
    if (!sha256(message, messageSize, digest)) return false;

    // BCRYPT_ECCKEY_BLOB header followed by X and Y.
    std::vector<UCHAR> blob(sizeof(BCRYPT_ECCKEY_BLOB) + publicKey.size());
    BCRYPT_ECCKEY_BLOB header{};
    header.dwMagic = BCRYPT_ECDSA_PUBLIC_P256_MAGIC;
    header.cbKey = 32;
    std::memcpy(blob.data(), &header, sizeof(header));
    std::memcpy(blob.data() + sizeof(header), publicKey.data(), publicKey.size());

    AlgorithmHandle algorithm;
    KeyHandle key;
    if (!succeeded(BCryptOpenAlgorithmProvider(&algorithm.handle, BCRYPT_ECDSA_P256_ALGORITHM, nullptr, 0))) return false;
    if (!succeeded(BCryptImportKeyPair(algorithm.handle, nullptr, BCRYPT_ECCPUBLIC_BLOB, &key.handle,
                                       blob.data(), static_cast<ULONG>(blob.size()), 0))) {
        return false;
    }
    return succeeded(BCryptVerifySignature(key.handle, nullptr, digest, sizeof(digest),
                                           const_cast<PUCHAR>(signature), static_cast<ULONG>(signatureSize), 0));
}

#else

bool signatureVerificationAvailable() { return false; }

bool verifyEcdsaP256Sha256(const PublicKey&, const uint8_t*, size_t, const uint8_t*, size_t) { return false; }

#endif

} // namespace aladyn::engine::licensing
