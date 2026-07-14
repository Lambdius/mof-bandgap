import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mof_bandgap.infrastructure.database.models import MofStructure
from mof_bandgap.infrastructure.minio.storage import Storage

logger = logging.getLogger(__name__)


@dataclass
class Sample:
    structure: MofStructure
    cif: bytes


async def iter_dataset(session: AsyncSession, storage: Storage) -> AsyncIterator[Sample]:
    stmt = (
        select(MofStructure)
        .where(MofStructure.band_gap.is_not(None), MofStructure.has_file.is_(True))
        .order_by(MofStructure.name)
    )
    structures = (await session.execute(stmt)).scalars().all()

    count = 0
    for structure in structures:
        cif = await storage.load(f"{structure.id}.cif")
        count += 1
        yield Sample(structure=structure, cif=cif)

    logger.info("[Train] streamed %d samples with a known band gap and a stored cif file", count)
