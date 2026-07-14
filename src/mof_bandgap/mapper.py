import uuid

import numpy as np
import numpy.typing as npt
import torch

from mof_bandgap.constants import CGCNN_MIN_STD, OXIDATION_STATE_PATTERN
from mof_bandgap.infrastructure.database.models import Features, MofStructure
from mof_bandgap.scraper.algorithms.base import ScrapeResult


class Mapper:
    @staticmethod
    def normalize_cif(text: str) -> str:
        return OXIDATION_STATE_PATTERN.sub(r"\2\1", text)

    @staticmethod
    def to_float(value: str | None) -> float | None:
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    @staticmethod
    def to_structure(result: ScrapeResult) -> MofStructure:
        properties = result.properties
        selections = result.selections
        return MofStructure(
            id=uuid.uuid4(),
            name=result.name,
            metal=selections.get("METAL"),
            linker_code=selections.get("LINKER"),
            group=selections.get("GROUP"),
            metal2=selections.get("METAL2"),
            model=selections.get("MODEL"),
            volume=Mapper.to_float(properties.get("Volume")),
            density=Mapper.to_float(properties.get("Density")),
            av_void_fraction=Mapper.to_float(properties.get("AV_Void_Fraction")),
            gsa=Mapper.to_float(properties.get("GSA")),
            vsa=Mapper.to_float(properties.get("VSA")),
            lcd=Mapper.to_float(properties.get("LCD")),
            poav_void_fraction=Mapper.to_float(properties.get("POAV_Void_Fraction")),
            e_f=Mapper.to_float(properties.get("E_f")),
            e_b=Mapper.to_float(properties.get("E_b")),
            band_gap=Mapper.to_float(properties.get("Band_Gap")),
            dbc_up=Mapper.to_float(properties.get("DBC_Up")),
            dbc_down=Mapper.to_float(properties.get("DBC_Down")),
            metal_center=properties.get("Metal_Center") or None,
            linker=properties.get("Linker") or None,
        )


class FeatureMapper:
    @staticmethod
    def pack_fingerprint(fingerprint: list[float]) -> bytes:
        return np.packbits(np.array(fingerprint, dtype=np.uint8)).tobytes()

    @staticmethod
    def unpack_fingerprint(data: bytes, n_bits: int) -> list[float]:
        bits = np.unpackbits(np.frombuffer(data, dtype=np.uint8), count=n_bits)
        return [float(bit) for bit in bits]

    @staticmethod
    def to_forest_matrix(features: list[Features]) -> npt.NDArray[np.float64]:
        return np.array(
            [
                f.linker_fingerprint + f.metal_descriptors + f.metal2_descriptors + [f.has_interior_metal]
                for f in features
            ]
        )

    @staticmethod
    def to_node_matrix(features: list[Features]) -> npt.NDArray[np.float64]:
        return np.array([f.metal_descriptors for f in features])

    @staticmethod
    def to_edge_matrix(features: list[Features]) -> npt.NDArray[np.float64]:
        return np.array([f.linker_descriptors + [f.has_interior_metal] + f.metal2_descriptors for f in features])

    @staticmethod
    def to_target(features: list[Features]) -> npt.NDArray[np.float64]:
        return np.array([f.band_gap for f in features])

    @staticmethod
    def normalize(
        train: npt.NDArray[np.float64], val: npt.NDArray[np.float64]
    ) -> tuple[torch.Tensor, torch.Tensor]:
        mean = train.mean(axis=0)
        std = train.std(axis=0)
        std[std < CGCNN_MIN_STD] = 1.0
        return (
            torch.tensor((train - mean) / std, dtype=torch.float32),
            torch.tensor((val - mean) / std, dtype=torch.float32),
        )
