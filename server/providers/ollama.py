from ollama import AsyncClient

from providers import BaseProvider


class OllamaProvider(BaseProvider):
    def __init__(self, base_url):
        self.base_url = base_url

    async def health_status(self):
        try:
            status = await AsyncClient(self.base_url).ps()
            return [model['name'] for model in status['models']]
        except:
            return None
