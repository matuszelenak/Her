import subprocess
from urllib.parse import urlparse

import requests
from ollama import Client, ResponseError

from utils.constants import WHISPER_API_URL, XTTS2_API_URL, OLLAMA_API_URL


def whisper_status():
    try:
        whisper_parsed_url = urlparse(WHISPER_API_URL)
        subprocess.check_output(['nc', '-zv', f'{whisper_parsed_url.hostname}', f'{whisper_parsed_url.port}'], stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False

def ollama_status():
    try:
        status = Client(OLLAMA_API_URL).ps()
        return [model['name'] for model in status['models']]
    except ResponseError:
        return None


def xtts_status():
    try:
        requests.get(f'{XTTS2_API_URL}/api/ready', timeout=100)
        return True
    except requests.ConnectionError:
        return False
