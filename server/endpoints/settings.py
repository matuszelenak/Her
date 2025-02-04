from fastapi import APIRouter
from ollama import AsyncClient

from utils.constants import OLLAMA_API_URL

settings_router = APIRouter()


@settings_router.get('/models')
async def get_models():
    models = (await AsyncClient(OLLAMA_API_URL).list())['models']

    return sorted(models, key=lambda m: m['model'])


@settings_router.get('/tools')
async def get_tools():
    return ['get_ip_address_def', 'get_current_moon_phase']
