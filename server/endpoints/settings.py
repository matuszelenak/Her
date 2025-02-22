from typing import List

from fastapi import APIRouter
from openai.types import Model

from providers import OpenAIProvider, providers

settings_router = APIRouter()


@settings_router.get('/models')
async def get_models():
    llm_provider: OpenAIProvider = providers['llm']
    models: List[Model] = (await llm_provider.models.list()).data

    return sorted(models, key=lambda m: m.id)


@settings_router.get('/tools')
async def get_tools():
    return ['get_ip_address_def', 'get_current_moon_phase']
