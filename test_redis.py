import os
import asyncio
import trio
import trio_asyncio
import aioredis
import dotenv


async def main(redis_url):
    redis = await trio_asyncio.aio_as_trio(aioredis.from_url)(
        redis_url,
        decode_responses=True,
    )
    await trio_asyncio.aio_as_trio(redis.set("my-phone", "+79166138405"))
    value = await trio_asyncio.aio_as_trio(redis.get("my-phone"))
    print(value)


async def async_main_wrapper(redis_url):
    async with trio_asyncio.open_loop() as loop:
        assert loop == asyncio.get_event_loop()
        await main(redis_url)


if __name__ == "__main__":
    dotenv.load_dotenv()
    redis_url_env = os.environ['REDIS_URL']
    trio.run(async_main_wrapper, redis_url_env)
