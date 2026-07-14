import logging

from sklearn.model_selection import KFold  # type: ignore[import-untyped]

from mof_bandgap.config import Settings
from mof_bandgap.constants import CV_N_SPLITS, CV_RANDOM_STATE
from mof_bandgap.infrastructure.database.connect import connect
from mof_bandgap.infrastructure.database.models import Features
from mof_bandgap.infrastructure.minio.storage import Storage
from mof_bandgap.train.dataset import iter_dataset
from mof_bandgap.train.features import iter_features
from mof_bandgap.train.models.base import CVMetrics, Metrics, Model
from mof_bandgap.train.models.cgcnn import CGCNNModel
from mof_bandgap.train.models.random_forest import RandomForestModel

logger = logging.getLogger(__name__)


def _cross_validate(name: str, model_factory: type[Model], features: list[Features]) -> CVMetrics:
    kfold = KFold(n_splits=CV_N_SPLITS, shuffle=True, random_state=CV_RANDOM_STATE)

    folds: list[Metrics] = []
    for fold, (train_idx, val_idx) in enumerate(kfold.split(features), start=1):
        train = [features[i] for i in train_idx]
        val = [features[i] for i in val_idx]

        metrics = model_factory().evaluate(train, val)
        folds.append(metrics)
        logger.info(
            "[Train] %s fold %d/%d mae=%.4f r2=%.4f", name, fold, CV_N_SPLITS, metrics.mae, metrics.r2
        )

    return CVMetrics.from_folds(folds)


async def run(settings: Settings) -> None:
    storage = Storage.connect(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        bucket=settings.minio_bucket,
        secure=settings.minio_secure,
    )

    async with connect(settings.database_url) as session:
        features = [feature async for feature in iter_features(session, iter_dataset(session, storage))]

    if len(features) < CV_N_SPLITS:
        raise RuntimeError("not enough samples with usable features to run cross-validation")

    models: list[tuple[str, type[Model]]] = [
        ("RandomForest", RandomForestModel),
        ("CGCNN", CGCNNModel),
    ]

    for name, model_factory in models:
        cv_metrics = _cross_validate(name, model_factory, features)
        logger.info(
            "[Train] %s cv mae=%.4f±%.4f r2=%.4f±%.4f (%d folds)",
            name,
            cv_metrics.mae_mean,
            cv_metrics.mae_std,
            cv_metrics.r2_mean,
            cv_metrics.r2_std,
            CV_N_SPLITS,
        )
