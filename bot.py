import asyncio
import logging
import sys

# Windows UTF-8 encoding mosligi uchun
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand, BotCommandScopeDefault

from config import config
from database.db import db
from handlers.admin import router as admin_router
from handlers.group import router as group_router
from handlers.user import router as user_router

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def set_bot_commands(bot: Bot):
    """Botning standart menyu buyruqlarini o'rnatish (Asosiy til: Qaraqalpaqsha)"""
    commands_qr = [
        BotCommand(command="mymembers", description="Қосқан адамларым дизими"),
        BotCommand(command="set", description="Топар лимитин белгилеў (Админ)"),
        BotCommand(command="setchannel", description="Мәжбүрий каналды жалғаў (Админ)"),
        BotCommand(command="channel", description="Қосылған каналды көриў"),
        BotCommand(command="help", description="Қолланба ҳәм буйрықлар"),
        BotCommand(command="top", description="ТОП-10 адам қосқан"),
    ]
    commands_uz = [
        BotCommand(command="mymembers", description="Qo'shgan odamlarim ro'yxati"),
        BotCommand(command="set", description="Guruh limitini belgilash (Admin)"),
        BotCommand(command="setchannel", description="Majburiy kanalni ulash (Admin)"),
        BotCommand(command="channel", description="Ulangan kanalni ko'rish"),
        BotCommand(command="help", description="Qo'llanma va buyruqlar"),
        BotCommand(command="top", description="TOP-10 odam qo'shganlar"),
    ]
    commands_ru = [
        BotCommand(command="mymembers", description="Список добавленных мной участников"),
        BotCommand(command="set", description="Установить лимит группы (Админ)"),
        BotCommand(command="setchannel", description="Привязать обязательный канал (Админ)"),
        BotCommand(command="channel", description="Информация о канале"),
        BotCommand(command="help", description="Инструкция и команды"),
        BotCommand(command="top", description="ТОП-10 пригласивших"),
    ]
    commands_en = [
        BotCommand(command="mymembers", description="List of members invited by me"),
        BotCommand(command="set", description="Set group invite limit (Admin)"),
        BotCommand(command="setchannel", description="Link required channel (Admin)"),
        BotCommand(command="channel", description="View linked channel"),
        BotCommand(command="help", description="Guide and commands"),
        BotCommand(command="top", description="TOP-10 inviters"),
    ]
    try:
        await bot.set_my_commands(commands_qr, scope=BotCommandScopeDefault())
        await bot.set_my_commands(commands_uz, scope=BotCommandScopeDefault(), language_code="uz")
        await bot.set_my_commands(commands_ru, scope=BotCommandScopeDefault(), language_code="ru")
        await bot.set_my_commands(commands_en, scope=BotCommandScopeDefault(), language_code="en")
    except Exception as e:
        logger.warning(f"Error setting bot commands: {e}")



async def main():
    if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("DIQQAT: .env faylida BOT_TOKEN ko'rsatilmagan! Iltimos, .env fayliga haqiqiy bot tokenini yozing.")
        return

    # Ma'lumotlar bazasini ishga tushirish
    await db.init_db()

    # Bot va Dispatcher yaratish
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Routerlarni ro'yxatdan o'tkazish
    # Eslatma: Tartib muhim: Admin -> Guruh -> Shaxsiy chat
    dp.include_router(user_router)
    dp.include_router(admin_router)
    dp.include_router(group_router)

    # Bot buyruqlari menyusi
    await set_bot_commands(bot)

    logger.info("Bot muvaffaqiyatli ishga tushdi va xabarlarni kutmoqda...")
    try:
        # Eski o'qilmagan xabarlarni o'tkazib yuborish
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(
            bot,
            allowed_updates=["message", "edited_message", "callback_query", "chat_member", "my_chat_member"]
        )
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
