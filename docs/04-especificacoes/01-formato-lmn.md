# 📦 Especificação Técnica: Container LMN (v2+)

O formato **`.lmn`** (*Lumenia Native Project File*) é o container oficial de persistência de projetos do Lumenia Art Studio.

---

## 🗄️ 1. Arquitetura do Container ZIP

O arquivo `.lmn` é um arquivo ZIP não criptografado, comprimido via `zipfile.ZIP_DEFLATED`, contendo:

```text
meu_projeto.lmn
├── manifest.json                     # Metadados estruturais, layers, guias e configurações
├── layers/                           # Payloads brutos de pixels por camada
│   ├── 1.rgba                        # Pixels RGBA 8-bit brutos da Camada 1
│   └── 2.rgba                        # Pixels RGBA 8-bit brutos da Camada 2
├── selection/
│   └── mask.alpha                    # Máscara de seleção ativa (canal alfa de 8 bits)
├── paper/
│   └── texture.rgba                  # Textura de papel customizada embutida
└── profiles/
    └── document.icc                  # Perfil de cor ICC customizado embutido (Plano B / F-006)
```

---

## 📄 2. Estrutura do `manifest.json`

O arquivo `manifest.json` governa a reconstrução fiel do projeto:

```json
{
  "version": 2,
  "document_uid": "art-doc-8942",
  "name": "Pintura Conceitual",
  "width": 3840,
  "height": 2160,
  "created_at": "2026-09-14T10:00:00Z",
  "updated_at": "2026-09-14T12:00:00Z",
  "active_uid": 2,
  "color_profile_id": 150,
  "color_profile_name": "Studio Custom DCI-P3",
  "color_profile_payload": "profiles/document.icc",
  "layers": [
    {
      "uid": 1,
      "name": "Fundo",
      "is_group": false,
      "is_filter": false,
      "visible": true,
      "locked": false,
      "alpha_locked": false,
      "opacity": 1.0,
      "blend_mode": "Normal",
      "clipping_mask": false,
      "parent_uid": null,
      "pixel_payload": "layers/1.rgba"
    },
    {
      "uid": 2,
      "name": "Personagem",
      "is_group": false,
      "is_filter": false,
      "visible": true,
      "locked": false,
      "alpha_locked": false,
      "opacity": 1.0,
      "blend_mode": "Normal",
      "clipping_mask": false,
      "parent_uid": null,
      "pixel_payload": "layers/2.rgba"
    }
  ],
  "camera": {
    "zoom": 1.25,
    "pan_x": 100.0,
    "pan_y": -50.0,
    "rotation": 0.0
  },
  "paper": {
    "color": [255, 255, 255, 255],
    "visible": true,
    "texture_id": 1,
    "texture_enabled": true,
    "texture_payload": "paper/texture.rgba"
  },
  "selection": {
    "payload": "selection/mask.alpha"
  }
}
```

---

## 🔄 3. Tolerância a Falhas e Migração Automática

1. **Migração Transparente**:
   - O validador de schema (`ui/core/document/schema.py`) migra arquivos legados automaticamente:
     - `v0` $	o$ `v1`: Adiciona metadados estruturais de câmera e integridade de UIDs.
     - `v1` $	o$ `v2`: Incorpora suporte a guias, simetria radial, papel e texturas.
     - `v2` $	o$ `v2+`: Incorpora validação de perfil ICC embutido (`profiles/document.icc`).
2. **Gravação Atômica e Backup de Segurança**:
   - A gravação é realizada primeiro em um arquivo temporário no mesmo volume de disco.
   - O arquivo temporário é validado (verificação de integridade ZIP e conferência de checksum).
   - O arquivo original anterior é renomeado para `.lmn.bak`.
   - O arquivo temporário substitui atômica e definitivamente o arquivo principal via `os.replace`.\n