#include "Lz4Codec.hpp"
#include <algorithm>
#include <cstring>

namespace aladyn::engine::compression {

namespace {
constexpr size_t HASH_BITS = 12;
constexpr size_t HASH_SIZE = 1 << HASH_BITS;

inline size_t hash4(const uint8_t* p) noexcept {
    uint32_t v;
    std::memcpy(&v, p, 4);
    return static_cast<size_t>((v * 2654435761U) >> (32 - HASH_BITS));
}
} // namespace

size_t Lz4Codec::compressBlock(
    const uint8_t* src,
    size_t srcSize,
    uint8_t* dst,
    size_t dstCapacity
) noexcept {
    if (!src || srcSize == 0 || !dst || dstCapacity < maxCompressedSize(srcSize)) {
        return 0;
    }

    if (srcSize < 13) {
        if (dstCapacity < srcSize + 2) return 0;
        uint8_t* op = dst;
        if (srcSize < 15) {
            *op++ = static_cast<uint8_t>(srcSize << 4);
        } else {
            *op++ = static_cast<uint8_t>(15 << 4);
            size_t extra = srcSize - 15;
            while (extra >= 255) { *op++ = 255; extra -= 255; }
            *op++ = static_cast<uint8_t>(extra);
        }
        std::memcpy(op, src, srcSize);
        op += srcSize;
        return static_cast<size_t>(op - dst);
    }

    const uint8_t* hashTable[HASH_SIZE] = {nullptr};

    const uint8_t* ip = src;
    const uint8_t* const srcEnd = src + srcSize;
    const uint8_t* const matchLimit = srcEnd - 12;
    const uint8_t* anchor = ip;
    uint8_t* op = dst;
    const uint8_t* const dstEnd = dst + dstCapacity;

    while (ip < matchLimit) {
        const size_t h = hash4(ip);
        const uint8_t* ref = hashTable[h];
        hashTable[h] = ip;

        if (ref && (ip - ref) <= 65535 && (ip - ref) > 0) {
            uint32_t v1, v2;
            std::memcpy(&v1, ip, 4);
            std::memcpy(&v2, ref, 4);
            if (v1 == v2) {
                const size_t litLen = static_cast<size_t>(ip - anchor);

                size_t matchLen = 4;
                while (ip + matchLen < srcEnd - 5 && ref[matchLen] == ip[matchLen]) {
                    ++matchLen;
                }

                const size_t tokenLit = std::min(litLen, static_cast<size_t>(15));
                const size_t tokenMatch = std::min(matchLen - 4, static_cast<size_t>(15));
                if (op >= dstEnd) return 0;
                *op++ = static_cast<uint8_t>((tokenLit << 4) | tokenMatch);

                if (litLen >= 15) {
                    size_t extra = litLen - 15;
                    while (extra >= 255) {
                        if (op >= dstEnd) return 0;
                        *op++ = 255;
                        extra -= 255;
                    }
                    if (op >= dstEnd) return 0;
                    *op++ = static_cast<uint8_t>(extra);
                }

                if (op + litLen > dstEnd) return 0;
                std::memcpy(op, anchor, litLen);
                op += litLen;

                const uint16_t offset = static_cast<uint16_t>(ip - ref);
                if (op + 2 > dstEnd) return 0;
                *op++ = static_cast<uint8_t>(offset & 0xFF);
                *op++ = static_cast<uint8_t>((offset >> 8) & 0xFF);

                if (matchLen - 4 >= 15) {
                    size_t extra = (matchLen - 4) - 15;
                    while (extra >= 255) {
                        if (op >= dstEnd) return 0;
                        *op++ = 255;
                        extra -= 255;
                    }
                    if (op >= dstEnd) return 0;
                    *op++ = static_cast<uint8_t>(extra);
                }

                ip += matchLen;
                anchor = ip;
                continue;
            }
        }
        ++ip;
    }

    const size_t lastLitLen = static_cast<size_t>(srcEnd - anchor);
    if (lastLitLen > 0) {
        const size_t tokenLit = std::min(lastLitLen, static_cast<size_t>(15));
        if (op >= dstEnd) return 0;
        *op++ = static_cast<uint8_t>(tokenLit << 4);

        if (lastLitLen >= 15) {
            size_t extra = lastLitLen - 15;
            while (extra >= 255) {
                if (op >= dstEnd) return 0;
                *op++ = 255;
                extra -= 255;
            }
            if (op >= dstEnd) return 0;
            *op++ = static_cast<uint8_t>(extra);
        }

        if (op + lastLitLen > dstEnd) return 0;
        std::memcpy(op, anchor, lastLitLen);
        op += lastLitLen;
    }

    return static_cast<size_t>(op - dst);
}

bool Lz4Codec::decompressBlock(
    const uint8_t* src,
    size_t srcSize,
    uint8_t* dst,
    size_t dstCapacity
) noexcept {
    if (!src || srcSize == 0 || !dst || dstCapacity == 0) {
        return false;
    }

    const uint8_t* ip = src;
    const uint8_t* const ipEnd = src + srcSize;
    uint8_t* op = dst;
    uint8_t* const opEnd = dst + dstCapacity;

    while (ip < ipEnd) {
        const uint8_t token = *ip++;
        size_t litLen = (token >> 4);

        if (litLen == 15) {
            while (ip < ipEnd && *ip == 255) {
                litLen += 255;
                ++ip;
            }
            if (ip >= ipEnd) return false;
            litLen += *ip++;
        }

        if (op + litLen > opEnd || ip + litLen > ipEnd) return false;
        std::memcpy(op, ip, litLen);
        op += litLen;
        ip += litLen;

        if (ip >= ipEnd) break;

        if (ip + 2 > ipEnd) return false;
        const uint16_t offset = static_cast<uint16_t>(ip[0]) | (static_cast<uint16_t>(ip[1]) << 8);
        ip += 2;

        if (offset == 0 || (op - offset) < dst) return false;

        size_t matchLen = (token & 0x0F) + 4;
        if ((token & 0x0F) == 15) {
            while (ip < ipEnd && *ip == 255) {
                matchLen += 255;
                ++ip;
            }
            if (ip >= ipEnd) return false;
            matchLen += *ip++;
        }

        if (op + matchLen > opEnd) return false;

        const uint8_t* matchSrc = op - offset;
        for (size_t m = 0; m < matchLen; ++m) {
            op[m] = matchSrc[m];
        }
        op += matchLen;
    }

    return (op == opEnd);
}

std::vector<uint8_t> Lz4Codec::compress(const uint8_t* src, size_t srcSize) {
    if (!src || srcSize == 0) return {};
    std::vector<uint8_t> result(maxCompressedSize(srcSize));
    size_t compSize = compressBlock(src, srcSize, result.data(), result.size());
    if (compSize == 0) return {};
    result.resize(compSize);
    result.shrink_to_fit();
    return result;
}

bool Lz4Codec::decompress(const std::vector<uint8_t>& compressed, std::vector<uint8_t>& dst) {
    if (compressed.empty() || dst.empty()) return false;
    return decompressBlock(compressed.data(), compressed.size(), dst.data(), dst.size());
}

} // namespace aladyn::engine::compression
