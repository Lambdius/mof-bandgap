import logging

from sklearn.model_selection import train_test_split  # type: ignore[import-untyped]

from mof_bandgap.config import Settings
from mof_bandgap.constants import TRAIN_TEST_SIZE, TRAIN_TEST_SPLIT_RANDOM_STATE
from mof_bandgap.infrastructure.database.connect import connect
from mof_bandgap.infrastructure.minio.storage import Storage
from mof_bandgap.train.dataset import iter_dataset
from mof_bandgap.train.features import iter_features
from mof_bandgap.train.models.base import Model
from mof_bandgap.train.models.cgcnn import CGCNNModel
from mof_bandgap.train.models.random_forest import RandomForestModel

logger = logging.getLogger(__name__)


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

    if len(features) < 2:
        raise RuntimeError("not enough samples with usable features to train on")

    train, val = train_test_split(features, test_size=TRAIN_TEST_SIZE, random_state=TRAIN_TEST_SPLIT_RANDOM_STATE)

    models: list[tuple[str, Model]] = [
        ("RandomForest", RandomForestModel()),
        ("CGCNN", CGCNNModel()),
    ]

    for name, model in models:
        metrics = model.evaluate(train, val)
        logger.info("[Train] %s mae=%.4f r2=%.4f", name, metrics.mae, metrics.r2)
