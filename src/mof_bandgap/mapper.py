import numpy as np  # pyright: ignore[reportMissingImports]
import numpy.typing as npt  # pyright: ignore[reportMissingImports]

from mof_bandgap.constants import OXIDATION_STATE_PATTERN
from mof_bandgap.infrastructure.database.models import Features


class Mapper:
    @staticmethod
    def normalize_cif(text: str) -> str:
        return OXIDATION_STATE_PATTERN.sub(r"\2\1", text)


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
                f.linker_fingerprint
                + f.linker_descriptors
                + f.metal_descriptors
                + f.metal2_descriptors
                + [f.has_interior_metal]
                + f.structural_descriptors
                for f in features
            ]
        )

    @staticmethod
    def to_target(features: list[Features]) -> npt.NDArray[np.float64]:
        return np.array([f.band_gap for f in features])
