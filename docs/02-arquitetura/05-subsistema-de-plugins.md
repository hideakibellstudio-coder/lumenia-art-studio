# 🧩 Subsistema de Plugins e Extensibilidade

O **Lumenia** adota uma arquitetura orientada a plugins onde até mesmo recursos centrais (como painel de pincéis, gerenciador de camadas e telemetria) operam como plugins modulares.

---

## 🏛️ 1. Estrutura do Subsistema (`ui/core/plugins/`)

- **`PluginManager`** (`manager.py`): Singleton responsável pela descoberta, resolução de dependências, ativação e desativação de plugins.
- **`register_module_plugins` / `discover_compiled_plugins`** (`discovery.py`): Funções (não uma classe `PluginDiscovery`) que descobrem subclasses concretas de `BasePlugin` expostas pelos módulos Python dentro de `plugins/system/` e `plugins/ui/`. Não há manifesto em arquivo para esses plugins — os metadados vêm do objeto `PluginMetadata` retornado por `get_metadata()`.
- **`install_plugin_package` / `uninstall_plugin_package`** (`package_installer.py`): Funções (não uma classe `PackageInstaller`) que extraem pacotes `.zip` de plugins instalados externamente, validam o `manifest.json` do pacote e o promovem para `plugins_dir`, com quarentena automática (`.plugin-quarantine/`) em caso de falha de validação.
- **`validate_package_manifest`** (`package_manifest.py`): Valida o `manifest.json` de pacotes externos — schema, SemVer, versão mínima de API e permissões (ver seção 2).
- **`PluginContext`** (`context.py`): Objeto injetado em cada plugin via `initialize()`, expondo `bridge_client`, `backend`, `main_window` e `service_registry`.
- **`ServiceRegistry`** (`registry.py`): Registro singleton de serviços tipados para comunicação desacoplada entre plugins.
- **Configuração Persistente (`plugins_config.json`)**: Salva o estado habilitado/desabilitado de cada plugin de forma atômica com backup automático (`.bak`).

---

## 📋 2. Metadados do Plugin

O Lumenia distingue dois níveis de metadados de plugin — não existe um único manifesto `plugin.json` usado em todo o sistema.

### A. Plugins internos — `PluginMetadata` (`ui/core/plugins/metadata.py`)

Todo plugin embutido no repositório (`plugins/system/`, `plugins/ui/`) declara seus metadados em código Python, através do método `get_metadata()` exigido por `BasePlugin`, retornando a dataclass:

```python
@dataclass
class PluginMetadata:
    id: str
    name: str
    version: str
    author: str
    description: str
    plugin_type: PluginType = PluginType.UI   # SYSTEM, UI, BRUSH, FILTER, TOOL, IO
    dependencies: List[str] = field(default_factory=list)
    icon: Optional[str] = None
```

Não existe arquivo `plugin.json` nem campos `entry_point`, `api_version` ou `permissions` neste nível — a descoberta acontece por introspecção das classes Python carregadas (`register_module_plugins`), não pela leitura de um manifesto em disco.

### B. Pacotes externos instalados — `manifest.json` (`ui/core/plugins/package_manifest.py`)

Pacotes `.zip` instalados pelo usuário via `PluginManager.load_plugin_from_source()` *são* validados contra um manifesto declarativo real — mas o arquivo se chama `manifest.json`, não `plugin.json`, e vive na raiz do pacote extraído:

```json
{
  "id": "brush_plugin",
  "version": "1.0.0",
  "minimum_api_version": 1,
  "dependencies": ["workspace_core"],
  "permissions": ["ui", "engine"],
  "entrypoint": "__init__.py",
  "integrity": {
    "algorithm": "sha256",
    "files": { "__init__.py": "<sha256 do arquivo>" }
  }
}
```

- `minimum_api_version` é validado contra a constante `PLUGIN_API_VERSION` (atualmente `1`) declarada no próprio módulo.
- `permissions` é restrito ao conjunto fechado `ALLOWED_PERMISSIONS = {"ui", "engine", "filesystem_read", "filesystem_write", "network"}` — é uma declaração de intenção verificada no schema, não um sandbox de execução real.
- `entrypoint` deve ser literalmente `"__init__.py"`.
- `integrity` é opcional; quando presente, cada arquivo listado tem seu SHA-256 recalculado e comparado antes da promoção.
- Após extração segura (proteção contra symlinks, path traversal, entradas duplicadas e pacotes acima de 512 MiB), o pacote é promovido atomicamente para `plugins_dir` e o `PluginManager` confirma que a classe `BasePlugin` promovida expõe o mesmo `id` e as mesmas `dependencies` do manifesto — caso contrário, o pacote é movido para quarentena.

---

## 🔄 3. Ciclo de Vida do Plugin

1. **Discovery (`PluginManager.rescan_plugins`)**: Varre `plugins_dir` (com fallback para módulos compilados embutidos) e registra toda subclasse concreta de `BasePlugin` encontrada, sem desativar plugins já ativos.
2. **Resolução de Dependências (`_resolve_load_order`)**: Ordena os plugins descobertos por prioridade (`get_priority()`, maior primeiro) e então executa uma busca em profundidade (DFS) sobre os `id`s declarados em `PluginMetadata.dependencies`, produzindo uma ordem topológica de ativação. Uma dependência cíclica interrompe a resolução com `ValueError`.
3. **Ativação (`PluginLifecycle.enable`, em `lifecycle.py`)**: Instancia o plugin, ativa recursivamente suas dependências, injeta o `PluginContext` via `instance.initialize(context)` e então chama `instance.activate()` — não existem hooks `setup(api)`/`teardown` no `BasePlugin` real.
4. **Desativação (`PluginLifecycle.disable`)**: Executa, em ordem, `deactivate()` → `shutdown()` → `dispose()` na instância ativa e remove o plugin de `active_instances`. Plugins com `is_system_plugin() == True` não podem ser desativados pelo usuário.
5. **Rollback Seguro**: Se `initialize`/`activate` lançar qualquer exceção, `PluginLifecycle.enable` aciona um teardown de compensação (chamando apenas os hooks que já haviam começado a rodar) e retorna `False`, sem deixar o `PluginManager` com estado parcialmente ativado; falha de um plugin de sistema interrompe o boot com `RuntimeError`.
