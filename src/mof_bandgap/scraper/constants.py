import re
from enum import IntEnum

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
