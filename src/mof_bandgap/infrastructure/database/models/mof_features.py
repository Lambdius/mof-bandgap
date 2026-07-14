from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import Float, ForeignKey, LargeBinary, Uuid
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from mof_bandgap.constants import FINGERPRINT_BITS
from mof_bandgap.infrastructure.database.base import Base


@dataclass
class Features:
    name: str
    metal_descriptors: list[float]
    metal2_descriptors: list[float]
    has_interior_metal: float
    linker_descriptors: list[float]
    linker_fingerprint: list[float]
    band_gap: float


class MofFeatures(Base):
    __tablename__ = "mof_features"

    mof_structure_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("mof_structures.id"), primary_key=True)
    smiles: Mapped[str]
    metal_descriptors: Mapped[list[float]] = mapped_column(ARRAY(Float))
    metal2_descriptors: Mapped[list[float]] = mapped_column(ARRAY(Float))
    has_interior_metal: Mapped[bool]
    linker_descriptors: Mapped[list[float]] = mapped_column(ARRAY(Float))
    linker_fingerprint: Mapped[bytes] = mapped_column(LargeBinary)

    def to_features(self, name: str, band_gap: float) -> Features:
        from mof_bandgap.mapper import FeatureMapper

        return Features(
            name=name,
            metal_descriptors=self.metal_descriptors,
            metal2_descriptors=self.metal2_descriptors,
            has_interior_metal=float(self.has_interior_metal),
            linker_descriptors=self.linker_descriptors,
            linker_fingerprint=FeatureMapper.unpack_fingerprint(self.linker_fingerprint, FINGERPRINT_BITS),
            band_gap=band_gap,
        )

    @classmethod
    def from_features(cls, structure_id: uuid.UUID, smiles: str, features: Features) -> MofFeatures:
        from mof_bandgap.mapper import FeatureMapper

        return cls(
            mof_structure_id=structure_id,
            smiles=smiles,
            metal_descriptors=features.metal_descriptors,
            metal2_descriptors=features.metal2_descriptors,
            has_interior_metal=bool(features.has_interior_metal),
            linker_descriptors=features.linker_descriptors,
            linker_fingerprint=FeatureMapper.pack_fingerprint(features.linker_fingerprint),
        )
