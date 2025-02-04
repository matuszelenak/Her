import logging

import httpx

from providers.base import BaseProvider

logger = logging.getLogger(__name__)


class WhisperProvider(BaseProvider):
    def __init__(self, base_url):
        self.base_url = base_url

    async def health_status(self):
        async with httpx.AsyncClient() as client:
            resp = await client.get(f'http://{self.base_url}/health', timeout=500)
            return resp.json()['status']
