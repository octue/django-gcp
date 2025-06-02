import asyncio

from asgiref.sync import async_to_sync


def run_coroutine(handler, **kwargs):
    """Run an async routine, by converting to synchronous if possible"""
    try:
        return async_to_sync(handler)(**kwargs)
    except RuntimeError:
        coroutine = handler(**kwargs)
        return asyncio.get_event_loop().create_task(coroutine)
