import re
from enum import IntEnum

# --- Scraper: EC-MOF form ---

LOAD_BUTTON_NAME = re.compile(r"^Click to Load$", re.IGNORECASE)
MOFSDB_URL_PATTERN = re.compile(r"mofsdb\.php\?q=")
EXPECTED_SELECT_COUNT = 5
HIDDEN_CLASS = "d-none"


class Field(IntEnum):
    METAL = 0
    LINKER = 1
    GROUP = 2
    METAL2 = 3
    MODEL = 4


# --- Scraper: properties table parsing ---

UNIT_SUFFIX_PATTERN = re.compile(r"\s*\([^)]*\)\s*$")

# --- Train: linker extraction ---

MIN_LINKER_ATOMS = 3

OXIDATION_STATE_PATTERN = re.compile(r"(?<!\.)(\d+)([+-])(?!\d)")

# --- Train: descriptors ---

DESCRIPTOR_NAMES = [
    "MolWt",
    "NumRings",
    "NumAromaticRings",
    "TPSA",
    "NumHDonors",
    "NumHAcceptors",
    "NumRotatableBonds",
    "FractionCSP3",
    "MolLogP",
    "HeavyAtomCount",
]

METAL_DESCRIPTOR_NAMES = [
    "Z",
    "electronegativity",
    "atomic_radius",
    "atomic_mass",
    "group",
    "row",
    "is_transition_metal",
]

FINGERPRINT_BITS = 2048
FINGERPRINT_RADIUS = 2
DEFAULT_ATOMIC_RADIUS = 1.3

# --- Train: RandomForest model ---

RANDOM_FOREST_N_ESTIMATORS = 300
RANDOM_FOREST_RANDOM_STATE = 1

# --- Train: CGCNN model ---

CGCNN_HIDDEN_DIM = 64
CGCNN_N_CONV_LAYERS = 3
CGCNN_LEARNING_RATE = 1e-3
CGCNN_WEIGHT_DECAY = 1e-5
CGCNN_EPOCHS = 200
CGCNN_MIN_STD = 1e-8
CGCNN_RANDOM_STATE = 0

# --- Train: pipeline ---

TRAIN_TEST_SIZE = 0.2
TRAIN_TEST_SPLIT_RANDOM_STATE = 0
