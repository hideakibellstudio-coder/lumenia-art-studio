"""
ICCProfileInfo — Representação canônica de metadados e bytes de um perfil ICC.
=============================================================================
Unifica perfis nativos embutidos do Aladyn e perfis ICC externos (.icc / .icm).
"""

from __future__ import annotations
import hashlib
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class ICCProfileInfo:
    """Metadados e conteúdo binário de um perfil de cor ICC/ICM."""

    id: int
    name: str
    category: str = "Digital (RGB)"
    description: str = ""
    color_space: str = "RGB"          # "RGB", "CMYK", "GRAY"
    connection_space: str = "XYZ "    # "XYZ ", "Lab "
    gamut: str = ""
    whitepoint: str = "D65 (6500K)"
    transfer: str = "sRGB"
    file_path: Optional[str] = None
    icc_bytes: Optional[bytes] = None
    sha256: str = ""
    is_custom: bool = False

    def __post_init__(self) -> None:
        if self.icc_bytes and not self.sha256:
            self.sha256 = hashlib.sha256(self.icc_bytes).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Serializa os metadados do perfil para consumo pela UI e catálogo."""
        return {
            "id": int(self.id),
            "name": str(self.name),
            "category": str(self.category),
            "description": str(self.description),
            "color_space": str(self.color_space),
            "connection_space": str(self.connection_space),
            "gamut": str(self.gamut),
            "whitepoint": str(self.whitepoint),
            "transfer": str(self.transfer),
            "file_path": str(self.file_path) if self.file_path else None,
            "has_icc_bytes": bool(self.icc_bytes),
            "sha256": str(self.sha256),
            "is_custom": bool(self.is_custom),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], icc_bytes: Optional[bytes] = None) -> ICCProfileInfo:
        return cls(
            id=int(data.get("id", 0)),
            name=str(data.get("name", "Perfil")),
            category=str(data.get("category", "Customizado")),
            description=str(data.get("description", "")),
            color_space=str(data.get("color_space", "RGB")),
            connection_space=str(data.get("connection_space", "XYZ ")),
            gamut=str(data.get("gamut", "")),
            whitepoint=str(data.get("whitepoint", "D65 (6500K)")),
            transfer=str(data.get("transfer", "")),
            file_path=data.get("file_path"),
            icc_bytes=icc_bytes,
            sha256=str(data.get("sha256", "")),
            is_custom=bool(data.get("is_custom", False)),
        )
