# 🎨 Especificação: Gestão Profissional de Cor (LittleCMS 2.18 & ICC)

O subsistema de cor do **Lumenia** fornece gerenciamento de cor de padrão industrial com fidelidade para impressão e telas de alta gama (*Wide Gamut*).

---

## 🏛️ 1. Componentes do Subsistema (`ui/core/color/`)

- **`ICCProfileInfo` (`icc_profile.py`)**: Dataclass canônica contendo ID, nome do perfil, espaço de cor (RGB, CMYK, Gray), gamut, ponto branco, curva de transferência e hash SHA-256 dos bytes ICC.
- **`ColorManagementEngine` (`cms_engine.py`)**: Wrapper de alta performance sobre o **LittleCMS 2.18** utilizando `PIL.ImageCms`. Implementa cache LRU de perfis compilados e transformadores de buffer.
- **`ColorProfileCatalog` (`catalog.py`)**: Catálogo unificado que integra:
  - Os 14 perfis C++ nativos embutidos (IDs 0 a 13: sRGB, Display P3, Adobe RGB, ProPhoto, Rec.2020, etc.).
  - Perfis do sistema operacional instalados no Windows Spooler (`C:\Windows\System32\spool\drivers\color`).
  - Perfis customizados do usuário importados em tempo de execução (IDs $\ge 100$).
- **`SoftProofConfig` (`proofing.py`)**: Configuração de prova suave com emulação de saída para gráfica ou dispositivos específicos.

---

## 🖨️ 2. Soft-Proofing & Gamut Warning

O pipeline de soft-proofing simula em tempo real no monitor como a pintura será reproduzida em um meio físico ou espaço de cor de destino (ex: perfis CMYK padrão ISO Coated, FOGRA39, US Web Coated SWOP).

### Intents de Renderização Suportados:
1. **Perceptual (0)**: Preserva as relações visuais entre as cores de forma natural (ideal para arte e fotografia).
2. **Relative Colorimetric (1)**: Ajusta as cores em relação ao ponto branco de destino; mantém as cores dentro do gamut idênticas.
3. **Saturation (2)**: Preserva a vivacidade das cores (ideal para gráficos e ilustrações vetoriais).
4. **Absolute Colorimetric (3)**: Mantém os valores exatos de cor sem adaptar ao ponto branco do papel (ideal para provas contratuais).

### Compensação de Ponto Preto (BPC) e Alerta de Gamut:
- **BPC (Black Point Compensation)**: Evita que sombras fiquem empastadas ou convertidas em cinza quando a faixa dinâmica de saída for menor.
- **Gamut Warning**: Destaca visualmente em tempo real no canvas os pixels que estão fora do espaço de cor do dispositivo de saída.

---

## 🚀 3. Roadmap para Buffers Nativos de 16-bit e Float

Consulte o documento completo em [`docs/COLOR_PIPELINE_ARCHITECTURE.md`](../COLOR_PIPELINE_ARCHITECTURE.md) para a especificação do plano de evolução dos buffers internos do C++:
- Transição de `uint8_t[4]` (RGBA8) para `uint16_t[4]` (RGBA16 linear) e `float[4]` (RGBA32F HDR).
- Eliminação definitiva de *color banding* em gradientes suaves e pintura com pincéis de baixa opacidade.\n