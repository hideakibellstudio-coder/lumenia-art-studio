"""
SoftProofConfig & RenderingIntent — Configuração e contratos de Prova de Cor.
=============================================================================
Define as opções de simulação de gamut de impressão e intenções de renderização.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import IntEnum
from typing import Dict, Any, Optional, Tuple


class RenderingIntent(IntEnum):
    """Intenções canônicas de renderização ICC (LittleCMS)."""
    PERCEPTUAL = 0
    RELATIVE_COLORIMETRIC = 1
    SATURATION = 2
    ABSOLUTE_COLORIMETRIC = 3

    @classmethod
    def get_label(cls, value: int) -> str:
        labels = {
            cls.PERCEPTUAL: "Perceptual (Fotográfico)",
            cls.RELATIVE_COLORIMETRIC: "Colorimétrico Relativo (Padrão)",
            cls.SATURATION: "Saturação (Gráficos/Apresentações)",
            cls.ABSOLUTE_COLORIMETRIC: "Colorimétrico Absoluto (Prova Fiel)",
        }
        return labels.get(value, "Colorimétrico Relativo")


@dataclass
class SoftProofConfig:
    """Parâmetros ativos de simulação de prova de cor (Soft-Proofing)."""

    enabled: bool = False
    proof_profile_id: int = 5                  # Default: FOGRA39 (5) ou SWOP (4)
    custom_proof_icc: Optional[bytes] = None
    custom_proof_name: Optional[str] = None
    rendering_intent: int = int(RenderingIntent.RELATIVE_COLORIMETRIC)
    proof_rendering_intent: int = int(RenderingIntent.RELATIVE_COLORIMETRIC)
    bpc: bool = True                           # Black Point Compensation
    gamut_warning: bool = False                 # Alerta de cores fora de gama
    alarm_color: Tuple[int, int, int, int] = (128, 128, 128, 255)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": bool(self.enabled),
            "proof_profile_id": int(self.proof_profile_id),
            "custom_proof_name": self.custom_proof_name,
            "has_custom_proof": bool(self.custom_proof_icc),
            "rendering_intent": int(self.rendering_intent),
            "proof_rendering_intent": int(self.proof_rendering_intent),
            "bpc": bool(self.bpc),
            "gamut_warning": bool(self.gamut_warning),
            "alarm_color": list(self.alarm_color),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], custom_icc: Optional[bytes] = None) -> SoftProofConfig:
        alarm = data.get("alarm_color", [128, 128, 128, 255])
        if not isinstance(alarm, (list, tuple)) or len(alarm) != 4:
            alarm = (128, 128, 128, 255)
        else:
            alarm = (int(alarm[0]), int(alarm[1]), int(alarm[2]), int(alarm[3]))
        return cls(
            enabled=bool(data.get("enabled", False)),
            proof_profile_id=int(data.get("proof_profile_id", 5)),
            custom_proof_icc=custom_icc,
            custom_proof_name=data.get("custom_proof_name"),
            rendering_intent=int(data.get("rendering_intent", 1)),
            proof_rendering_intent=int(data.get("proof_rendering_intent", 1)),
            bpc=bool(data.get("bpc", True)),
            gamut_warning=bool(data.get("gamut_warning", False)),
            alarm_color=alarm,
        )
