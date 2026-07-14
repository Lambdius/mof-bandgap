import logging
from http import HTTPStatus

import httpx

logger = logging.getLogger(__name__)


async def fetch(client: httpx.AsyncClient, base_url: str, name: str) -> bytes | None:
    response = await client.get(f"{base_url}/MOFdata/{name}.cif")

    if response.status_code == HTTPStatus.NOT_FOUND:
        logger.warning("[Fetch] %s.cif not found (404)", name)
        return None

    response.raise_for_status()
    logger.info("[Fetch] downloaded %s.cif (%d bytes)", name, len(response.content))
    return response.content
