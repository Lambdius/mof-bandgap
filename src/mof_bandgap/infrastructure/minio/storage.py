import asyncio
import io
import logging
from typing import Self

from minio import Minio

logger = logging.getLogger(__name__)


class Storage:
    def __init__(self, client: Minio, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    @classmethod
    def connect(cls, *, endpoint: str, access_key: str, secret_key: str, bucket: str, secure: bool) -> Self:
        client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
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
