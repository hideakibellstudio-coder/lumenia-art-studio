#ifndef ALADYN_ENGINE_ENGINE_TELEMETRY_HPP
#define ALADYN_ENGINE_ENGINE_TELEMETRY_HPP

#include <cstdint>
#include <atomic>
#include <vector>
#include <chrono>
#include <algorithm>

namespace aladyn::engine::telemetry {

struct StageMetrics {
    double timeInterpolationUs{0.0};
    double timeRasterDabUs{0.0};
    double timeUndoRecordUs{0.0};
    double timeCompositeUs{0.0};
    uint32_t dabsRendered{0};
    double dirtyWidth{0.0};
    double dirtyHeight{0.0};
    double dirtyAreaPx{0.0};
    uint32_t tilesRecorded{0};
    uint32_t tilesComposited{0};
};

struct RealTimeStrokeMetrics {
    // ⏱️ Latência e Tempo de Processamento Geral
    double lastSegmentLatencyUs{0.0};   // Tempo do último segmento em microssegundos (µs)
    double strokeTotalTimeMs{0.0};       // Duração total do traço ativo em ms
    uint32_t totalDabsInStroke{0};       // Total de carimbos no traço atual
    uint32_t totalDabsPerSecond{0};      // Taxa instantânea de dabs/segundo
    uint32_t inputEventRateHz{0};        // Frequência de eventos de entrada (Hz)

    // 🔬 Decomposição Granular do Pipeline (µs)
    double timeKinematicsUs{0.0};       // Mapeamento dinâmico, estabilização e velocidade
    double timeInterpolationUs{0.0};   // Interpolação adaptativa de dabs e resíduos
    double timeRasterDabUs{0.0};        // Execução de renderDab (cálculo de ponta, grão, papel)
    double timeUndoRecordUs{0.0};       // Backup de tiles no UndoManager
    double timeCompositeUs{0.0};        // Mesclagem de camadas visíveis no Compositor

    // 📐 Pegada Geométrica e Densidade Instantânea
    uint32_t lastDabsRendered{0};       // Dabs emitidos no micro-evento
    double lastDirtyWidth{0.0};         // Largura da bounding box suja (px)
    double lastDirtyHeight{0.0};        // Altura da bounding box suja (px)
    double lastDirtyAreaPx{0.0};        // Área de pixels da bounding box suja
    uint32_t lastTilesRecorded{0};      // Quantidade de tiles salvos no histórico
    uint32_t lastTilesComposited{0};    // Quantidade de tiles mesclados no compositor

    // 🧱 Memória e Gestão de Blocos (Tiles)
    uint32_t activeTileCount{0};         // Total de blocos 128x128 alocados
    uint32_t dirtyTilesLastStroke{0};    // Quantidade de blocos modificados no último traço
    double tileGridMemoryMB{0.0};        // RAM ocupada pelo TileGrid (MB)
    double undoStackMemoryMB{0.0};       // RAM ocupada pela pilha de Undo (MB)
    uint32_t undoStepsCount{0};          // Quantidade de passos de Undo

    // 🖋️ Cinemática e Estabilização
    double rawPressure{0.0};             // Pressão física pura (0.0 .. 1.0)
    double dynamicPressure{0.0};         // Pressão após curva de resposta (0.0 .. 1.0)
    double strokeVelocity{0.0};          // Velocidade vetorial (px/s)
    double stabilizerLagPx{0.0};         // Distância entre caneta e ponto suavizado (px)

    // 🎨 Mini-Motor & SIMD
    int activeEngineId{0};               // ID do mini-motor em uso
#if defined(__AVX2__)
    bool simdActive{true};               // Compilado com AVX2 (SimdSpanBlender vetorizado)
#else
    bool simdActive{false};              // Build escalar (padrão de scripts/build_native.py)
#endif
};

class EngineTelemetryManager {
public:
    EngineTelemetryManager() = default;

    void setEnabled(bool enabled) noexcept {
        m_enabled.store(enabled, std::memory_order_relaxed);
        if (!enabled) {
            cleanup();
        }
    }

    [[nodiscard]] bool isEnabled() const noexcept {
        return m_enabled.load(std::memory_order_relaxed);
    }

    void setDetailedLogging(bool detailed) noexcept {
        m_detailedLogging.store(detailed, std::memory_order_relaxed);
    }

    [[nodiscard]] bool isDetailedLogging() const noexcept {
        return m_detailedLogging.load(std::memory_order_relaxed);
    }

    void onBeginStroke(double pressure, int engineId) {
        if (!isEnabled()) return;
        m_strokeStartTime = std::chrono::high_resolution_clock::now();
        m_lastEventTime = m_strokeStartTime;
        m_currentMetrics.strokeTotalTimeMs = 0.0;
        m_currentMetrics.totalDabsInStroke = 0;
        m_currentMetrics.rawPressure = pressure;
        m_currentMetrics.dynamicPressure = pressure;
        m_currentMetrics.activeEngineId = engineId;
        m_eventCountInStroke = 1;
    }

    void onSegmentRendered(double latencyUs, uint32_t dabsRendered, double rawPressure, double dynamicPressure, double velocity, double stabilizerLag) {
        if (!isEnabled()) return;
        m_currentMetrics.lastSegmentLatencyUs = latencyUs;
        m_currentMetrics.totalDabsInStroke += dabsRendered;
        m_currentMetrics.lastDabsRendered = dabsRendered;
        m_currentMetrics.rawPressure = rawPressure;
        m_currentMetrics.dynamicPressure = dynamicPressure;
        m_currentMetrics.strokeVelocity = velocity;
        m_currentMetrics.stabilizerLagPx = stabilizerLag;

        auto now = std::chrono::high_resolution_clock::now();
        double elapsedStroke = std::chrono::duration<double, std::milli>(now - m_strokeStartTime).count();
        m_currentMetrics.strokeTotalTimeMs = elapsedStroke;

        double dtSec = std::chrono::duration<double>(now - m_lastEventTime).count();
        if (dtSec > 0.0001) {
            m_currentMetrics.inputEventRateHz = static_cast<uint32_t>(1.0 / dtSec);
        }
        m_lastEventTime = now;

        if (elapsedStroke > 10.0 && m_currentMetrics.totalDabsInStroke > 0) {
            m_currentMetrics.totalDabsPerSecond = static_cast<uint32_t>((m_currentMetrics.totalDabsInStroke / elapsedStroke) * 1000.0);
        }
        m_eventCountInStroke++;
    }

    void onSegmentRenderedDetailed(
        double latencyUs,
        double timeKinematicsUs,
        const StageMetrics& stages,
        double rawPressure,
        double dynamicPressure,
        double velocity,
        double stabilizerLag
    ) {
        if (!isEnabled()) return;
        m_currentMetrics.lastSegmentLatencyUs = latencyUs;
        m_currentMetrics.timeKinematicsUs = timeKinematicsUs;
        m_currentMetrics.timeInterpolationUs = stages.timeInterpolationUs;
        m_currentMetrics.timeRasterDabUs = stages.timeRasterDabUs;
        m_currentMetrics.timeUndoRecordUs = stages.timeUndoRecordUs;
        m_currentMetrics.timeCompositeUs = stages.timeCompositeUs;

        m_currentMetrics.lastDabsRendered = stages.dabsRendered;
        m_currentMetrics.totalDabsInStroke += stages.dabsRendered;
        m_currentMetrics.lastDirtyWidth = stages.dirtyWidth;
        m_currentMetrics.lastDirtyHeight = stages.dirtyHeight;
        m_currentMetrics.lastDirtyAreaPx = stages.dirtyAreaPx;
        m_currentMetrics.lastTilesRecorded = stages.tilesRecorded;
        m_currentMetrics.lastTilesComposited = stages.tilesComposited;

        m_currentMetrics.rawPressure = rawPressure;
        m_currentMetrics.dynamicPressure = dynamicPressure;
        m_currentMetrics.strokeVelocity = velocity;
        m_currentMetrics.stabilizerLagPx = stabilizerLag;

        auto now = std::chrono::high_resolution_clock::now();
        double elapsedStroke = std::chrono::duration<double, std::milli>(now - m_strokeStartTime).count();
        m_currentMetrics.strokeTotalTimeMs = elapsedStroke;

        double dtSec = std::chrono::duration<double>(now - m_lastEventTime).count();
        if (dtSec > 0.0001) {
            m_currentMetrics.inputEventRateHz = static_cast<uint32_t>(1.0 / dtSec);
        }
        m_lastEventTime = now;

        if (elapsedStroke > 10.0 && m_currentMetrics.totalDabsInStroke > 0) {
            m_currentMetrics.totalDabsPerSecond = static_cast<uint32_t>((m_currentMetrics.totalDabsInStroke / elapsedStroke) * 1000.0);
        }
        m_eventCountInStroke++;
    }

    void onEndStroke(uint32_t dirtyTiles, uint32_t activeTiles, double tileMemMB, double undoMemMB, uint32_t undoSteps) {
        if (!isEnabled()) return;
        auto now = std::chrono::high_resolution_clock::now();
        m_currentMetrics.strokeTotalTimeMs = std::chrono::duration<double, std::milli>(now - m_strokeStartTime).count();
        m_currentMetrics.dirtyTilesLastStroke = dirtyTiles;
        m_currentMetrics.activeTileCount = activeTiles;
        m_currentMetrics.tileGridMemoryMB = tileMemMB;
        m_currentMetrics.undoStackMemoryMB = undoMemMB;
        m_currentMetrics.undoStepsCount = undoSteps;
        m_currentMetrics.rawPressure = 0.0;
        m_currentMetrics.dynamicPressure = 0.0;
        m_currentMetrics.strokeVelocity = 0.0;
        m_currentMetrics.stabilizerLagPx = 0.0;
    }

    [[nodiscard]] RealTimeStrokeMetrics getSnapshot(uint32_t activeTiles, double tileMemMB, double undoMemMB, uint32_t undoSteps) const {
        RealTimeStrokeMetrics snapshot = m_currentMetrics;
        snapshot.activeTileCount = activeTiles;
        snapshot.tileGridMemoryMB = tileMemMB;
        snapshot.undoStackMemoryMB = undoMemMB;
        snapshot.undoStepsCount = undoSteps;
        return snapshot;
    }

    void reset() noexcept {
        m_currentMetrics = RealTimeStrokeMetrics{};
        m_eventCountInStroke = 0;
    }

    void cleanup() noexcept {
        reset();
    }

private:
    std::atomic<bool> m_enabled{false};
    std::atomic<bool> m_detailedLogging{false};
    RealTimeStrokeMetrics m_currentMetrics{};
    std::chrono::time_point<std::chrono::high_resolution_clock> m_strokeStartTime;
    std::chrono::time_point<std::chrono::high_resolution_clock> m_lastEventTime;
    uint32_t m_eventCountInStroke{0};
};

} // namespace aladyn::engine::telemetry

#endif // ALADYN_ENGINE_ENGINE_TELEMETRY_HPP
