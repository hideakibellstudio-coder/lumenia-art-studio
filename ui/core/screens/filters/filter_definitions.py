"""
filter_definitions.py — Catálogo de Metadados e Parâmetros dos Filtros do Motor ALADYN.
========================================================================================
Define os esquemas canônicos de cada tipo de filtro suportado pelo ALADYN ENGINE,
seus limites numéricos, passos e tipos de controles de interface.
"""

from __future__ import annotations

FILTER_DEFINITIONS = [
    {
        "type_id": 0,
        "key": "huesat",
        "name": "Matiz / Saturação (HSV)",
        "category": "Cores",
        "icon": "cat_efeitos",
        "description": "Ajusta matiz, saturação e luminosidade das cores da imagem.",
        "params": [
            {"id": "hue", "label": "Matiz (Hue Shift)", "min": -180, "max": 180, "default": 0, "suffix": "°"},
            {"id": "sat", "label": "Saturação (Saturation)", "min": -100, "max": 100, "default": 0, "suffix": "%"},
            {"id": "light", "label": "Luminosidade (Lightness)", "min": -100, "max": 100, "default": 0, "suffix": "%"},
            {"id": "colorize", "label": "Modo Colorizar", "type": "bool", "default": False},
        ]
    },
    {
        "type_id": 1,
        "key": "brightness",
        "name": "Brilho, Contraste & Gama",
        "category": "Iluminação",
        "icon": "theme",
        "description": "Controle de exposição, nível de sombras, brilho e curva de gama.",
        "params": [
            {"id": "bright", "label": "Brilho (Brightness)", "min": -100, "max": 100, "default": 0, "suffix": "%"},
            {"id": "contrast", "label": "Contraste (Contrast)", "min": -100, "max": 100, "default": 0, "suffix": "%"},
            {"id": "gamma", "label": "Gama (Correction)", "min": 1, "max": 30, "default": 10, "factor": 10.0, "suffix": ""},
        ]
    },
    {
        "type_id": 2,
        "key": "gaussian_blur",
        "name": "Desfoque Gaussiano",
        "category": "Efeitos",
        "icon": "cat_efeitos",
        "description": "Suaviza detalhes e atenua ruído com desfoque de raio contínuo.",
        "params": [
            {"id": "radius", "label": "Raio de Desfoque (Blur Radius)", "min": 1, "max": 100, "default": 10, "suffix": "px"},
            {"id": "preserve_alpha", "label": "Preservar Transparência", "type": "bool", "default": True},
        ]
    },
    {
        "type_id": 3,
        "key": "colorbalance",
        "name": "Balanço de Cores / Níveis",
        "category": "Cores",
        "icon": "cat_efeitos",
        "description": "Ajuste independente dos canais Vermelho, Verde e Azul (RGB).",
        "params": [
            {"id": "red", "label": "Vermelho (Red)", "min": -100, "max": 100, "default": 0, "suffix": "%"},
            {"id": "green", "label": "Verde (Green)", "min": -100, "max": 100, "default": 0, "suffix": "%"},
            {"id": "blue", "label": "Azul (Blue)", "min": -100, "max": 100, "default": 0, "suffix": "%"},
        ]
    },
    {
        "type_id": 4,
        "key": "sharpen_vignette",
        "name": "Nitidez & Vinheta",
        "category": "Efeitos",
        "icon": "cat_efeitos",
        "description": "Realça micro-contrastes de borda e adiciona vinheta cinematográfica.",
        "params": [
            {"id": "sharpen", "label": "Nitidez (Sharpness)", "min": 0, "max": 100, "default": 25, "suffix": "%"},
            {"id": "vignette", "label": "Escurecimento de Vinheta", "min": 0, "max": 100, "default": 0, "suffix": "%"},
            {"id": "vignette_radius", "label": "Raio da Vinheta", "min": 10, "max": 100, "default": 50, "suffix": "%"},
        ]
    },
    {
        "type_id": 5,
        "key": "invert",
        "name": "Inversão & Limiar (Threshold)",
        "category": "Efeitos",
        "icon": "clean_layer",
        "description": "Inverte os canais de cor ou converte a imagem em alto contraste P&B.",
        "params": [
            {"id": "mode", "label": "Modo Inverter (vs Limiar)", "type": "bool", "default": True},
            {"id": "thresh", "label": "Corte de Limiar (Threshold)", "min": 0, "max": 255, "default": 128, "suffix": ""},
        ]
    },
    {
        "type_id": 6,
        "key": "pixelate",
        "name": "Pixelizar (Mosaico 8-Bits)",
        "category": "Efeitos",
        "icon": "cat_efeitos",
        "description": "Converte a imagem em blocos procedurais de pixels estilo retro 8-bits.",
        "params": [
            {"id": "block", "label": "Tamanho dos Blocos (Pixel Size)", "min": 2, "max": 64, "default": 8, "suffix": "px"},
        ]
    },
]
