import asyncio
import json
import logging

# import scipy
import websockets

from utils.constants import WHISPER_API_URL
from utils.session import Session

logger = logging.getLogger(__name__)


async def stt_sender(session: Session, received_speech_queue: asyncio.Queue):
    receiver_task = None
    try:
        async for stt_socket in websockets.connect(WHISPER_API_URL):
            receiver_task = asyncio.create_task(stt_receiver(session, stt_socket))

            try:
                while True:
                    samples = await received_speech_queue.get()
                    if samples is None:
                        await stt_socket.send(json.dumps({
                            'commit': True
                        }))
                    else:
                        await stt_socket.send(json.dumps({
                            'samples': samples
                        }))
            except websockets.exceptions.ConnectionClosedError:
                logger.warning('STT socket disconnected, will attempt new connection')


    except asyncio.CancelledError:
        logger.warning('STT Task cancelled')
    except Exception as e:
        logger.error('STT task exception', exc_info=True)
        logger.error(str(e))
    finally:
        if receiver_task is not None:
            receiver_task.cancel()


async def stt_receiver(session: Session, socket):
    while True:
        prompt_words = []

        async for message in socket:
            resp = json.loads(message)
            logger.warning(resp)

            await session.client_socket.send_json({
                'type': 'stt_output',
                'segment': resp
            })

            if resp.get('complete'):
                prompt_words.extend(resp['words'])

            if resp.get('final'):
                session.prompt = ' '.join(prompt_words)
                logger.warning(f'Setting prompt to {session.prompt}')

                break
