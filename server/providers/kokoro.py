import uuid

import httpx

from utils.session import Session


async def generate_audio(session: Session, text: str):
    _id = str(uuid.uuid4())
    filename = f'/tts_output/{_id}.mp3'

    async with httpx.AsyncClient() as client:
        with open(filename, 'wb') as f:
            async with client.stream(
                    'POST',
                    f'http://10.0.0.2:8880/v1/audio/speech',
                    json={
                        "model": "kokoro",
                        "input": text,
                        "voice": "af_sky+af_bella",
                        "response_format": "mp3",
                        "stream": True,
                    }
            ) as resp:
                async for chunk in resp.aiter_bytes(chunk_size=512):
                    f.write(chunk)

    return f'{_id}.mp3'
