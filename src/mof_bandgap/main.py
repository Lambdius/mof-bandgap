import asyncio
import logging

from mof_bandgap.config import Settings
from mof_bandgap.scraper.pipeline import run as run_scraper
from mof_bandgap.train.pipeline import run as run_training

logger = logging.getLogger(__name__)


async def _run() -> None:
    settings = Settings()
    logging.basicConfig(level=settings.log_level, format="%(message)s")

    if not settings.run_scraper and not settings.run_training:
        raise RuntimeError("nothing to run: enable RUN_SCRAPER and/or RUN_TRAINING")

    if settings.run_scraper:
        await run_scraper(settings)

    if settings.run_training:
        await run_training(settings)


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
