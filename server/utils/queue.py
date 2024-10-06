import asyncio


async def empty_queue(queue):
    try:
        while not queue.empty():
            queue.get_nowait()
            queue.task_done()
    except asyncio.QueueEmpty:
        pass
