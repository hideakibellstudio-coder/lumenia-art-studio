"""Catalog of available color profiles for rendering and proofing."""

def get_default_color_profiles() -> list[dict]:
    """Retorna o catálogo padrão de perfis de cores e simulação de gamut."""
    return [
        # 1. Digital (RGB)
        {
            "id": 0,
            "name": "Padrão (sRGB)",
            "category": "Digital (RGB)",
            "description": "Espaço de cor universal padrão para web, monitores convencionais e dispositivos móveis.",
            "gamut": "sRGB IEC61966-2.1",
            "whitepoint": "D65 (6500K)",
            "gamma": "2.2"
        },
        {
            "id": 1,
            "name": "Display P3 (Wide Gamut)",
            "category": "Digital (RGB)",
            "description": "Gamut cinematográfico e telas modernas (Apple Retina, monitores HDR). 25% mais cores que sRGB.",
            "gamut": "DCI-P3 D65",
            "whitepoint": "D65 (6500K)",
            "gamma": "sRGB Transfer"
        },
        {
            "id": 2,
            "name": "Adobe RGB (1998)",
            "category": "Digital (RGB)",
            "description": "Excelente amplitude em tons verdes e cianos, ideal para fotografia profissional e preparação para gráfica.",
            "gamut": "Adobe RGB 1998",
            "whitepoint": "D65 (6500K)",
            "gamma": "2.2"
        },
        {
            "id": 3,
            "name": "Rec. 2020 (UHD TV)",
            "category": "Digital (RGB)",
            "description": "Gamut ultra-amplo para masterização de vídeo 4K/8K HDR e arte digital de próxima geração.",
            "gamut": "BT.2020",
            "whitepoint": "D65 (6500K)",
            "gamma": "ITU-R BT.2020"
        },

        # 2. Impressão (CMYK Pro)
        {
            "id": 4,
            "name": "U.S. Web Coated (SWOP) v2",
            "category": "Impressão (CMYK)",
            "description": "Padrão norte-americano e brasileiro para impressão comercial rotativa em papel couché.",
            "gamut": "SWOP v2 (CMYK)",
            "whitepoint": "D50 (5000K)",
            "gamma": "Press Tone Value"
        },
        {
            "id": 5,
            "name": "ISO Coated v2 (ECI / FOGRA39)",
            "category": "Impressão (CMYK)",
            "description": "Referência oficial europeia para offset plano em papel brilhante/fosco de alta qualidade.",
            "gamut": "FOGRA39 (CMYK)",
            "whitepoint": "D50 (5000K)",
            "gamma": "ISO 12647-2"
        },
        {
            "id": 6,
            "name": "GRACoL 2006 (Coated 1v2)",
            "category": "Impressão (CMYK)",
            "description": "Especificação premium para gráficas de ponta e provas contratuais com G7 Calibration.",
            "gamut": "GRACoL 2006",
            "whitepoint": "D50 (5000K)",
            "gamma": "G7 Curves"
        },
        {
            "id": 7,
            "name": "Japan Color 2001 Coated",
            "category": "Impressão (CMYK)",
            "description": "Padrão industrial da indústria gráfica japonesa para mangás, artbooks e ilustrações.",
            "gamut": "Japan Color 2001",
            "whitepoint": "D50 (5000K)",
            "gamma": "Japan Print Std"
        },

        # 3. Acessibilidade & Prova de Daltonismo
        {
            "id": 8,
            "name": "Protanopia (Sem Vermelho)",
            "category": "Acessibilidade",
            "description": "Simulação em tempo real para avaliar legibilidade de ilustrações sem cones L (vermelho).",
            "gamut": "Simulação Protanopia",
            "whitepoint": "D65",
            "gamma": "Linear Match"
        },
        {
            "id": 9,
            "name": "Deuteranopia (Sem Verde)",
            "category": "Acessibilidade",
            "description": "Simulação do tipo mais comum de daltonismo (ausência de cones M - verde).",
            "gamut": "Simulação Deuteranopia",
            "whitepoint": "D65",
            "gamma": "Linear Match"
        },
        {
            "id": 10,
            "name": "Tritanopia (Sem Azul/Amarelo)",
            "category": "Acessibilidade",
            "description": "Simulação de percepção visual com ausência de cones S (azul).",
            "gamut": "Simulação Tritanopia",
            "whitepoint": "D65",
            "gamma": "Linear Match"
        },
        {
            "id": 11,
            "name": "Acromatopsia (Monocromático)",
            "category": "Acessibilidade",
            "description": "Prova rigorosa de luminância, hierarquia tonal e contraste puro em preto e branco.",
            "gamut": "Luminância Pura (Y)",
            "whitepoint": "D65",
            "gamma": "Luminance Rec.709"
        },

        # 4. Pipeline do Motor & VFX
        {
            "id": 12,
            "name": "Linear sRGB (Physical Blending)",
            "category": "Motor Físico",
            "description": "Cálculo de mistura física fotométrica sem distorção gama, ideal para iluminação e sombras reais.",
            "gamut": "sRGB Primaries",
            "whitepoint": "D65",
            "gamma": "1.0 (Linear Puro)"
        },
        {
            "id": 13,
            "name": "ACEScg (Academy Color Encoding)",
            "category": "Motor Físico",
            "description": "Padrão da indústria de cinema e efeitos visuais (VFX) com suporte a iluminação com alcance dinâmico infinito.",
            "gamut": "AP1 Primaries",
            "whitepoint": "D60 (ACES)",
            "gamma": "1.0 (Linear Float)"
        }
    ]
