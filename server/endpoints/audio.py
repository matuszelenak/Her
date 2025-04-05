from fastapi import APIRouter

from providers import providers
from providers.base import TextToSpeechProvider

audio_router = APIRouter()


@audio_router.get('/voices')
async def get_voices():
    tts_provider: TextToSpeechProvider = providers.get('tts')
    if tts_provider:
        voices = await tts_provider.get_voices()

        return voices

    return []
