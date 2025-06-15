from typing import Dict, TypedDict

from providers.base import BaseProvider, TextToSpeechProvider
from providers.chatterbox import ChatterBoxAudioProvider
from providers.kokoro import KokoroAudioProvider
from providers.orpheus import OrpheusAudioProvider
from providers.whisper import WhisperProvider
from providers.xtts2 import XTTSProvider
from config import config


class ProviderDict(TypedDict):
    stt: Dict[str, WhisperProvider]
    tts: Dict[str, TextToSpeechProvider]


def initialize_providers() -> ProviderDict:
    p = ProviderDict(stt={}, tts={})

    if config.KOKORO_API_URL:
        p['tts']['kokoro'] = KokoroAudioProvider(config.KOKORO_API_URL)

    if config.ORPHEUS_API_URL:
        p['tts']['orpheus'] = OrpheusAudioProvider(config.ORPHEUS_API_URL)

    if config.CHATTERBOX_API_URL:
        p['tts']['chatterbox'] = ChatterBoxAudioProvider(config.CHATTERBOX_API_URL)

    if config.WHISPER_API_URL:
        p['stt']['whisper'] = WhisperProvider(config.WHISPER_API_URL)

    return p


providers = initialize_providers()
