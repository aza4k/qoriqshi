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
    
    # PostgreSQL sozlamalari (Railway / Docker / Standalone)
    _raw_db_url: str = (
        os.getenv("DATABASE_URL")
        or os.getenv("DATABASE_PRIVATE_URL")
        or os.getenv("DATABASE_PUBLIC_URL")
        or ""
    ).strip()
    if _raw_db_url.startswith("postgres://"):
        DATABASE_URL: str = _raw_db_url.replace("postgres://", "postgresql://", 1)
    else:
        DATABASE_URL: str = _raw_db_url

config = Config()

