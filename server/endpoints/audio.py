from fastapi import APIRouter, HTTPException

from providers import providers
from providers.base import TextToSpeechProvider

audio_router = APIRouter()


@audio_router.get('/voices/{provider}')
async def get_voices(provider: str):
    try:
        tts_provider: TextToSpeechProvider = providers["tts"][provider]
        voices = await tts_provider.get_voices()

        return voices

    except KeyError:
        raise HTTPException(status_code=404)
