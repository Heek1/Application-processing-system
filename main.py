import asyncio
import uvicorn

from api import app
from bot import dp, bot


async def run_fastapi():
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def run_bot():
    await dp.start_polling(bot)


async def main():
    await asyncio.gather(
        run_fastapi(),
        run_bot()
    )


if __name__ == "__main__":
    asyncio.run(main())