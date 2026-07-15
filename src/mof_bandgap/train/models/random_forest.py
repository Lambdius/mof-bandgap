from sklearn.ensemble import RandomForestRegressor  # type: ignore[import-untyped]
from sklearn.metrics import mean_absolute_error, r2_score  # type: ignore[import-untyped]

from mof_bandgap.constants import RANDOM_FOREST_N_ESTIMATORS, RANDOM_FOREST_RANDOM_STATE
from mof_bandgap.infrastructure.database.models import Features
from mof_bandgap.mapper import FeatureMapper
from mof_bandgap.train.models.base import Metrics


class RandomForestModel:
    def evaluate(self, train: list[Features], val: list[Features]) -> Metrics:
        model = RandomForestRegressor(
            n_estimators=RANDOM_FOREST_N_ESTIMATORS, random_state=RANDOM_FOREST_RANDOM_STATE, n_jobs=-1
        )
        model.fit(FeatureMapper.to_forest_matrix(train), FeatureMapper.to_target(train))

        predictions = model.predict(FeatureMapper.to_forest_matrix(val))
        target      = FeatureMapper.to_target(val)

        return Metrics(
            mae=float(mean_absolute_error(target, predictions)), r2=float(r2_score(target, predictions))
        )
