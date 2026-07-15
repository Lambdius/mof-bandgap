import re
from enum import IntEnum

# --- Scraper: EC-MOF form ---

LOAD_BUTTON_NAME      = re.compile(r"^Click to Load$", re.IGNORECASE)
MOFSDB_URL_PATTERN    = re.compile(r"mofsdb\.php\?q=")
EXPECTED_SELECT_COUNT = 5
HIDDEN_CLASS          = "d-none"


class Field(IntEnum):
    METAL  = 0
    LINKER = 1
    GROUP  = 2
    METAL2 = 3
    MODEL  = 4


# --- Scraper: properties table parsing ---

UNIT_SUFFIX_PATTERN = re.compile(r"\s*\([^)]*\)\s*$")

# --- Dataset build: loading ---

DATASET_DOWNLOAD_BATCH_SIZE   = 32
MINIO_CONNECTION_POOL_SIZE    = DATASET_DOWNLOAD_BATCH_SIZE
MINIO_REQUEST_TIMEOUT_SECONDS = 30

# --- Dataset build: linker extraction ---

MIN_LINKER_ATOMS = 3

OXIDATION_STATE_PATTERN = re.compile(r"(?<!\.)(\d+)([+-])(?!\d)")

# --- Dataset build: descriptors ---

METAL_DESCRIPTOR_NAMES = [
    "Z",
    "electronegativity",
    "atomic_radius",
    "atomic_mass",
    "group",
    "row",
    "is_transition_metal",
]

FINGERPRINT_BITS      = 512
FINGERPRINT_RADIUS    = 2
DEFAULT_ATOMIC_RADIUS = 1.3

# --- Dataset build: crystal graph ---

GRAPH_CUTOFF_RADIUS = 6.0
GRAPH_MAX_NEIGHBORS = 12
GRAPH_MAX_ATOMS     = 500

# --- Train: RandomForest model ---

RANDOM_FOREST_N_ESTIMATORS = 300
RANDOM_FOREST_RANDOM_STATE = 1

# --- Train: CGCNN model ---

CGCNN_ATOM_EMBED_DIM          = 32
CGCNN_HIDDEN_DIM              = 64
CGCNN_N_CONV_LAYERS           = 3
CGCNN_RBF_BINS                = 20
CGCNN_RBF_WIDTH               = 0.5
CGCNN_LEARNING_RATE           = 1e-3
CGCNN_WEIGHT_DECAY            = 1e-5
CGCNN_EPOCHS                  = 200
CGCNN_RANDOM_STATE            = 0
CGCNN_EARLY_STOPPING_PATIENCE = 20
CGCNN_MAX_ATOMIC_NUMBER       = 100

# --- Dataset build: caching ---

DATASET_COMMIT_BATCH_SIZE = 50

# --- Train: pipeline ---

CV_N_SPLITS     = 5
CV_RANDOM_STATE = 0
