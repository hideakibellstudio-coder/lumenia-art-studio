// O laço AVX2 do Normal em gama linear de 16 bits (BlendKernel16.hpp), oito pixels por vez.
//
// Compilado SEM -mavx2 no módulo inteiro, como `BlendKernelAvx2.cpp`: só as funções daqui levam o atributo de alvo e
// só são escolhidas depois de `cpuHasAvx2()`. Cada operação é a do laço escalar (`rowNormal16Linear`), na mesma
// ordem e no mesmo tipo (o alfa em double, as tabelas e a mistura em float de 32 bits, soma e produto separados, sem
// fusão: o alvo é "avx2", sem "fma"), então o resultado é igual bit a bit; `tests/native/blend16_checks.cpp` confere
// em milhões de pixels.
//
// Só o caso comum é vetorizado: destino opaco nos oito pixels (o fator do destino é então 1 - alfa e o alfa de saída é
// 65535). Qualquer outro grupo de oito vai para a linha escalar, que tem a divisão e os desvios do alfa parcial.
#include "BlendKernel16Internal.hpp"
#include "BlendEquations16.hpp"
#include "../../color/LinearColorSpace16.hpp"

#if (defined(__x86_64__) || defined(_M_X64) || defined(__i386__) || defined(_M_IX86)) && (defined(__GNUC__) || defined(_MSC_VER))
#define ALADYN_AVX2_KERNEL16 1
#include <immintrin.h>
#endif

namespace aladyn::engine::document::blending {

#ifdef ALADYN_AVX2_KERNEL16

#if defined(__GNUC__)
#define ALADYN_TARGET_AVX2_16 __attribute__((target("avx2")))
#else
#define ALADYN_TARGET_AVX2_16
#endif

namespace {

using utils::ColorRGBA16;

// Os quatro alfas efetivos (double) de quatro pixels: `detail16::effectiveAlpha`, igual.
ALADYN_TARGET_AVX2_16 inline __m256d effectiveAlpha4(__m128i alpha, __m256d opacity) noexcept {
    const __m256d unit = _mm256_mul_pd(_mm256_cvtepi32_pd(alpha), _mm256_set1_pd(detail16::kInv65535));
    const __m256d full = _mm256_castsi256_pd(_mm256_cvtepi32_epi64(_mm_cmpeq_epi32(alpha, _mm_set1_epi32(65535))));
    return _mm256_mul_pd(_mm256_blendv_pd(unit, _mm256_set1_pd(1.0), full), opacity);
}

ALADYN_TARGET_AVX2_16 inline __m256 joinFloats(__m128 low, __m128 high) noexcept {
    return _mm256_insertf128_ps(_mm256_castps128_ps256(low), high, 1);
}

// Um canal de oito pixels: as duas tabelas, a mistura e a codificação `color::linearToSrgb16`.
ALADYN_TARGET_AVX2_16 inline __m256i mixChannel(
    const color::Srgb16Tables& tables, __m256 source, __m256 destination, __m256i sourceChannel, __m256i destinationChannel
) noexcept {
    const __m256 linear = _mm256_add_ps(_mm256_mul_ps(_mm256_i32gather_ps(tables.toLinear, sourceChannel, 4), source),
                                        _mm256_mul_ps(_mm256_i32gather_ps(tables.toLinear, destinationChannel, 4), destination));
    // A saturação da escalar; um NaN cai em 0 (`max` devolve o segundo operando).
    const __m256 clamped = _mm256_min_ps(_mm256_max_ps(linear, _mm256_setzero_ps()), _mm256_set1_ps(1.0f));
    const __m256 position = _mm256_mul_ps(clamped, _mm256_set1_ps(static_cast<float>(color::Srgb16Tables::kEncodeBuckets)));
    const __m256i bucket = _mm256_cvttps_epi32(position);
    const __m256 fraction = _mm256_sub_ps(position, _mm256_cvtepi32_ps(bucket));
    const __m256 low = _mm256_i32gather_ps(tables.encode, bucket, 4);
    const __m256 high = _mm256_i32gather_ps(tables.encode + 1, bucket, 4);
    const __m256 value = _mm256_add_ps(_mm256_add_ps(low, _mm256_mul_ps(_mm256_sub_ps(high, low), fraction)), _mm256_set1_ps(0.5f));
    return _mm256_cvttps_epi32(value);
}

} // namespace

ALADYN_TARGET_AVX2_16 void rowNormal16LinearAvx2(const BlendPlan16& plan, const ColorRGBA16* src, ColorRGBA16* dst, size_t count) noexcept {
    const color::Srgb16Tables& tables = color::srgb16Tables();
    const __m256i low16 = _mm256_set1_epi32(0xFFFF);
    const __m256i opaqueHigh = _mm256_set1_epi32(static_cast<int>(0xFFFF0000u));
    const __m256i opaque = _mm256_set1_epi32(65535);
    const __m256d opacity = _mm256_set1_pd(plan.opacity);
    const __m256d one = _mm256_set1_pd(1.0);
    const __m256 oneF = _mm256_set1_ps(1.0f);

    size_t i = 0;
    for (; i + 8 <= count; i += 8) {
        // Quatro pixels são dois grupos de 128 bits de (r|g, b|a); `shuffle` junta os r|g e os b|a de oito pixels
        // na ordem 0 1 4 5 | 2 3 6 7. A ordem não importa dentro da conta, e `unpack` a devolve à de memória.
        const __m256 s0 = _mm256_castsi256_ps(_mm256_loadu_si256(reinterpret_cast<const __m256i*>(src + i)));
        const __m256 s1 = _mm256_castsi256_ps(_mm256_loadu_si256(reinterpret_cast<const __m256i*>(src + i + 4)));
        const __m256i srcRg = _mm256_castps_si256(_mm256_shuffle_ps(s0, s1, _MM_SHUFFLE(2, 0, 2, 0)));
        const __m256i srcBa = _mm256_castps_si256(_mm256_shuffle_ps(s0, s1, _MM_SHUFFLE(3, 1, 3, 1)));
        const __m256i sourceAlpha = _mm256_srli_epi32(srcBa, 16);
        const __m256i transparent = _mm256_cmpeq_epi32(sourceAlpha, _mm256_setzero_si256());
        if (_mm256_movemask_epi8(transparent) == -1) continue;  // oito pixels sem tinta

        const __m256 d0 = _mm256_castsi256_ps(_mm256_loadu_si256(reinterpret_cast<const __m256i*>(dst + i)));
        const __m256 d1 = _mm256_castsi256_ps(_mm256_loadu_si256(reinterpret_cast<const __m256i*>(dst + i + 4)));
        const __m256i dstRg = _mm256_castps_si256(_mm256_shuffle_ps(d0, d1, _MM_SHUFFLE(2, 0, 2, 0)));
        const __m256i dstBa = _mm256_castps_si256(_mm256_shuffle_ps(d0, d1, _MM_SHUFFLE(3, 1, 3, 1)));
        if (_mm256_movemask_epi8(_mm256_cmpeq_epi32(_mm256_srli_epi32(dstBa, 16), opaque)) != -1) {
            rowNormal16Linear(plan, src + i, dst + i, 8);  // destino com alfa: a conta com divisão e desvios
            continue;
        }

        const __m256d alphaLow = effectiveAlpha4(_mm256_castsi256_si128(sourceAlpha), opacity);
        const __m256d alphaHigh = effectiveAlpha4(_mm256_extracti128_si256(sourceAlpha, 1), opacity);
        const __m256 source = joinFloats(_mm256_cvtpd_ps(alphaLow), _mm256_cvtpd_ps(alphaHigh));
        const __m256 destination = joinFloats(_mm256_cvtpd_ps(_mm256_sub_pd(one, alphaLow)), _mm256_cvtpd_ps(_mm256_sub_pd(one, alphaHigh)));

        const __m256i red = mixChannel(tables, source, destination, _mm256_and_si256(srcRg, low16), _mm256_and_si256(dstRg, low16));
        const __m256i green = mixChannel(tables, source, destination, _mm256_srli_epi32(srcRg, 16), _mm256_srli_epi32(dstRg, 16));
        const __m256i blue = mixChannel(tables, source, destination, _mm256_and_si256(srcBa, low16), _mm256_and_si256(dstBa, low16));
        __m256i mixedRg = _mm256_or_si256(red, _mm256_slli_epi32(green, 16));
        __m256i mixedBa = _mm256_or_si256(blue, opaqueHigh);

        // Alfa efetivo >= 1: a cor da origem cobre, com alfa cheio; sem tinta (alfa 0, ou efetivo <= 0): o destino fica.
        const __m256i covers = _mm256_castps_si256(_mm256_cmp_ps(source, oneF, _CMP_GE_OQ));
        mixedRg = _mm256_blendv_epi8(mixedRg, srcRg, covers);
        mixedBa = _mm256_blendv_epi8(mixedBa, _mm256_or_si256(_mm256_and_si256(srcBa, low16), opaqueHigh), covers);
        const __m256i keeps = _mm256_or_si256(transparent, _mm256_castps_si256(_mm256_cmp_ps(source, _mm256_setzero_ps(), _CMP_LE_OQ)));
        mixedRg = _mm256_blendv_epi8(mixedRg, dstRg, keeps);
        mixedBa = _mm256_blendv_epi8(mixedBa, dstBa, keeps);
        _mm256_storeu_si256(reinterpret_cast<__m256i*>(dst + i), _mm256_unpacklo_epi32(mixedRg, mixedBa));
        _mm256_storeu_si256(reinterpret_cast<__m256i*>(dst + i + 4), _mm256_unpackhi_epi32(mixedRg, mixedBa));
    }
    if (i < count) rowNormal16Linear(plan, src + i, dst + i, count - i);
}

#else  // sem AVX2 neste alvo: o nível nunca é escolhido

void rowNormal16LinearAvx2(const BlendPlan16& plan, const utils::ColorRGBA16* src, utils::ColorRGBA16* dst, size_t count) noexcept {
    rowNormal16Linear(plan, src, dst, count);
}

#endif

} // namespace aladyn::engine::document::blending
