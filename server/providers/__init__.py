import logging
import os
from typing import Dict

from providers.base import BaseProvider
from providers.kokoro import KokoroAudioProvider
from providers.ollama import OllamaProvider
from providers.openai import OpenAIProvider
from providers.whisper import WhisperProvider
from providers.xtts2 import XTTSProvider

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


def initialize_providers() -> Dict[str, BaseProvider]:
    p = {}
    logger.error('Initializing providers ...')

    kokoro_url = os.environ.get('KOKORO_API_URL')
    if kokoro_url:
        p['tts'] = KokoroAudioProvider(kokoro_url)

    whisper_url = os.environ.get('WHISPER_API_URL')
    if whisper_url:
        p['stt'] = WhisperProvider(whisper_url)

    # xtts_api_url = os.environ.get('XTTS2_API_URL')
    # if xtts_api_url:
    #     p['tts'] = XTTSProvider(xtts_api_url)

    # ollama_api_url = os.environ.get('OLLAMA_API_URL')
    # if ollama_api_url:
    #     p['llm'] = OllamaProvider(ollama_api_url)

    open_api_url = os.environ.get('OPENAI_API_URL')
    if open_api_url:
        p['llm'] = OpenAIProvider(base_url=open_api_url, api_key='nagaega')

    return p


providers = initialize_providers()
