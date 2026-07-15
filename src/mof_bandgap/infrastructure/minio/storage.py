import asyncio
import io
import logging
import os
from typing import Self

import certifi  # pyright: ignore[reportMissingImports]
import urllib3  # pyright: ignore[reportMissingImports]
from minio import Minio  # pyright: ignore[reportMissingImports]
from urllib3 import Retry  # pyright: ignore[reportMissingImports]
from urllib3.util import Timeout  # pyright: ignore[reportMissingImports]

from mof_bandgap.constants import MINIO_CONNECTION_POOL_SIZE, MINIO_REQUEST_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


class Storage:
    def __init__(self, client: Minio, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    @classmethod
    def connect(cls, *, endpoint: str, access_key: str, secret_key: str, bucket: str, secure: bool) -> Self:
        timeout     = MINIO_REQUEST_TIMEOUT_SECONDS
        http_client = urllib3.PoolManager(
            timeout   = Timeout(connect=timeout, read=timeout),
            maxsize   = MINIO_CONNECTION_POOL_SIZE,
            cert_reqs = "CERT_REQUIRED",
            ca_certs  = os.environ.get("SSL_CERT_FILE") or certifi.where(),
            retries   = Retry(total=5, backoff_factor=0.2, status_forcelist=[500, 502, 503, 504]),
        )
        client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure, http_client=http_client)
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
        return cls(client, bucket)

    async def save(self, key: str, data: bytes) -> None:
        await asyncio.to_thread(
            self._client.put_object,
            self._bucket,
            key,
            io.BytesIO(data),
            length=len(data),
        )
        logger.info("[Storage] saved %s (%d bytes)", key, len(data))

    async def load(self, key: str) -> bytes:
        def _get() -> bytes:
            response = self._client.get_object(self._bucket, key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()

        data = await asyncio.to_thread(_get)
        logger.info("[Storage] loaded %s (%d bytes)", key, len(data))
        return data
