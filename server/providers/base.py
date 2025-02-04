class BaseProvider:
    async def health_status(self):
        raise NotImplementedError



class TextToSpeechProvider(BaseProvider):
    async def get_voices(self):
        raise NotImplementedError

    async def generate_audio(self, text: str, voice: str):
        raise NotImplementedError
