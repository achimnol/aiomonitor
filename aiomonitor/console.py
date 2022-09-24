from __future__ import annotations

import asyncio

from concurrent.futures import Future
from typing import Any, Dict, Optional, TextIO

import aioconsole

from .telnet import TelnetClient


async def init_console_server(
    host: str,
    port: int,
    locals: Optional[Dict[str, Any]],
    monitor_loop: asyncio.AbstractEventLoop,
) -> asyncio.AbstractServer:
    ui_loop = asyncio.get_running_loop()
    done = asyncio.Event()

    async def _start(done: asyncio.Event) -> asyncio.AbstractServer:
        def _factory(streams: Any = None) -> aioconsole.AsynchronousConsole:
            return aioconsole.AsynchronousConsole(
                locals=locals, streams=streams, loop=monitor_loop
            )

        server = await aioconsole.start_interactive_server(
            host=host,
            port=port,
            factory=_factory,
            loop=monitor_loop,
        )
        ui_loop.call_soon_threadsafe(done.set)
        return server

    console_future = asyncio.run_coroutine_threadsafe(
        _start(done),
        loop=monitor_loop,
    )
    await done.wait()
    return console_future.result()


async def close_server(
    server: asyncio.AbstractServer,
    monitor_loop: asyncio.AbstractEventLoop,
) -> None:
    ui_loop = asyncio.get_running_loop()
    done = asyncio.Event()

    async def _close(done: asyncio.Event) -> None:
        server.close()
        await server.wait_closed()
        ui_loop.call_soon_threadsafe(done.set)

    asyncio.run_coroutine_threadsafe(_close(done), loop=monitor_loop)
    await done.wait()


async def console_proxy(sin: TextIO, sout: TextIO, host: str, port: int) -> None:
    async with TelnetClient(host, port, sin, sout) as client:
        await client.interact()
