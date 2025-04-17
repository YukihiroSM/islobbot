import json
import os

import pytz
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.environ.get("TOKEN")
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost/islobbot"
)
ADMIN_CHAT_IDS = json.loads(os.environ.get("ADMIN_CHAT_IDS"))

timezone = pytz.timezone("Europe/Kyiv")

BASE_DIR = os.getcwd()
