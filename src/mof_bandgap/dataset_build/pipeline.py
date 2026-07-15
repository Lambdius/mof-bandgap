import logging

from mof_bandgap.config import Settings
from mof_bandgap.dataset_build.builder import DatasetBuilder
from mof_bandgap.dataset_build.samples import iter_samples
from mof_bandgap.infrastructure.database.connect import connect
from mof_bandgap.infrastructure.minio.storage import Storage

logger = logging.getLogger(__name__)


async def run(settings: Settings) -> None:
    storage = Storage.connect(
        endpoint   = settings.minio_endpoint,
        access_key = settings.minio_access_key,
        secret_key = settings.minio_secret_key,
        bucket     = settings.minio_bucket,
        secure     = settings.minio_secure,
    )

    async with connect(settings.database_url) as session:
        builder = DatasetBuilder(session)
        count   = 0
        async for _ in builder.build(iter_samples(session, storage)):
            count += 1

        logger.info("[Dataset] build complete: %d feature row(s) available", count)
