import asyncio
import html
from typing import Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

async def delete_message_delayed(bot: Bot, chat_id: int, message_id: int, delay: int = 7):
    """Xabarni belgilangan soniyadan so'ng avtomatik o'chirish"""
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

def get_user_mention(user_id: int, full_name: str, username: Optional[str] = None) -> str:
    """Xavfsiz HTML mention yaratish"""
    safe_name = html.escape(full_name or "Foydalanuvchi")
    return f'<a href="tg://user?id={user_id}">{safe_name}</a>'

def get_add_to_group_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    """Guruhga qo'shish tugmasi"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Botni guruhga qo'shish",
                    url=f"https://t.me/{bot_username}?startgroup=true&admin=post_messages+delete_messages+restrict_members"
                )
            ]
        ]
    )
    return keyboard
