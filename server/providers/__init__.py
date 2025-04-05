import os
from typing import Dict

from providers.base import BaseProvider
from providers.kokoro import KokoroAudioProvider
from providers.orpheus import OrpheusAudioProvider
from providers.whisper import WhisperProvider
from providers.xtts2 import XTTSProvider


def initialize_providers() -> Dict[str, BaseProvider]:
    p = {}

    kokoro_url = os.environ.get('KOKORO_API_URL')
    if kokoro_url:
        p['tts'] = KokoroAudioProvider(kokoro_url)

    orpheus_url = os.environ.get('ORPHEUS_API_URL')
    if orpheus_url:
        p['tts'] = OrpheusAudioProvider(orpheus_url)

    whisper_url = os.environ.get('WHISPER_API_URL')
    if whisper_url:
        p['stt'] = WhisperProvider(whisper_url)

    # xtts_api_url = os.environ.get('XTTS2_API_URL')
    # if xtts_api_url:
    #     p['tts'] = XTTSProvider(xtts_api_url)

    return p


providers = initialize_providers()
