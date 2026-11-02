import os
import logging
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from google import genai

# Load Environment Variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FUNSTAT_API_KEY = os.getenv("FUNSTAT_API_KEY", "")

logging.basicConfig(level=logging.INFO)

# Core Instances
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
ai_client = genai.Client(api_key=GEMINI_API_KEY)
thread_pool = ThreadPoolExecutor(max_workers=20)
