import asyncio
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass

from sqlalchemy import select  # pyright: ignore[reportMissingImports]
from sqlalchemy.ext.asyncio import AsyncSession  # pyright: ignore[reportMissingImports]

from mof_bandgap.constants import DATASET_DOWNLOAD_BATCH_SIZE
from mof_bandgap.infrastructure.database.models import MofStructure
from mof_bandgap.infrastructure.minio.storage import Storage

logger = logging.getLogger(__name__)


@dataclass
class Sample:
    structure: MofStructure
    cif:       bytes


async def _load_sample(storage: Storage, structure: MofStructure) -> Sample:
    cif = await storage.load(f"{structure.id}.cif")
    return Sample(structure=structure, cif=cif)


async def iter_samples(session: AsyncSession, storage: Storage) -> AsyncIterator[Sample]:
    stmt = (
        select(MofStructure)
        .where(MofStructure.band_gap.is_not(None), MofStructure.has_file.is_(True))
        .order_by(MofStructure.name)
    )
    structures = (await session.execute(stmt)).scalars().all()

    count = 0
    for batch_start in range(0, len(structures), DATASET_DOWNLOAD_BATCH_SIZE):
        batch = structures[batch_start : batch_start + DATASET_DOWNLOAD_BATCH_SIZE]
        for coro in asyncio.as_completed([_load_sample(storage, structure) for structure in batch]):
            sample = await coro
            count += 1
            yield sample

    logger.info("[Dataset] streamed %d samples with a known band gap and a stored cif file", count)
