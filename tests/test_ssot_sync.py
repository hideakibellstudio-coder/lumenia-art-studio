"""
Testes de Validação do Single Source of Truth (SSoT): Borracha Nativa e Presets.
================================================================================
"""

import sys
import os
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from ui.core.engine.stabilizer_hub import StabilizerHub
from plugins.ui.brush_plugin.presets_data import (
    BRUSH_CATEGORIES,
    CATEGORY_DEFAULT_STABILIZER,
    PRESET_SPECIFIC_STABILIZER,
)


class TestSsotSync(unittest.TestCase):

    def test_presets_have_calibrated_stabilizer_weights(self):
        """Garante que todas as receitas de pincel possuem stabilizer_weight calibrado."""
        self.assertGreater(len(BRUSH_CATEGORIES), 0)
        
        total_presets = 0
        for cat in BRUSH_CATEGORIES:
            cat_id = cat.get("id")
            presets = cat.get("presets", [])
            for p in presets:
                total_presets += 1
                self.assertIn(
                    "stabilizer_weight",
                    p,
                    f"Preset '{p.get('label')}' na categoria '{cat_id}' não possui stabilizer_weight."
                )
                weight = p["stabilizer_weight"]
                self.assertTrue(
                    0.0 <= weight <= 1.0,
                    f"Peso {weight} inválido no preset '{p.get('label')}'"
                )

        self.assertGreater(total_presets, 20)

    def test_specific_presets_calibration(self):
        """Verifica a calibração de ferramentas-chave."""
        # G-Pen deve ser 65% (Lineart)
        gpen = None
        for cat in BRUSH_CATEGORIES:
            for p in cat.get("presets", []):
                if p.get("label") == "G-Pen (Mangá)":
                    gpen = p
                    break
        self.assertIsNotNone(gpen)
        self.assertEqual(gpen["stabilizer_weight"], 0.65)

        # Lápis HB deve ser 20% (Fluido)
        pencil_hb = None
        for cat in BRUSH_CATEGORIES:
            for p in cat.get("presets", []):
                if p.get("label") == "Lápis HB (Médio)":
                    pencil_hb = p
                    break
        self.assertIsNotNone(pencil_hb)
        self.assertEqual(pencil_hb["stabilizer_weight"], 0.20)

        # Borracha Dura deve ser 30%
        hard_eraser = None
        for cat in BRUSH_CATEGORIES:
            for p in cat.get("presets", []):
                if p.get("label") == "Borracha Dura":
                    hard_eraser = p
                    break
        self.assertIsNotNone(hard_eraser)
        self.assertEqual(hard_eraser["stabilizer_weight"], 0.30)

    def test_preset_selection_propagates_to_stabilizer_hub(self):
        """Verifica se carregar o preset G-Pen atualiza o StabilizerHub para 65% (Lineart)."""
        hub = StabilizerHub.instance()

        # Simula carregamento de preset de Lápis (20%)
        hub.set_fine_tuning_pct(int(0.20 * 100), source="preset")
        self.assertEqual(hub.fine_tuning_pct, 20)
        self.assertEqual(hub.current_profile, "fluid")

        # Simula carregamento de G-Pen (65%)
        hub.set_fine_tuning_pct(int(0.65 * 100), source="preset")
        self.assertEqual(hub.fine_tuning_pct, 65)
        self.assertEqual(hub.current_profile, "lineart")


if __name__ == "__main__":
    unittest.main()
