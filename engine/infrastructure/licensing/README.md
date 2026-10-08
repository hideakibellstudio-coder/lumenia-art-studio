# `engine/infrastructure/licensing/` — licença do Lumenia

**Responsabilidade:** decidir se este processo tem uma licença válida e, sem ela, marcar a imagem exportada. Não sabe de camadas, pincéis nem documentos: recebe texto (a licença) e bytes RGBA (a exportação).

## Porta de entrada

`LicenseAuthority.hpp` (`LicenseAuthority::instance()`, `evaluateLicense`) e `ExportWatermark.hpp` (`stampUnlicensedWatermark`), expostos ao Python por `bridge/core/bindings/bind_runtime.cpp`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `LicenseToken.hpp` / `LicenseToken.cpp` | O formato `LUMENIA1-<base32 do conteúdo>.<base32 da assinatura>`: base32, separação e leitura das linhas `chave=valor` (versão 1, chaves desconhecidas ou repetidas recusam a licença). Espelho de `lumenia_licgen/token_format.py` do gerador. |
| `SignatureVerifier.hpp` / `SignatureVerifier.cpp` | ECDSA P-256 sobre SHA-256 pelo CNG do Windows (`bcrypt.dll`). Nenhuma criptografia escrita à mão: fora do Windows toda licença é `unsupported`. |
| `LicenseAuthority.hpp` / `LicenseAuthority.cpp` | Avalia a licença (assinatura, revogada, expirada, versão mais nova que `upd`) e guarda a ativa do processo. Uma licença inválida nunca substitui uma válida. |
| `ExportWatermark.hpp` / `ExportWatermark.cpp` | "LUMENIA FREE" em grade, claro sobre sombra escura, no RGBA exportado sem licença. A pintura e o `.lmn` nunca são tocados. |
| `LicensePublicKey.hpp` | **Gerado** pelo gerador de licenças (`export`): a chave pública que este binário aceita e o nome dela (`dev` ou `prod`). |
| `RevokedLicenses.hpp` | **Gerado** pelo gerador (`export`): os ids de licenças revogadas. |

## Regras

- A chave privada nunca entra neste repositório. Trocar de chave = `python -m lumenia_licgen export --key prod --lumenia <este repositório>` no gerador e recompilar o motor.
- `scripts/build_release.py` recusa empacotar um motor que ainda confia na chave `dev`.
- Datas são texto `AAAA-MM-DD` e se comparam como texto; "hoje" é UTC e a data do binário vem de `__DATE__`.
- Mudou o formato? Mude o gerador junto e suba `v`: licenças antigas continuam `v=1`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
(nenhuma dependência interna)
<!-- /arccc:deps -->
