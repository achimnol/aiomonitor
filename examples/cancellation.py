import asyncio
import tracemalloc

import aiomonitor


async def chain3():
    await asyncio.sleep(10)


async def chain2():
    t = asyncio.create_task(chain3())
    try:
        await asyncio.sleep(10)
    finally:
        t.cancel()
        await t


async def chain1():
    t = asyncio.create_task(chain2())
    try:
        await asyncio.sleep(10)
    finally:
        t.cancel()
        await t


async def chain_main():
    try:
        while True:
            t = asyncio.create_task(chain1())
            await asyncio.sleep(0.5)
            t.cancel()
    finally:
        print("terminating chain_main")


async def self_cancel_main():
    async def do_self_cancel(tick):
        await asyncio.sleep(tick)
        raise asyncio.CancelledError("self-cancelled")

    try:
        while True:
            await asyncio.sleep(0.21)
            asyncio.create_task(do_self_cancel(0.2))
    finally:
        print("terminating self_cancel_main")


async def unhandled_exc_main():
    async def do_unhandled(tick):
        await asyncio.sleep(tick)
        return 1 / 0

    try:
        while True:
            try:
                await asyncio.create_task(do_unhandled(0.2))
            except ZeroDivisionError:
                continue
    finally:
        print("terminating unhandled_exc_main")


async def main():
    loop = asyncio.get_running_loop()
    with aiomonitor.start_monitor(loop, hook_task_factory=True):
        chain_main_task = asyncio.create_task(chain_main())
        self_cancel_main_task = asyncio.create_task(self_cancel_main())
        unhandled_exc_main_task = asyncio.create_task(unhandled_exc_main())
        tracemalloc.start()
        try:
            while True:
                await asyncio.sleep(10)
        finally:
            print("cancelling")
            chain_main_task.cancel()
            self_cancel_main_task.cancel()
            unhandled_exc_main_task.cancel()
            await asyncio.gather(
                chain_main_task,
                self_cancel_main_task,
                unhandled_exc_main_task,
                return_exceptions=True,
            )

            print("memory footprint")
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics("lineno")
            print("[ Top 10 ]")
            for stat in top_stats[:10]:
                print(stat)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("terminated")
