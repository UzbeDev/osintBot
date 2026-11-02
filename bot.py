import asyncio
import logging

from config import bot, dp
from handlers import common, username, email, phone, funstat

# Register Modular Routers
dp.include_router(common.router)
dp.include_router(username.router)
dp.include_router(email.router)
dp.include_router(phone.router)
dp.include_router(funstat.router)

async def main():
    logging.info("Starting OSINT Bot with modular architecture...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
