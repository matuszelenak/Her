import asyncio

import httpx
import numpy as np
import starlette
from fastapi import FastAPI
import scipy.io.wavfile as wav
from starlette.websockets import WebSocket


async def main():
    with open('utils/please_streamed.wav', 'wb') as f:

        async with httpx.AsyncClient() as client:
            async with client.stream(
                'POST',
                f'http://10.0.0.2:5005/v1/audio/speech/stream',
                json={
                    "model": "orpheus",
                    "input": 'What the fuck did you just fucking say about me, you little bitch? I\'ll have you know I graduated top of my class in the Navy Seals, and I\'ve been involved in numerous secret raids on Al-Quaeda, and I have over 300 confirmed kills. I am trained in gorilla warfare and I\'m the top sniper in the entire US armed forces. You are nothing to me but just another target. I will wipe you the fuck out with precision the likes of which has never been seen before on this Earth, mark my fucking words. You think you can get away with saying that shit to me over the Internet?',
                    "voice": 'jess',
                    "response_format": "wav",
                    "stream": True,
                }
            ) as resp:
                chunk: bytes
                async for chunk in resp.aiter_bytes(chunk_size=4096):
                    f.write(chunk)
                    samples = np.frombuffer(chunk, dtype=np.int16)
                    # print(samples[:10])

if __name__ == "__main__":
    asyncio.run(main())
