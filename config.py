import os
from dotenv import load_dotenv
import pytz

load_dotenv()
BOT_TOKEN = os.environ.get("TOKEN")
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost/islobbot"
)
REDIS_URL = "redis://default:Ti86GjDiqMuqTxvJl9z9QMtNMFOdpR7K@redis-15808.c300.eu-central-1-1.ec2.redns.redis-cloud.com:15808"
ADMIN_CHAT_ID = "591812219"

timezone = pytz.timezone("Europe/Kyiv")
