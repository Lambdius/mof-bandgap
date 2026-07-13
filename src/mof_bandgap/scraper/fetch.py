import logging

import httpx

logger = logging.getLogger(__name__)


async def fetch(client: httpx.AsyncClient, base_url: str, name: str) -> bytes:
    response = await client.get(f"{base_url}/MOFdata/{name}.cif")
    response.raise_for_status()
    logger.info("[Fetch] downloaded %s.cif (%d bytes)", name, len(response.content))
    return response.content
