import asyncio
import logging

import httpx

from mof_bandgap.config import Settings
from mof_bandgap.infrastructure.database.connect import connect
from mof_bandgap.infrastructure.minio.storage import Storage
from mof_bandgap.mapper import Mapper
from mof_bandgap.scraper.algorithms.ec_mof import EcMofAlgorithm
from mof_bandgap.scraper.browser import Browser
from mof_bandgap.scraper.fetch import fetch

logger = logging.getLogger(__name__)


async def _run() -> None:
    settings = Settings()
    logging.basicConfig(level=settings.log_level, format="%(message)s")

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
            headless=True,
            click_timeout_ms=settings.scraper_click_timeout_ms,
            page_load_timeout_ms=settings.scraper_page_load_timeout_ms,
        ) as browser,
        httpx.AsyncClient() as client,
    ):
        algorithm = EcMofAlgorithm(browser)

        if not await algorithm.check_ready():
            raise RuntimeError("EC-MOF form is missing expected elements")

        async for result in algorithm.run():
            structure = Mapper.to_structure(result)
            cif = await fetch(client, settings.mof_site_base_url, result.name)
            await storage.save(f"{structure.id}.cif", cif)

            session.add(structure)
            await session.commit()

            logger.info("[Main] saved %s (%s.cif, %d bytes)", result.name, structure.id, len(cif))


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
