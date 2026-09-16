"""Catalog of document presets, paper properties, and memory estimators for Lumenia."""

from __future__ import annotations
from typing import Dict, List, Tuple, Any

PRESET_CATEGORIES: Dict[str, Dict[str, Any]] = {
    "illustration": {
        "name": "Ilustração & Print",
        "icon": "brush",
        "presets": [
            ("a4_print", "A4 Ilustração", 2480, 3508, 300, "file", "210 × 297 mm • Padrão de Arte"),
            ("a3_poster", "A3 Pôster", 3508, 4960, 300, "file", "297 × 420 mm • Grande Formato"),
            ("manga_b5", "Mangá / Comic B5", 2079, 2953, 600, "book", "182 × 257 mm • Traço Fino 600 DPI"),
            ("square_art", "Quadrado Arte 3K", 3000, 3000, 300, "shapes", "3000 × 3000 px • Alta Resolução"),
            ("a5_sketch", "A5 Sketchbook", 1748, 2480, 300, "file", "148 × 210 mm • Croquis e Estudos"),
        ]
    },
    "web_screen": {
        "name": "Web & Telas",
        "icon": "display",
        "presets": [
            ("4k_uhd", "4K UHD", 3840, 2160, 72, "display", "3840 × 2160 px • 4K Ultra HD"),
            ("full_hd", "Full HD", 1920, 1080, 72, "display", "1920 × 1080 px • Padrão 1080p"),
            ("qhd_1440p", "QHD 1440p", 2560, 1440, 72, "display", "2560 × 1440 px • Monitor 2K"),
            ("ultrawide", "Ultrawide 21:9", 3440, 1440, 72, "display", "3440 × 1440 px • Panorâmico"),
            ("hd_720p", "HD 720p", 1280, 720, 72, "display", "1280 × 720 px • Conteúdo Leve"),
        ]
    },
    "social_media": {
        "name": "Redes & Mobile",
        "icon": "smartphone",
        "presets": [
            ("insta_post", "Instagram Post", 1080, 1080, 72, "shapes", "1080 × 1080 px • Quadrado 1:1"),
            ("insta_story", "Story / Reels", 1080, 1920, 72, "smartphone", "1080 × 1920 px • Vertical 9:16"),
            ("yt_thumb", "YouTube Thumbnail", 1280, 720, 72, "video", "1280 × 720 px • Miniatura 16:9"),
            ("twitter_header", "X / Twitter Header", 1500, 500, 72, "display", "1500 × 500 px • Banner"),
            ("avatar_sq", "Avatar / Perfil", 800, 800, 72, "user", "800 × 800 px • Foto de Perfil"),
        ]
    },
    "cinema": {
        "name": "Cinema & Concept",
        "icon": "video",
        "presets": [
            ("cine_16_9", "Concept Art 16:9", 3840, 2160, 72, "video", "3840 × 2160 px • Widescreen"),
            ("cine_anamorphic", "Cinematic 2.35:1", 2048, 872, 72, "video", "2048 × 872 px • Anamórfico"),
            ("storyboard_grid", "Storyboard Sheet", 1920, 1080, 72, "grid", "1920 × 1080 px • Prancha"),
        ]
    }
}

BACKGROUND_COLORS = [
    ("Branco Neve (#FFFFFF)", (255, 255, 255, 255)),
    ("Papel Marfim (#FDF6E3)", (253, 246, 227, 255)),
    ("Cinza Neutro (#808080)", (128, 128, 128, 255)),
    ("Preto Escuro (#1A1A1A)", (26, 26, 26, 255)),
    ("Transparente (Sem Fundo)", (0, 0, 0, 0)),
]

PAPER_TEXTURES = [
    ("Nenhuma (Superfície Lisa)", 0),
    ("Papel Fino de Desenho (Fine Grain)", 1),
    ("Textura de Aquarela Algodão (Rough)", 2),
    ("Tela de Pintura (Linen Canvas)", 3),
]

COLOR_PROFILES = [
    (0, "sRGB Padrão (Telas & Web)"),
    (1, "Display P3 (Amplo Gamut Apple)"),
    (2, "Adobe RGB (Fotografia & Fine Art)"),
    (3, "Rec. 2020 (Cinema Ultra HD)"),
    (4, "Tons de Cinza / Grayscale (Mangá)"),
]


def estimate_ram_usage_mb(width: int, height: int, num_layers: int = 3) -> float:
    bytes_per_pixel = 4
    canvas_bytes = float(width) * float(height) * bytes_per_pixel
    total_bytes = canvas_bytes * (num_layers + 1.5)
    return total_bytes / (1024.0 * 1024.0)
