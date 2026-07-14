import asyncio
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mof_bandgap.config import Settings
from mof_bandgap.infrastructure.database.connect import connect
from mof_bandgap.infrastructure.database.models import MofStructure
from mof_bandgap.infrastructure.minio.storage import Storage
from mof_bandgap.mapper import Mapper
from mof_bandgap.scraper.algorithms.base import ResumePoint
from mof_bandgap.scraper.algorithms.ec_mof import EcMofAlgorithm
from mof_bandgap.scraper.browser import Browser
from mof_bandgap.scraper.fetch import fetch

logger = logging.getLogger(__name__)


async def _last_resume_point(session: AsyncSession) -> ResumePoint | None:
    stmt = select(MofStructure).order_by(MofStructure.created_at.desc()).limit(1)
    last = (await session.execute(stmt)).scalar_one_or_none()

    if last is None or last.metal is None or last.linker_code is None or last.model is None:
        return None

    return ResumePoint(
        metal=last.metal, linker=last.linker_code, model=last.model, group=last.group, metal2=last.metal2
    )


async def run(settings: Settings) -> None:
    storage = Storage.connect(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        bucket=settings.minio_bucket,
        secure=settings.minio_secure,
    )

    async with (
        connect(settings.database_url) as session,
        Browser.open(
            settings.mof_site_base_url,
            headless=settings.scraper_headless,
            click_timeout_ms=settings.scraper_click_timeout_ms,
            page_load_timeout_ms=settings.scraper_page_load_timeout_ms,
        ) as browser,
        httpx.AsyncClient() as client,
    ):
        algorithm = EcMofAlgorithm(browser)

        if not await algorithm.check_ready():
            raise RuntimeError("EC-MOF form is missing expected elements")

        scraped_names = set((await session.execute(select(MofStructure.name))).scalars().all())
        resume = await _last_resume_point(session)
        logger.info("[Main] resuming: %d structures already scraped, resume point=%s", len(scraped_names), resume)

        try:
            async for result in algorithm.run(resume=resume):
                if result.name in scraped_names:
                    logger.info("[Scrap] skipping %s: already scraped", result.name)
                    continue

                structure = Mapper.to_structure(result)
                cif = await fetch(client, settings.mof_site_base_url, result.name)

                structure.has_file = cif is not None
                if cif is not None:
                    await storage.save(f"{structure.id}.cif", cif)

                session.add(structure)
                await session.commit()
                scraped_names.add(result.name)

                logger.info(
                    "[Main] saved %s (has_file=%s, %s)",
                    result.name,
                    structure.has_file,
                    f"{structure.id}.cif, {len(cif)} bytes" if cif is not None else "no cif file",
                )
        except Exception:
            if not settings.dev_mode:
                raise
            logger.exception("[Scrap] step failed, stopping (dev mode) — browser left open for inspection")
            await asyncio.to_thread(input, "Press Enter to close the browser and exit...")
