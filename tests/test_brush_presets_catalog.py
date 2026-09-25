"""Unit tests for Camada 4 - Fase 1: Modularização do Catálogo de Presets de Pincéis.

Tests modular presets under ARCcC v2.
"""

import unittest
from ui.plugins.panels.brush_plugin.presets_data import (
    BRUSH_CATEGORIES,
    PARAM_GROUPS,
    ENGINE_TYPE_TO_CATEGORY,
    get_preset_display_name,
    get_category_display_name,
)


class TestBrushPresetsModular(unittest.TestCase):
    """Verifies that brush presets modularization maintains 100% data integrity."""

    def test_categories_count_and_ids(self):
        """All 9 brush categories are present and correctly ordered."""
        self.assertEqual(len(BRUSH_CATEGORIES), 9)
        expected_ids = ["brush", "pencil", "inker", "eraser", "marker", "blur", "smudge", "watercolor", "oil"]
        actual_ids = [cat["id"] for cat in BRUSH_CATEGORIES]
        self.assertEqual(actual_ids, expected_ids)

    def test_total_presets_count(self):
        """All 33 curated presets are present across the 9 categories."""
        total_presets = sum(len(cat["presets"]) for cat in BRUSH_CATEGORIES)
        self.assertEqual(total_presets, 33)

    def test_engine_type_mapping(self):
        """ENGINE_TYPE_TO_CATEGORY correctly maps all 9 engine indices (0 to 8)."""
        self.assertEqual(len(ENGINE_TYPE_TO_CATEGORY), 9)
        for engine_type in range(9):
            self.assertIn(engine_type, ENGINE_TYPE_TO_CATEGORY)
            self.assertEqual(ENGINE_TYPE_TO_CATEGORY[engine_type]["engine_type"], engine_type)

    def test_defaults_injected(self):
        """Category defaults for stabilizer_weight and stroke_taper_enabled are present in all presets."""
        for cat in BRUSH_CATEGORIES:
            for preset in cat["presets"]:
                self.assertIn("stabilizer_weight", preset, f"Preset '{preset.get('label')}' missing stabilizer_weight")
                self.assertIn("stroke_taper_enabled", preset, f"Preset '{preset.get('label')}' missing stroke_taper_enabled")

    def test_i18n_lookup_functions(self):
        """Preset and category display name resolution functions return correct values."""
        # Known presets
        name = get_preset_display_name("Pincel Redondo")
        self.assertTrue(len(name) > 0)

        # Unknown fallback
        self.assertEqual(get_preset_display_name("Custom Nonexistent Preset"), "Custom Nonexistent Preset")

        # Categories
        cat_name = get_category_display_name("pencil", "Lápis")
        self.assertTrue(len(cat_name) > 0)
        self.assertEqual(get_category_display_name("unknown_cat", "Default"), "Default")

    def test_param_groups_integrity(self):
        """Param groups set is complete."""
        expected_groups = {
            "size_opacity", "geometry", "jitters", "scatter", "textures",
            "velocity", "pencil_params", "inker_params", "marker_params",
            "blur_params", "smudge_params"
        }
        self.assertEqual(PARAM_GROUPS, expected_groups)


if __name__ == "__main__":
    unittest.main()
