import logging
from dataclasses import dataclass

from pymatgen.core.sites import PeriodicSite  # pyright: ignore[reportMissingImports]
from pymatgen.core.structure import Structure  # pyright: ignore[reportMissingImports]

from mof_bandgap.constants import GRAPH_CUTOFF_RADIUS, GRAPH_MAX_ATOMS, GRAPH_MAX_NEIGHBORS
from mof_bandgap.mapper import Mapper

logger = logging.getLogger(__name__)


@dataclass
class CrystalGraph:
    atomic_numbers: list[int]
    edge_index:     list[list[int]]
    edge_distances: list[float]


def _dominant_atomic_number(site: PeriodicSite) -> int:
    dominant_species = max(site.species.items(), key=lambda item: item[1])[0]
    return int(dominant_species.Z)


def build_crystal_graph(cif_text: str) -> CrystalGraph | None:
    cif_text = Mapper.normalize_cif(cif_text)

    try:
        structure = Structure.from_str(cif_text, fmt="cif")
    except Exception:
        logger.warning("[Dataset] failed to parse cif for graph construction", exc_info=True)
        return None

    atom_count = len(structure)
    if atom_count == 0 or atom_count > GRAPH_MAX_ATOMS:
        logger.warning("[Dataset] structure has %d atom(s), skipping graph construction", atom_count)
        return None

    try:
        atomic_numbers = [_dominant_atomic_number(site) for site in structure]
    except Exception:
        logger.warning("[Dataset] failed to read atomic numbers for graph construction", exc_info=True)
        return None

    try:
        all_neighbors = structure.get_all_neighbors(GRAPH_CUTOFF_RADIUS)
    except Exception:
        logger.warning("[Dataset] failed to find neighbors for graph construction", exc_info=True)
        return None

    edge_index:     list[list[int]] = []
    edge_distances: list[float]     = []
    for site_index, neighbors in enumerate(all_neighbors):
        nearest = sorted(neighbors, key=lambda neighbor: neighbor.nn_distance)[:GRAPH_MAX_NEIGHBORS]
        for neighbor in nearest:
            edge_index.append([site_index, int(neighbor.index)])
            edge_distances.append(float(neighbor.nn_distance))

    if not edge_index:
        logger.warning("[Dataset] no edges found within cutoff radius, skipping structure")
        return None

    return CrystalGraph(atomic_numbers=atomic_numbers, edge_index=edge_index, edge_distances=edge_distances)
