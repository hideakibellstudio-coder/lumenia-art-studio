# 🧩 Subsistema de Plugins e Extensibilidade

O **Lumenia** adota uma arquitetura orientada a plugins onde até mesmo recursos centrais (como painel de pincéis, gerenciador de camadas e telemetria) operam como plugins modulares.

---

## 🏛️ 1. Estrutura do Subsistema (`ui/core/plugins/`)

- **`PluginManager` (`manager.py`)**: Singleton responsável pela inicialização, verificação de dependências, ativação e desativação de plugins.
- **`PluginDiscovery` (`discovery.py`)**: Descobre manifestos `plugin.json` nas pastas canônicas do sistema (`plugins/system/` e `plugins/ui/`).
- **`PackageInstaller` (`package_installer.py`)**: Gerencia o isolamento de pacotes externos, validação de integridade SHA-256 e quarentena de plugins incompatíveis.
- **Configuração Persistente (`plugins_config.json`)**: Salva o estado habilitado/desabilitado de cada plugin de forma atômica com backup automático.

---

## 📋 2. Manifesto do Plugin (`plugin.json`)

Todo plugin declara seus metadados de forma declarativa:

```json
{
  "id": "brush_plugin",
  "name": "Brush Engine Studio",
  "version": "1.0.0",
  "api_version": 2,
  "entry_point": "panel.py",
  "description": "Painel de configuração avançada de pincéis e curvas de pressão.",
  "dependencies": ["workspace_core"],
  "permissions": ["engine.brush", "ui.dock"]
}
```

---

## 🔄 3. Ciclo de Vida do Plugin

1. **Discovery**: Escaneamento do manifesto e validação de schema.
2. **Dependency Resolution**: Grafo acíclico dirigido (DAG) de dependências. Se uma dependência estiver ausente, o plugin é colocado em estado desativado com log explícito.
3. **Activation (`enable_plugin`)**: Executa o método `setup(api)` do plugin, injetando docks, ferramentas e atalhos na UI.
4. **Deactivation (`disable_plugin`)**: Executa rotinas de limpeza (`teardown`), desconectando slots Qt e destruindo widgets com segurança.
5. **Rollback Seguro**: Se a inicialização de um plugin lançar qualquer exceção, o `PluginManager` cancela a operação, executa o rollback das dependências ativadas e notifica o usuário sem comprometer a estabilidade do processo principal.\n