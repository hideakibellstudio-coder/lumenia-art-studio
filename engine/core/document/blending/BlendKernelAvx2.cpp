// O laço AVX2 do Normal em gama linear de 8 bits (BlendKernel.hpp), oito pixels por vez.
//
// Compilado SEM -mavx2 no módulo inteiro: só as funções daqui levam o atributo de alvo, e só são chamadas
// depois de `cpuHasAvx2()`. É por isso que o binário distribuído (escalar) roda em qualquer CPU e usa AVX2
// onde ela existir.
//
// Cada operação é a mesma do laço escalar, na mesma ordem e em float de 32 bits (soma e produto separados,
// nunca fundidos: o alvo é "avx2", sem "fma"), então o resultado é igual bit a bit.
#include "BlendKernelInternal.hpp"
#include "BlendEquations.hpp"

#if (defined(__x86_64__) || defined(_M_X64) || defined(__i386__) || defined(_M_IX86)) && (defined(__GNUC__) || defined(_MSC_VER))
#define ALADYN_AVX2_KERNEL 1
#include <immintrin.h>
#if defined(_MSC_VER) && !defined(__clang__)
#include <intrin.h>
#endif
#endif

namespace aladyn::engine::document::blending {

#ifdef ALADYN_AVX2_KERNEL

#if defined(__GNUC__)
#define ALADYN_TARGET_AVX2 __attribute__((target("avx2")))
#else
#define ALADYN_TARGET_AVX2
#endif

bool cpuHasAvx2() noexcept {
#if defined(__GNUC__)
    return __builtin_cpu_supports("avx2") != 0;
#else
    int info[4] = {0, 0, 0, 0};
    __cpuid(info, 0);
    if (info[0] < 7) return false;
    __cpuid(info, 1);
    const bool osXsave = (info[2] & (1 << 27)) != 0;
    const bool avx = (info[2] & (1 << 28)) != 0;
    if (!osXsave || !avx) return false;
    if ((_xgetbv(0) & 0x6) != 0x6) return false;  // o sistema guarda o estado dos registradores YMM
    __cpuidex(info, 7, 0);
    return (info[1] & (1 << 5)) != 0;
#endif
}

namespace {

// Um canal de oito pixels: tabela sRGB -> linear da origem e do destino, mistura, índice de 12 bits e tabela
// linear -> sRGB.
ALADYN_TARGET_AVX2 inline __m256i mixChannel(
    const KernelTables& tables, __m256 alpha, __m256 inverse, __m256i sourceChannel, __m256i destinationChannel
) noexcept {
    const __m256 linear = _mm256_add_ps(
        _mm256_mul_ps(_mm256_i32gather_ps(tables.srgbToLinear, sourceChannel, 4), alpha),
        _mm256_mul_ps(_mm256_i32gather_ps(tables.srgbToLinear, destinationChannel, 4), inverse));
    __m256i index = _mm256_cvttps_epi32(_mm256_add_ps(_mm256_mul_ps(linear, _mm256_set1_ps(4095.0f)), _mm256_set1_ps(0.5f)));
    index = _mm256_min_epi32(_mm256_max_epi32(index, _mm256_setzero_si256()), _mm256_set1_epi32(4095));
    return _mm256_and_si256(
        _mm256_i32gather_epi32(reinterpret_cast<const int*>(tables.linearToSrgb), index, 1), _mm256_set1_epi32(255));
}

} // namespace

ALADYN_TARGET_AVX2 void rowNormalLinear8Avx2(
    const BlendPlan& plan, const utils::ColorRGBA* src, utils::ColorRGBA* dst, size_t count
) noexcept {
    const KernelTables& tables = *plan.tables;
    const __m256i channelMask = _mm256_set1_epi32(255);
    const __m256i opaqueAlpha = _mm256_set1_epi32(static_cast<int>(0xFF000000u));
    const __m256i colorBits = _mm256_set1_epi32(0x00FFFFFF);
    const __m256 one = _mm256_set1_ps(1.0f);
    const __m256 zero = _mm256_setzero_ps();

    size_t i = 0;
    for (; i + 8 <= count; i += 8) {
        const __m256i s = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(src + i));
        const __m256i sourceAlpha = _mm256_srli_epi32(s, 24);
        const __m256i transparent = _mm256_cmpeq_epi32(sourceAlpha, _mm256_setzero_si256());
        if (_mm256_movemask_epi8(transparent) == -1) continue;  // oito pixels sem tinta

        const __m256i d = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(dst + i));
        const __m256i destinationOpaque = _mm256_cmpeq_epi32(_mm256_srli_epi32(d, 24), channelMask);
        if (_mm256_movemask_epi8(destinationOpaque) != -1) {
            // Destino com alfa: a definição, pixel a pixel (a mistura com alfa tem divisão e desvios).
            for (size_t lane = 0; lane < 8; ++lane) {
                if (src[i + lane].a == 0) continue;
                dst[i + lane] = blendPixel(src[i + lane], plan.opacity, dst[i + lane], plan.mode, true, false);
            }
            continue;
        }

        const __m256 alpha = _mm256_i32gather_ps(plan.alphaF, sourceAlpha, 4);
        const __m256 inverse = _mm256_sub_ps(one, alpha);
        const __m256i red = mixChannel(tables, alpha, inverse, _mm256_and_si256(s, channelMask), _mm256_and_si256(d, channelMask));
        const __m256i green = mixChannel(tables, alpha, inverse, _mm256_and_si256(_mm256_srli_epi32(s, 8), channelMask),
                                         _mm256_and_si256(_mm256_srli_epi32(d, 8), channelMask));
        const __m256i blue = mixChannel(tables, alpha, inverse, _mm256_and_si256(_mm256_srli_epi32(s, 16), channelMask),
                                        _mm256_and_si256(_mm256_srli_epi32(d, 16), channelMask));
        __m256i mixed = _mm256_or_si256(_mm256_or_si256(red, _mm256_slli_epi32(green, 8)),
                                        _mm256_or_si256(_mm256_slli_epi32(blue, 16), opaqueAlpha));

        // alfa efetivo >= 1: a cor da origem cobre; alfa efetivo <= 0 ou origem transparente: o destino fica.
        const __m256i covers = _mm256_castps_si256(_mm256_cmp_ps(alpha, one, _CMP_GE_OQ));
        mixed = _mm256_blendv_epi8(mixed, _mm256_or_si256(_mm256_and_si256(s, colorBits), opaqueAlpha), covers);
        const __m256i keeps = _mm256_or_si256(transparent, _mm256_castps_si256(_mm256_cmp_ps(alpha, zero, _CMP_LE_OQ)));
        mixed = _mm256_blendv_epi8(mixed, d, keeps);
        _mm256_storeu_si256(reinterpret_cast<__m256i*>(dst + i), mixed);
    }
    for (; i < count; ++i) {
        if (src[i].a == 0) continue;
        dst[i] = blendPixel(src[i], plan.opacity, dst[i], plan.mode, true, false);
    }
}

#else  // sem AVX2 neste alvo: o nível nunca é escolhido

bool cpuHasAvx2() noexcept { return false; }

void rowNormalLinear8Avx2(const BlendPlan& plan, const utils::ColorRGBA* src, utils::ColorRGBA* dst, size_t count) noexcept {
    for (size_t i = 0; i < count; ++i) {
        if (src[i].a == 0) continue;
        dst[i] = blendPixel(src[i], plan.opacity, dst[i], plan.mode, plan.linearGamma, plan.deepColor);
    }
}

#endif

} // namespace aladyn::engine::document::blending
