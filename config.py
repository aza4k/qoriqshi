import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMINS: List[int] = [
        int(admin_id.strip())
        for admin_id in os.getenv("ADMINS", "").split(",")
        if admin_id.strip().isdigit()
    ]
    DB_PATH: str = os.getenv("DB_PATH", "database/bot.db")

config = Config()
