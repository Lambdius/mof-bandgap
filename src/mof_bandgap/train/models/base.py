import statistics
from dataclasses import dataclass
from typing import Protocol

from mof_bandgap.infrastructure.database.models import Features


@dataclass
class Metrics:
    mae: float
    r2:  float


@dataclass
class CVMetrics:
    mae_mean: float
    mae_std:  float
    r2_mean:  float
    r2_std:   float
    folds:    list[Metrics]

    @classmethod
    def from_folds(cls, folds: list[Metrics]) -> "CVMetrics":
        maes = [fold.mae for fold in folds]
        r2s = [fold.r2 for fold in folds]
        return cls(
            mae_mean = statistics.mean(maes),
            mae_std  = statistics.pstdev(maes) if len(maes) > 1 else 0.0,
            r2_mean  = statistics.mean(r2s),
            r2_std   = statistics.pstdev(r2s) if len(r2s) > 1 else 0.0,
            folds    = folds,
        )


class Model(Protocol):
    def evaluate(self, train: list[Features], val: list[Features]) -> Metrics: ...
