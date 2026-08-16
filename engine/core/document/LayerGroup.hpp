#ifndef ALADYN_ENGINE_LAYER_GROUP_HPP
#define ALADYN_ENGINE_LAYER_GROUP_HPP

#include "LayerNode.hpp"
#include <vector>
#include <memory>

namespace aladyn::engine::document {

class LayerGroup : public LayerNode {
public:
    explicit LayerGroup(const std::string& name = "Novo Grupo")
        : LayerNode(name, LayerNodeType::Group) {}

    [[nodiscard]] bool isPassThrough() const noexcept { return m_passThrough; }
    void setPassThrough(bool passThrough) noexcept { m_passThrough = passThrough; }

    [[nodiscard]] bool isCollapsed() const noexcept { return m_collapsed; }
    void setCollapsed(bool collapsed) noexcept { m_collapsed = collapsed; }

    [[nodiscard]] const std::vector<std::unique_ptr<LayerNode>>& getChildren() const noexcept { return m_children; }
    [[nodiscard]] std::vector<std::unique_ptr<LayerNode>>& getChildren() noexcept { return m_children; }

    void addChild(std::unique_ptr<LayerNode> child) {
        if (child) {
            child->setParent(this);
            m_children.push_back(std::move(child));
        }
    }

private:
    bool m_passThrough{true};
    bool m_collapsed{false};
    std::vector<std::unique_ptr<LayerNode>> m_children;
};

} // namespace aladyn::engine::document

#endif // ALADYN_ENGINE_LAYER_GROUP_HPP
