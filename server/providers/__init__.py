import os
from typing import Dict, TypedDict

from providers.base import BaseProvider, TextToSpeechProvider
from providers.kokoro import KokoroAudioProvider
from providers.orpheus import OrpheusAudioProvider
from providers.whisper import WhisperProvider
from providers.xtts2 import XTTSProvider


class ProviderDict(TypedDict):
    stt: Dict[str, WhisperProvider]
    tts: Dict[str, TextToSpeechProvider]


def initialize_providers() -> ProviderDict:
    p = ProviderDict(stt={}, tts={})

    kokoro_url = os.environ.get('KOKORO_API_URL')
    if kokoro_url:
        p['tts']['kokoro'] = KokoroAudioProvider(kokoro_url)

    orpheus_url = os.environ.get('ORPHEUS_API_URL')
    if orpheus_url:
        p['tts']['orpheus'] = OrpheusAudioProvider(orpheus_url)

    whisper_url = os.environ.get('WHISPER_API_URL')
    if whisper_url:
        p['stt']['whisper'] = WhisperProvider(whisper_url)

    return p


providers = initialize_providers()
