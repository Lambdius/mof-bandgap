from dataclasses import dataclass
from typing import Protocol

from mof_bandgap.infrastructure.database.models import Features


@dataclass
class Metrics:
    mae: float
    r2: float


class Model(Protocol):
    def evaluate(self, train: list[Features], val: list[Features]) -> Metrics: ...
