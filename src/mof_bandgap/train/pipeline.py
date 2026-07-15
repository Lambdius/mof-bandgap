import logging

from sklearn.model_selection import KFold  # type: ignore[import-untyped]
from sqlalchemy import select  # pyright: ignore[reportMissingImports][import-untyped]
from sqlalchemy.ext.asyncio import AsyncSession  # pyright: ignore[reportMissingImports][import-untyped]

from mof_bandgap.config import Settings
from mof_bandgap.constants import CV_N_SPLITS, CV_RANDOM_STATE
from mof_bandgap.infrastructure.database.connect import connect
from mof_bandgap.infrastructure.database.models import Features, MofDataset, MofStructure, StructuralDescriptors
from mof_bandgap.train.models.base import CVMetrics, Metrics, Model
from mof_bandgap.train.models.cgcnn import CGCNNModel
from mof_bandgap.train.models.random_forest import RandomForestModel

logger = logging.getLogger(__name__)

MODELS: list[tuple[str, type[Model]]] = [
    ("RandomForest", RandomForestModel),
    ("CGCNN", CGCNNModel),
]


def _cross_validate(name: str, model_factory: type[Model], features: list[Features]) -> CVMetrics:
    kfold = KFold(n_splits=CV_N_SPLITS, shuffle=True, random_state=CV_RANDOM_STATE)

    folds: list[Metrics] = []
    for fold, (train_idx, val_idx) in enumerate(kfold.split(features), start=1):
        train = [features[i] for i in train_idx]
        val = [features[i] for i in val_idx]

        metrics = model_factory().evaluate(train, val)
        folds.append(metrics)
        logger.info("[Train] %s fold %d/%d mae=%.4f r2=%.4f", name, fold, CV_N_SPLITS, metrics.mae, metrics.r2)

    return CVMetrics.from_folds(folds)


async def _load_features(session: AsyncSession) -> list[Features]:
    defaults = await StructuralDescriptors.defaults(session)
    model_categories = await StructuralDescriptors.model_categories(session)

    stmt = (
        select(MofStructure, MofDataset)
        .join(MofDataset, MofDataset.mof_structure_id == MofStructure.id)
        .where(MofStructure.band_gap.is_not(None))
        .order_by(MofStructure.name)
    )
    rows = (await session.execute(stmt)).all()

    features: list[Features] = []
    for structure, dataset_row in rows:
        assert structure.band_gap is not None
        descriptors = StructuralDescriptors.for_structure(structure, defaults, model_categories)
        features.append(dataset_row.to_features(structure.name, structure.band_gap, descriptors))

    logger.info("[Train] loaded %d dataset row(s) for cross-validation", len(features))
    return features


async def run(settings: Settings) -> None:
    async with connect(settings.database_url) as session:
        features = await _load_features(session)

    if len(features) < CV_N_SPLITS:
        raise RuntimeError("not enough dataset rows for cross-validation; run the dataset build stage first")

    for name, model_factory in MODELS:
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
