import os
from dotenv import load_dotenv


load_dotenv()
BOT_TOKEN = os.environ.get("TOKEN")
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost/islobbot"
)
ADMIN_CHAT_ID = "591812219"
