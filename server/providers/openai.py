from openai import AsyncClient

from providers import BaseProvider


class OpenAIProvider(AsyncClient, BaseProvider):
    async def health_status(self):
        try:
            await self.models.list(timeout=300)
            return 'healthy'
        except:
            return 'unavailable'
