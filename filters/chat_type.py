from typing import Union, List
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated
from config import config

class ChatTypeFilter(BaseFilter):
    def __init__(self, chat_types: Union[str, List[str]]):
        if isinstance(chat_types, str):
            self.chat_types = [chat_types]
        else:
            self.chat_types = chat_types

    async def __call__(self, event: Union[Message, CallbackQuery, ChatMemberUpdated]) -> bool:
        if isinstance(event, CallbackQuery):
            chat = event.message.chat if event.message else None
        else:
            chat = getattr(event, "chat", None)

        if not chat:
            return False
        return chat.type in self.chat_types

from utils.cache import cache

class IsGroupAdminFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        if message.chat.type not in ["group", "supergroup"]:
            return False

        # 1. Guruh anonim admini sifatida yozilganda
        if message.sender_chat and message.sender_chat.id == message.chat.id:
            return True
        if message.from_user and message.from_user.username == "GroupAnonymousBot":
            return True

        if not message.from_user:
            return False

        # 2. Bot asosiy egasi (config.ADMINS)
        if message.from_user.id in config.ADMINS:
            return True

        # 3. Keshdan tekshiramiz
        cached_admins = cache.get_admins(message.chat.id)
        if cached_admins is not None:
            return message.from_user.id in cached_admins

        # 4. Keshda bo'lmasa, Telegram API dan adminlarni olib keshlaymiz
        try:
            admins = await message.bot.get_chat_administrators(message.chat.id)
            admin_ids = {admin.user.id for admin in admins}
            cache.set_admins(message.chat.id, admin_ids, ttl=300)
            return message.from_user.id in admin_ids
        except Exception:
            # Agar bot admin emasligi sababli get_chat_administrators ishlamasa:
            try:
                member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
                return member.status in ["creator", "administrator"]
            except Exception:
                return False


