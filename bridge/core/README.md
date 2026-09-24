# `bridge/core/` — núcleo da ponte

**Responsabilidade:** os bindings PyBind11 que expõem o motor.

## Porta de entrada

`bindings/engine_bindings.cpp`.

## Conteúdo

| Pasta | Responsabilidade |
|---|---|
| `bindings/` | Um arquivo `bind_*.cpp` por assunto, registrados pelo módulo. |

## Regras

- Sem lógica: converter, validar e delegar à `PaintEngineFacade`.
