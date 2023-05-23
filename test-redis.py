import asyncio
import trio
import trio_asyncio
import aioredis


async def main():
    redis = aioredis.from_url("redis://localhost", decode_responses=True)
    await redis.set("my-phone", "+79166138405")
    value = await redis.get("my-phone")
    print(value)


async def async_main_wrapper(*args):
    async with trio_asyncio.open_loop() as loop:
        assert loop == asyncio.get_event_loop()
        await main(*args)


if __name__ == "__main__":
    trio.run(async_main_wrapper)
