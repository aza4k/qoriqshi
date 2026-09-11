import random
import asyncio
import logging
from typing import Dict, Tuple, Any, Optional
from aiogram import Bot

logger = logging.getLogger(__name__)

# Faol captchalar xotirada saqlanadi: (chat_id, user_id) -> data
# data = {"correct": int, "attempts_left": int, "msg_id": int, "timeout_task": Task}
active_captchas: Dict[Tuple[int, int], Dict[str, Any]] = {}

def generate_math_captcha() -> Tuple[int, int, int, list]:
    """
    Random matematik misol generatsiya qilish:
    Maksimal yig'indi 30 gacha.
    Qaytaradi: (a, b, correct_answer, options_list)
    """
    a = random.randint(1, 15)
    max_b = max(1, 30 - a)
    b = random.randint(1, max_b)
    correct = a + b

    # correct atrofidagi (yaqin) sonlardan 3 ta unikal noto'g'ri variant tanlaymiz
    candidate_pool = [x for x in range(max(1, correct - 7), correct + 8) if x != correct and x > 0]
    wrong_options = random.sample(candidate_pool, min(3, len(candidate_pool)))

    options = wrong_options + [correct]
    random.shuffle(options)

    return a, b, correct, options

async def kick_user_soft(bot: Bot, chat_id: int, user_id: int):
    """
    Foydalanuvchini guruhdan chiqarish (qora ro'yxatga kiritmasdan).
    Buning uchun ban qilinadi va darhol unban qilinadi.
    """
    try:
        await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
        await bot.unban_chat_member(chat_id=chat_id, user_id=user_id, only_if_banned=True)
        logger.info(f"Foydalanuvchi {user_id} guruhdan {chat_id} chiqarildi (qora ro'yxatsiz).")
    except Exception as e:
        logger.warning(f"Kick error (Bot admin huquqi yo'qmi?): {e}")

async def captcha_timeout_handler(bot: Bot, chat_id: int, user_id: int, delay: int = 300):
    """5 daqiqa ichida javob berilmasa avtomatik guruhdan chiqarish"""
    try:
        await asyncio.sleep(delay)
        # Agar hali ham yechmagan bo'lsa
        captcha_data = active_captchas.pop((chat_id, user_id), None)
        if captcha_data:
            msg_id = captcha_data.get("msg_id")
            if msg_id:
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                except Exception:
                    pass
            # Guruhdan chiqarish
            await kick_user_soft(bot, chat_id, user_id)
    except asyncio.CancelledError:
        pass
