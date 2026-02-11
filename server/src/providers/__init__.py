from typing import Dict, TypedDict

from src.providers.base import BaseProvider, TextToSpeechProvider, SpeechToTextProvider
from src.providers.chatterbox import ChatterBoxAudioProvider
from src.providers.kokoro import KokoroAudioProvider
from src.providers.nemotron import NemotronProvider
from src.providers.orpheus import OrpheusAudioProvider
from src.providers.whisper import WhisperProvider
from src.providers.xtts2 import XTTSProvider
from src.config import config


class ProviderDict(TypedDict):
    stt: Dict[str, SpeechToTextProvider]
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

    if config.NEMOTRON_API_URL:
        p['stt']['nemotron'] = NemotronProvider(config.NEMOTRON_API_URL)

    return p


providers = initialize_providers()
