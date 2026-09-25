# `ui/plugins/system/workspace_core/workspace/canvas/math/` — matemática das guias

**Responsabilidade:** funções puras de projeção 3D (olho de peixe, rotações, curvas) e o construtor da malha da perspectiva curvilínea de 6 pontos.

## Porta de entrada

Importar por módulo: `camera_3d_projector` (funções), `curvilinear_mesh_builder.CurvilinearMeshBuilder`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Marca o pacote. |
| `camera_3d_projector.py` | Pure 3D mathematical projection and transformation utilities. |
| `curvilinear_mesh_builder.py` | Curvilinear 6P Mesh and Path Builder. |

## Regras

Sem Qt de interface e sem estado global: entra número, sai número. Lei do rio nº 2: se o motor já calcula algo, ligue ao método nativo em vez de duplicar aqui.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
(nenhuma dependência interna)
<!-- /arccc:deps -->
