from pymatgen.core.periodic_table import Element  # pyright: ignore[reportMissingImports]
from rdkit import Chem  # pyright: ignore[reportMissingImports]
from rdkit.Chem import AllChem, Descriptors  # pyright: ignore[reportMissingImports]

from mof_bandgap.constants import DEFAULT_ATOMIC_RADIUS, FINGERPRINT_BITS, FINGERPRINT_RADIUS


def linker_descriptors(smiles: str) -> list[float] | None:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    return [
        Descriptors.MolWt(mol),
        Descriptors.RingCount(mol),
        Descriptors.NumAromaticRings(mol),
        Descriptors.TPSA(mol),
        Descriptors.NumHDonors(mol),
        Descriptors.NumHAcceptors(mol),
        Descriptors.NumRotatableBonds(mol),
        Descriptors.FractionCSP3(mol),
        Descriptors.MolLogP(mol),
        Descriptors.HeavyAtomCount(mol),
    ]


def linker_fingerprint(smiles: str) -> list[float] | None:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    fingerprint = AllChem.GetMorganFingerprintAsBitVect(mol, radius=FINGERPRINT_RADIUS, nBits=FINGERPRINT_BITS)
    return [float(bit) for bit in fingerprint]


def metal_descriptors(symbol: str) -> list[float]:
    element = Element(symbol)

    try:
        electronegativity = float(element.X) if element.X else 0.0
    except Exception:
        electronegativity = 0.0

    try:
        atomic_radius = float(element.atomic_radius) if element.atomic_radius else DEFAULT_ATOMIC_RADIUS
    except Exception:
        atomic_radius = DEFAULT_ATOMIC_RADIUS

    return [
        float(element.Z),
        electronegativity,
        atomic_radius,
        float(element.atomic_mass),
        float(element.group),
        float(element.row),
        float(element.is_transition_metal),
    ]
