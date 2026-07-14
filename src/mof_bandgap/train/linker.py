import logging
from typing import cast

from pymatgen.core.periodic_table import Element
from pymatgen.core.structure import Molecule, Structure
from rdkit import Chem  # type: ignore[import-untyped]
from rdkit.Chem import rdDetermineBonds  # type: ignore[import-untyped]
from structuregraph_helpers.create import get_structure_graph  # type: ignore[import-untyped]
from structuregraph_helpers.subgraph import get_subgraphs_as_molecules  # type: ignore[import-untyped]

from mof_bandgap.constants import MIN_LINKER_ATOMS
from mof_bandgap.mapper import Mapper

logger = logging.getLogger(__name__)


def _is_metal(symbol: str) -> bool:
    try:
        return bool(Element(symbol).is_metal)
    except Exception:
        return False


def extract_linker_molecule(cif_text: str, metal_symbols: set[str]) -> Molecule | None:
    cif_text = Mapper.normalize_cif(cif_text)

    try:
        structure = Structure.from_str(cif_text, fmt="cif")
    except Exception:
        logger.warning("[Train] failed to parse cif", exc_info=True)
        return None

    present_symbols = {site.specie.symbol for site in structure}
    species_to_remove = {symbol for symbol in present_symbols if _is_metal(symbol)} | metal_symbols

    structure_no_metal = structure.copy()
    try:
        structure_no_metal.remove_species(list(species_to_remove))
    except Exception:
        logger.warning("[Train] failed to strip metal species", exc_info=True)
        return None

    if len(structure_no_metal) == 0:
        logger.warning("[Train] structure is empty after removing metal species")
        return None

    try:
        graph = get_structure_graph(structure_no_metal, method="vesta")
        molecules, *_ = get_subgraphs_as_molecules(graph, prune_long_edges=True)
    except Exception:
        logger.warning("[Train] failed to build structure graph", exc_info=True)
        return None

    if not molecules:
        logger.warning("[Train] no disconnected fragments found")
        return None

    linker = cast(Molecule, max(molecules, key=len))
    if len(linker) < MIN_LINKER_ATOMS:
        logger.warning("[Train] largest fragment is too small to be a linker")
        return None

    return linker


def molecule_to_smiles(molecule: Molecule) -> str | None:
    xyz_lines = [str(len(molecule)), ""]
    xyz_lines.extend(f"{site.specie.symbol} {site.x:.6f} {site.y:.6f} {site.z:.6f}" for site in molecule)
    xyz_block = "\n".join(xyz_lines) + "\n"

    mol = Chem.MolFromXYZBlock(xyz_block)
    if mol is None:
        logger.warning("[Train] rdkit failed to parse linker xyz block")
        return None

    mol_conn = Chem.Mol(mol)
    try:
        rdDetermineBonds.DetermineBonds(mol_conn, charge=0)
    except Exception:
        logger.warning("[Train] failed to determine bonds for linker", exc_info=True)
        return None

    smiles: str = Chem.MolToSmiles(mol_conn)
    return smiles
