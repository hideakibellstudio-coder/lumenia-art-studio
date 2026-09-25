#ifndef ALADYN_ENGINE_LAYER_NODE_HPP
#define ALADYN_ENGINE_LAYER_NODE_HPP

#include <string>
#include <memory>
#include <vector>
#include <cstdint>
#include "blending/LayerBlendMode.hpp"

namespace aladyn::engine::document {

enum class LayerNodeType {
    DrawingLayer = 0,
    Group = 1,
    FilterLayer = 2
};

// Enum da mesclagem, definido em blending/ e reexportado aqui: é parte do
// contrato do documento (document::LayerBlendMode).
using blending::LayerBlendMode;

class LayerNode {
public:
    LayerNode(const std::string& name, LayerNodeType type)
        : m_name(name), m_type(type) {}

    virtual ~LayerNode() = default;

    [[nodiscard]] LayerNodeType getType() const noexcept { return m_type; }
    [[nodiscard]] bool isGroup() const noexcept { return m_type == LayerNodeType::Group; }
    [[nodiscard]] bool isFilter() const noexcept { return m_type == LayerNodeType::FilterLayer; }

    [[nodiscard]] const std::string& getName() const noexcept { return m_name; }
    void setName(const std::string& name) { m_name = name; }

    // Identity assigned by the document boundary. It is independent from the
    // display name and vector position, both of which can change legitimately.
    [[nodiscard]] uint64_t getDocumentUid() const noexcept { return m_documentUid; }
    void setDocumentUid(uint64_t uid) noexcept { m_documentUid = uid; }

    [[nodiscard]] double getOpacity() const noexcept { return m_opacity; }
    void setOpacity(double opacity) noexcept { m_opacity = opacity; }

    [[nodiscard]] bool isVisible() const noexcept { return m_visible; }
    void setVisible(bool visible) noexcept { m_visible = visible; }

    [[nodiscard]] bool isLocked() const noexcept { return m_isLocked; }
    void setLocked(bool locked) noexcept { m_isLocked = locked; }

    [[nodiscard]] LayerBlendMode getBlendMode() const noexcept { return m_blendMode; }
    void setBlendMode(LayerBlendMode mode) noexcept { m_blendMode = mode; }

    [[nodiscard]] LayerNode* getParent() noexcept { return m_parent; }
    [[nodiscard]] const LayerNode* getParent() const noexcept { return m_parent; }
    void setParent(LayerNode* parent) noexcept { m_parent = parent; }

protected:
    std::string m_name;
    uint64_t m_documentUid{0};
    LayerNodeType m_type;
    double m_opacity{1.0};
    bool m_visible{true};
    bool m_isLocked{false};
    LayerBlendMode m_blendMode{LayerBlendMode::Normal};
    LayerNode* m_parent{nullptr};
};

} // namespace aladyn::engine::document

#endif // ALADYN_ENGINE_LAYER_NODE_HPP
