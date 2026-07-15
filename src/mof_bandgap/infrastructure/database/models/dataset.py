from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import Float, ForeignKey, LargeBinary, Uuid  # pyright: ignore[reportMissingImports]
from sqlalchemy.dialects.postgresql import ARRAY, JSONB  # pyright: ignore[reportMissingImports]
from sqlalchemy.orm import Mapped, mapped_column  # pyright: ignore[reportMissingImports]

from mof_bandgap.constants import FINGERPRINT_BITS
from mof_bandgap.infrastructure.database.base import Base


@dataclass
class Features:
    edge_index:             list[list[int]]
    metal_descriptors:      list[float]
    metal2_descriptors:     list[float]
    linker_descriptors:     list[float]
    linker_fingerprint:     list[float]
    structural_descriptors: list[float]
    edge_distances:         list[float]
    atomic_numbers:         list[int]
    has_interior_metal:     float
    band_gap:               float
    name:                   str


class MofDataset(Base):
    __tablename__ = "datasets"

    mof_structure_id:   Mapped[uuid.UUID]       = mapped_column(Uuid, ForeignKey("mof_structures.id"), primary_key=True)
    metal_descriptors:  Mapped[list[float]]     = mapped_column(ARRAY(Float))
    metal2_descriptors: Mapped[list[float]]     = mapped_column(ARRAY(Float))
    linker_descriptors: Mapped[list[float]]     = mapped_column(ARRAY(Float))
    edge_index:         Mapped[list[list[int]]] = mapped_column(JSONB)
    edge_distances:     Mapped[list[float]]     = mapped_column(JSONB)
    linker_fingerprint: Mapped[bytes]           = mapped_column(LargeBinary)
    atomic_numbers:     Mapped[list[int]]       = mapped_column(JSONB)
    has_interior_metal: Mapped[bool]
    smiles:             Mapped[str]

    def to_features(self, name: str, band_gap: float, structural_descriptors: list[float]) -> Features:
        from mof_bandgap.mapper import FeatureMapper

        return Features(
            linker_fingerprint     = FeatureMapper.unpack_fingerprint(self.linker_fingerprint, FINGERPRINT_BITS),
            has_interior_metal     = float(self.has_interior_metal),
            metal2_descriptors     = self.metal2_descriptors,
            linker_descriptors     = self.linker_descriptors,
            metal_descriptors      = self.metal_descriptors,
            structural_descriptors = structural_descriptors,
            atomic_numbers         = self.atomic_numbers,
            edge_distances         = self.edge_distances,
            edge_index             = self.edge_index,
            band_gap               = band_gap,
            name                   = name,
        )

    @classmethod
    def from_features(cls, structure_id: uuid.UUID, smiles: str, features: Features) -> MofDataset:
        from mof_bandgap.mapper import FeatureMapper

        return cls(
            linker_fingerprint = FeatureMapper.pack_fingerprint(features.linker_fingerprint),
            has_interior_metal = bool(features.has_interior_metal),
            metal2_descriptors = features.metal2_descriptors,
            linker_descriptors = features.linker_descriptors,
            metal_descriptors  = features.metal_descriptors,
            atomic_numbers     = features.atomic_numbers,
            edge_distances     = features.edge_distances,
            edge_index         = features.edge_index,
            mof_structure_id   = structure_id,
            smiles             = smiles,
        )
