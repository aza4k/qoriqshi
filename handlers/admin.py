import asyncio
import html
from typing import Optional
from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from database.db import db
from filters.chat_type import ChatTypeFilter, IsGroupAdminFilter
from utils.helpers import get_user_mention, delete_message_delayed
from utils.cache import cache
from utils.i18n import tr, clean_alert_text
from config import config
from utils.emojis import (
    EMOJI_BAN, EMOJI_PIN, EMOJI_POINT_DOWN, EMOJI_CHART,
    EMOJI_CHECK, EMOJI_STAR, EMOJI_GREEN_CIRCLE, EMOJI_PARTY,
    EMOJI_HOURGLASS, EMOJI_WARN, EMOJI_LIST, EMOJI_PEOPLE,
    EMOJI_CHANNEL, EMOJI_SHIELD, EMOJI_DOT, EMOJI_CROSS,
    EMOJI_MEDAL_1, EMOJI_MEDAL_2, EMOJI_MEDAL_3, EMOJI_CHART_UP, EMOJI_CHART_DOWN,
    EMOJI_SEARCH, EMOJI_PHONE, EMOJI_RESET, EMOJI_START_TROPHY,
    EMOJI_TARGET, EMOJI_FLAG_UZ, EMOJI_FLAG_QR, EMOJI_FLAG_RU, EMOJI_FLAG_EN,
    CUSTOM_ID_FLAG_UZ, CUSTOM_ID_FLAG_QR, CUSTOM_ID_FLAG_RU, CUSTOM_ID_FLAG_EN
)

router = Router()
router.message.filter(ChatTypeFilter(["group", "supergroup"]), IsGroupAdminFilter())
router.callback_query.filter(ChatTypeFilter(["group", "supergroup"]))

async def send_admin_response(
    message: Message,
    bot: Bot,
    text: str,
    delay: int = 15,
    reply_markup: Optional[InlineKeyboardMarkup] = None
):
    """
    Admin buyrug'ini chatdan darhol o'chirib,
    bot javobini faqat adminga ko'rinadigan qilib (receiver_user_id) yuborish.
    """
    # 1. Admin yuborgan buyruq xabarini o'chiramiz
    try:
        await message.delete()
    except Exception:
        pass

    # 2. Xabarni faqat shu adminga ko'rinadigan qilib jo'natamiz
    admin_id = message.from_user.id if message.from_user else None
    is_anon = bool(message.sender_chat and message.sender_chat.id == message.chat.id)

    msg = None
    try:
        if admin_id and not is_anon:
            msg = await bot.send_message(
                chat_id=message.chat.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML",
                receiver_user_id=admin_id
            )
        else:
            msg = await message.answer(text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        msg = await message.answer(text, reply_markup=reply_markup, parse_mode="HTML")

    # 3. Belgilangan vaqtdan keyin xabarni o'chirish
    if msg:
        asyncio.create_task(delete_message_delayed(bot, message.chat.id, msg.message_id, delay))


@router.message(Command(commands=["set", "limit", "setlimit"]))
async def cmd_set_limit(message: Message, bot: Bot):
    """
    Guruh uchun talab qilinadigan odam qo'shish sonini belgilash:
    /set 5 yoki /limit 10
    """
    group = await db.get_or_create_group(message.chat.id, message.chat.title or "")
    lang = group.get("language") or "qr"

    args = message.text.split()
    if len(args) < 2:
        if lang == "ru":
            text = (
                f"{EMOJI_WARN} <b>Неверный формат команды!</b>\n\n"
                f"Пример: <code>/set 5</code> (чтобы писать, каждый участник должен добавить 5 друзей).\n"
                f"Чтобы отключить лимит: <code>/set 0</code>"
            )
        elif lang == "en":
            text = (
                f"{EMOJI_WARN} <b>Invalid command format!</b>\n\n"
                f"Example: <code>/set 5</code> (each member must invite 5 friends to post).\n"
                f"To disable requirement completely: <code>/set 0</code>"
            )
        elif lang == "uz":
            text = (
                f"{EMOJI_WARN} <b>Noto'g'ri buyruq formati!</b>\n\n"
                f"Misol: <code>/set 5</code> (guruhda yozish uchun har bir a'zo 5 ta odam qo'shishi shart bo'ladi).\n"
                f"Cheklovni butunlay o'chirish uchun: <code>/set 0</code> deb yozing."
            )
        else: # qr
            text = (
                f"{EMOJI_WARN} <b>Надурыс буйрық форматы!</b>\n\n"
                f"Мисал: <code>/set 5</code> (топарда жазыў ушын ҳәрбир ағза 5 адам қосыўы шәрт болады).\n"
                f"Шеклеўди пүткиллей өшириў ушын: <code>/set 0</code> деп жазың."
            )
        await send_admin_response(message, bot, text, delay=10)
        return

    try:
        limit = int(args[1])
        if limit < 0 or limit > 500:
            err_text = {
                "ru": f"{EMOJI_WARN} Лимит должен быть от 0 до 500!",
                "en": f"{EMOJI_WARN} Limit must be between 0 and 500!",
                "uz": f"{EMOJI_WARN} Limit 0 dan 500 gacha bo'lishi kerak!",
                "qr": f"{EMOJI_WARN} Лимит 0 ден 500 ге шекем болыўы керек!"
            }.get(lang, f"{EMOJI_WARN} Лимит 0 ден 500 ге шекем болыўы керек!")
            await send_admin_response(message, bot, err_text, delay=8)
            return
    except ValueError:
        err_text = {
            "ru": f"{EMOJI_WARN} Лимит должен быть целым числом! Пример: <code>/set 5</code>",
            "en": f"{EMOJI_WARN} Limit must be an integer! Example: <code>/set 5</code>",
            "uz": f"{EMOJI_WARN} Limit faqat butun son bo'lishi kerak! Misol: <code>/set 5</code>",
            "qr": f"{EMOJI_WARN} Лимит тек пүтин сан болыўы керек! Мисал: <code>/set 5</code>"
        }.get(lang, f"{EMOJI_WARN} Лимит тек пүтин сан болыўы керек! Мисал: <code>/set 5</code>")
        await send_admin_response(message, bot, err_text, delay=8)
        return

    await db.set_group_limit(message.chat.id, limit, message.chat.title or "")
    cache.invalidate_group_settings(message.chat.id)
    cache.clear_allowed_users(message.chat.id)

    if limit == 0:
        if lang == "ru":
            text = f"{EMOJI_CHECK} <b>Лимит на добавление участников ОТКЛЮЧЕН!</b>\nТеперь все участники могут писать без ограничений."
        elif lang == "en":
            text = f"{EMOJI_CHECK} <b>Member invite requirement DISABLED!</b>\nNow all members can write without restrictions."
        elif lang == "uz":
            text = f"{EMOJI_CHECK} <b>Guruhda a'zo qo'shish cheklovi O'CHIRILDI!</b>\nEndi barcha a'zolar cheklovlarsiz yozishlari mumkin."
        else: # qr
            text = f"{EMOJI_CHECK} <b>Топарда ағза қосыў шеклеўи ӨШИРИЛДИ!</b>\nЕнди барлық ағзалар шеклеўлерсиз жазыўы мүмкин."
    else:
        if lang == "ru":
            text = (
                f"{EMOJI_CHECK} <b>Новый лимит успешно установлен!</b>\n\n"
                f"{EMOJI_TARGET} <b>Требование:</b> Чтобы писать в группе, каждый участник должен добавить <b>{limit} друзей</b>.\n"
                f"{EMOJI_SHIELD} Участники, не выполнившие условие, будут ограничены на 10 минут."
            )
        elif lang == "en":
            text = (
                f"{EMOJI_CHECK} <b>New limit successfully set!</b>\n\n"
                f"{EMOJI_TARGET} <b>Requirement:</b> Each member must invite <b>{limit} friends</b> to post in this group.\n"
                f"{EMOJI_SHIELD} Non-compliant members will be muted for 10 minutes."
            )
        elif lang == "uz":
            text = (
                f"{EMOJI_CHECK} <b>Yangi limit muvaffaqiyatli o'rnatildi!</b>\n\n"
                f"{EMOJI_TARGET} <b>Talab:</b> Har bir a'zo guruhda yozish uchun <b>{limit} ta odam</b> qo'shishi kerak.\n"
                f"{EMOJI_SHIELD} Limitni bajarmagan a'zolar 10 daqiqaga cheklanadi."
            )
        else: # qr
            text = (
                f"{EMOJI_CHECK} <b>Жаңа лимит табыслы орнатылды!</b>\n\n"
                f"{EMOJI_TARGET} <b>Талап:</b> Ҳәрбир ағза топарда жазыў ушын <b>{limit} адам</b> қосыўы керек.\n"
                f"{EMOJI_SHIELD} Лимитти орынламаған ағзалар 10 минутқа шекленеди."
            )

    await send_admin_response(message, bot, text, delay=15)


@router.message(Command(commands=["setchannel", "kanal"]))
async def cmd_set_channel(message: Message, bot: Bot):
    """
    Guruh uchun majburiy obuna kanalini o'rnatish:
    /setchannel @kanal_username yoki kanal xabariga reply qilib /setchannel
    """
    group = await db.get_or_create_group(message.chat.id, message.chat.title or "")
    lang = group.get("language") or "qr"

    channel_target = None

    # 1. Kanaldan forward qilingan xabarga reply qilingan bo'lsa:
    if message.reply_to_message:
        if message.reply_to_message.forward_from_chat and message.reply_to_message.forward_from_chat.type == "channel":
            channel_target = message.reply_to_message.forward_from_chat.id
        elif message.reply_to_message.text:
            channel_target = message.reply_to_message.text.strip()

    # 2. Argument orqali kiritilgan bo'lsa:
    if not channel_target:
        args = message.text.split()
        if len(args) >= 2:
            channel_target = args[1].strip()

    if not channel_target:
        if lang == "ru":
            text = (
                f"{EMOJI_WARN} <b>Неверный формат команды!</b>\n\n"
                f"{EMOJI_DOT} <code>/setchannel @имя_канала</code>\n"
                f"{EMOJI_DOT} <code>/setchannel https://t.me/имя_канала</code>\n"
                f"{EMOJI_DOT} Или перешлите сообщение из канала и ответьте на него <code>/setchannel</code>.\n\n"
                f"<i>Примечание: Бот обязательно должен быть <b>Администратором</b> в этом канале!</i>"
            )
        elif lang == "en":
            text = (
                f"{EMOJI_WARN} <b>Invalid command format!</b>\n\n"
                f"{EMOJI_DOT} <code>/setchannel @channel_name</code>\n"
                f"{EMOJI_DOT} <code>/setchannel https://t.me/channel_name</code>\n"
                f"{EMOJI_DOT} Or forward a post from the channel and reply with <code>/setchannel</code>.\n\n"
                f"<i>Note: Bot must be an <b>Administrator</b> in that channel!</i>"
            )
        elif lang == "uz":
            text = (
                f"{EMOJI_WARN} <b>Noto'g'ri buyruq formati!</b>\n\n"
                f"{EMOJI_DOT} <code>/setchannel @kanal_nomi</code>\n"
                f"{EMOJI_DOT} <code>/setchannel https://t.me/kanal_nomi</code>\n"
                f"{EMOJI_DOT} Yoki kanaldan xabarni guruhga forward qilib, unga reply qilib <code>/setchannel</code> yozing.\n\n"
                f"<i>Eslatma: Bot o'sha kanalda <b>Admin</b> bo'lishi shart!</i>"
            )
        else: # qr
            text = (
                f"{EMOJI_WARN} <b>Надурыс буйрық форматы!</b>\n\n"
                f"{EMOJI_DOT} <code>/setchannel @kanal_ati</code>\n"
                f"{EMOJI_DOT} <code>/setchannel https://t.me/kanal_ati</code>\n"
                f"{EMOJI_DOT} Ямаса каналдан хабарды топарға forward етип, оған reply етип <code>/setchannel</code> жазың.\n\n"
                f"<i>Еслетпе: Бот сол каналда <b>Admin</b> болыўы шәрт!</i>"
            )
        await send_admin_response(message, bot, text, delay=12)
        return

    # Havola tozalash: https://t.me/kanal -> @kanal
    if isinstance(channel_target, str):
        channel_target = channel_target.replace("https://t.me/", "").replace("t.me/", "").replace("http://t.me/", "").strip()
        if not channel_target.startswith("@") and not channel_target.startswith("-100") and not channel_target.lstrip("-").isdigit():
            channel_target = f"@{channel_target}"
        elif channel_target.lstrip("-").isdigit():
            channel_target = int(channel_target)

    try:
        chat = await bot.get_chat(channel_target)
        if chat.type != "channel":
            not_channel_msg = {
                "ru": f"{EMOJI_WARN} Указанный адрес не является каналом (это группа или пользователь)!",
                "en": f"{EMOJI_WARN} Provided chat is not a channel (group or user)!",
                "uz": f"{EMOJI_WARN} Ko'rsatilgan manzil kanal emas (guruh yoki foydalanuvchi)!",
                "qr": f"{EMOJI_WARN} Көрсетилген мәнзил канал емес (топар ямаса пайдаланыўшы)!"
            }.get(lang, f"{EMOJI_WARN} Көрсетилген мәнзил канал емес (топар ямаса пайдаланыўшы)!")
            await send_admin_response(message, bot, not_channel_msg, delay=8)
            return

        bot_user = await bot.get_me()
        bot_member = await bot.get_chat_member(chat.id, bot_user.id)
        if bot_member.status not in ["administrator", "creator"]:
            if lang == "ru":
                text = (
                    f"{EMOJI_WARN} <b>Бот не является Администратором в канале '{chat.title}'!</b>\n"
                    f"Пожалуйста, добавьте бота в администраторы канала и повторите попытку."
                )
            elif lang == "en":
                text = (
                    f"{EMOJI_WARN} <b>Bot is not an Administrator in '{chat.title}'!</b>\n"
                    f"Please promote the bot to channel admin and try again."
                )
            elif lang == "uz":
                text = (
                    f"{EMOJI_WARN} <b>Bot '{chat.title}' kanalida Admin emas!</b>\n"
                    f"Iltimos, avval botni kanalingizga admin qiling va qayta urinib ko'ring."
                )
            else: # qr
                text = (
                    f"{EMOJI_WARN} <b>Бот '{chat.title}' каналында Admin емес!</b>\n"
                    f"Илтимас, алдын ботты каналыңызға admin қылың ҳәм қайта урынып көриң."
                )
            await send_admin_response(message, bot, text, delay=12)
            return

        channel_id = str(chat.id)
        channel_username = chat.username or ""
        channel_title = chat.title or ""

        await db.set_group_channel(message.chat.id, channel_id, channel_username, channel_title)
        cache.invalidate_group_settings(message.chat.id)
        cache.clear_allowed_users(message.chat.id)

        if lang == "ru":
            text = (
                f"{EMOJI_CHECK} <b>Обязательный канал успешно установлен!</b>\n\n"
                f"{EMOJI_CHANNEL} <b>Канал:</b> {channel_title} (@{channel_username})\n"
                f"{EMOJI_PIN} Теперь после приглашения друзей участники обязаны подписаться на этот канал."
            )
        elif lang == "en":
            text = (
                f"{EMOJI_CHECK} <b>Mandatory channel successfully connected!</b>\n\n"
                f"{EMOJI_CHANNEL} <b>Channel:</b> {channel_title} (@{channel_username})\n"
                f"{EMOJI_PIN} Members must now subscribe to this channel after inviting friends."
            )
        elif lang == "uz":
            text = (
                f"{EMOJI_CHECK} <b>Majburiy obuna kanali muvaffaqiyatli o'rnatildi!</b>\n\n"
                f"{EMOJI_CHANNEL} <b>Kanal:</b> {channel_title} (@{channel_username})\n"
                f"{EMOJI_PIN} Endi a'zolar odam qo'shgandan so'ng, ushbu kanalga a'zo bo'lishlari shart bo'ladi."
            )
        else: # qr
            text = (
                f"{EMOJI_CHECK} <b>Мәжбүрий жазылыў каналы табыслы орнатылды!</b>\n\n"
                f"{EMOJI_CHANNEL} <b>Канал:</b> {channel_title} (@{channel_username})\n"
                f"{EMOJI_PIN} Енди ағзалар адам қосқаннан соң, усы каналға ағза болыўы шәрт болады."
            )
        await send_admin_response(message, bot, text, delay=15)

    except Exception as e:
        if lang == "ru":
            text = (
                f"{EMOJI_CROSS} <b>Не удалось подключить канал!</b>\n"
                f"Бот не нашел канал или не является в нем администратором.\n"
                f"Ошибка: <code>{html.escape(str(e))}</code>"
            )
        elif lang == "en":
            text = (
                f"{EMOJI_CROSS} <b>Failed to connect channel!</b>\n"
                f"Bot could not find channel or is not admin.\n"
                f"Error: <code>{html.escape(str(e))}</code>"
            )
        elif lang == "uz":
            text = (
                f"{EMOJI_CROSS} <b>Kanalni ulab bo'lmadi!</b>\n"
                f"Bot kanalni topa olmadi yoki kanalda admin emas.\n"
                f"Xatolik: <code>{html.escape(str(e))}</code>"
            )
        else: # qr
            text = (
                f"{EMOJI_CROSS} <b>Каналды жалғап болмады!</b>\n"
                f"Бот каналды таба алмады яки каналда admin емес.\n"
                f"Қәте: <code>{html.escape(str(e))}</code>"
            )
        await send_admin_response(message, bot, text, delay=12)


@router.message(Command(commands=["delchannel", "kanalnibekorqilish"]))
async def cmd_del_channel(message: Message, bot: Bot):
    """Guruhdan majburiy kanalni o'chirish"""
    group = await db.get_or_create_group(message.chat.id, message.chat.title or "")
    lang = group.get("language") or "qr"

    await db.del_group_channel(message.chat.id)
    cache.invalidate_group_settings(message.chat.id)
    cache.clear_allowed_users(message.chat.id)

    del_msg = {
        "ru": f"{EMOJI_CHECK} <b>Обязательная подписка на канал отменена!</b>",
        "en": f"{EMOJI_CHECK} <b>Mandatory channel subscription removed!</b>",
        "uz": f"{EMOJI_CHECK} <b>Majburiy kanal obunasi bekor qilindi!</b>",
        "qr": f"{EMOJI_CHECK} <b>Мәжбүрий каналға жазылыў бийкар етилди!</b>"
    }.get(lang, f"{EMOJI_CHECK} <b>Мәжбүрий каналға жазылыў бийкар етилди!</b>")
    await send_admin_response(message, bot, del_msg, delay=10)


@router.message(Command(commands=["channel", "kanalim"]))
async def cmd_show_channel(message: Message, bot: Bot):
    """Guruhga ulangan kanalni ko'rish"""
    group = await db.get_or_create_group(message.chat.id, message.chat.title or "")
    lang = group.get("language") or "qr"
    ch_id = group.get("channel_id")
    ch_user = group.get("channel_username")
    ch_title = group.get("channel_title")

    if ch_id and (ch_user or ch_title):
        if lang == "ru":
            text = (
                f"{EMOJI_CHANNEL} <b>Обязательный канал группы:</b>\n\n"
                f"{EMOJI_PIN} <b>Название:</b> {ch_title}\n"
                f"🔗 <b>Юзернейм:</b> @{ch_user if ch_user else 'Отсутствует'}\n\n"
                f"<i>Для отключения: <code>/delchannel</code></i>"
            )
        elif lang == "en":
            text = (
                f"{EMOJI_CHANNEL} <b>Connected mandatory channel:</b>\n\n"
                f"{EMOJI_PIN} <b>Title:</b> {ch_title}\n"
                f"🔗 <b>Username:</b> @{ch_user if ch_user else 'None'}\n\n"
                f"<i>To remove: <code>/delchannel</code></i>"
            )
        elif lang == "uz":
            text = (
                f"{EMOJI_CHANNEL} <b>Guruhga ulangan majburiy kanal:</b>\n\n"
                f"{EMOJI_PIN} <b>Nomi:</b> {ch_title}\n"
                f"🔗 <b>Username:</b> @{ch_user if ch_user else 'Mavjud emas'}\n\n"
                f"<i>O'chirish uchun: <code>/delchannel</code></i>"
            )
        else: # qr
            text = (
                f"{EMOJI_CHANNEL} <b>Топарға жалғанған мәжбүрий канал:</b>\n\n"
                f"{EMOJI_PIN} <b>Аты:</b> {ch_title}\n"
                f"🔗 <b>Username:</b> @{ch_user if ch_user else 'Жоқ'}\n\n"
                f"<i>Өшириў ушын: <code>/delchannel</code></i>"
            )
    else:
        if lang == "ru":
            text = f"ℹ️ К группе не подключен обязательный канал.\nПодключить: <code>/setchannel @имя_канала</code>"
        elif lang == "en":
            text = f"ℹ️ No mandatory channel is connected to this group.\nConnect: <code>/setchannel @channel_name</code>"
        elif lang == "uz":
            text = f"ℹ️ Guruhga hech qanday majburiy kanal ulanmagan.\nUlash uchun: <code>/setchannel @kanal_username</code>"
        else: # qr
            text = f"ℹ️ Топарға ҳешқандай мәжбүрий канал жалғанбаған.\nЖалғаў ушын: <code>/setchannel @kanal_username</code>"

    await send_admin_response(message, bot, text, delay=12)


@router.message(Command(commands=["status", "info", "settings", "gstats"]))
async def cmd_status(message: Message, bot: Bot):
    """Guruh sozlamalari va umumiy statistikasi (QR / UZ / RU / EN tillarida)"""
    group = await db.get_or_create_group(message.chat.id, message.chat.title or "")
    lang = group.get("language") or "qr"
    limit = group.get("required_count", 0)
    is_service = bool(group.get("del_service_msg", 1))
    is_anticheat = bool(group.get("anticheat", 0))
    is_captcha = bool(group.get("captcha", 1))
    ch_title = group.get("channel_title")
    ch_user = group.get("channel_username")

    stats = await db.get_group_total_stats(message.chat.id)

    lang_names = {
        "qr": f"{EMOJI_FLAG_QR} Қарақалпақша",
        "uz": f"{EMOJI_FLAG_UZ} O'zbekcha",
        "ru": f"{EMOJI_FLAG_RU} Русский",
        "en": f"{EMOJI_FLAG_EN} English"
    }
    lang_display = lang_names.get(lang, f"{EMOJI_FLAG_QR} Қарақалпақша")

    if lang == "ru":
        service_msg = "Включено" if is_service else "Выключено"
        anticheat = "Включен (При выходе снимается балл)" if is_anticheat else "Выключен"
        captcha_status = "Включена (5 минут на пример)" if is_captcha else "Выключена"
        channel_info = f"{ch_title} (@{ch_user})" if ch_title else "Не подключен"
        text = (
            f"{EMOJI_CHART} <b>Настройки и статистика группы:</b>\n\n"
            f"🏷 <b>Группа:</b> {message.chat.title}\n"
            f"🌐 <b>Язык группы:</b> <b>{lang_display}</b>\n"
            f"{EMOJI_PEOPLE} <b>Обязательное добавление:</b> <b>{limit} участников</b>\n"
            f"{EMOJI_CHANNEL} <b>Обязательный канал:</b> <b>{channel_info}</b>\n"
            f"🧹 <b>Удаление сервисных сообщений:</b> {service_msg}\n"
            f"{EMOJI_SHIELD} <b>Anti-Cheat:</b> {anticheat}\n"
            f"🧩 <b>Математическая капча:</b> {captcha_status}\n\n"
            f"{EMOJI_CHART_UP} <b>Общая статистика:</b>\n"
            f"{EMOJI_DOT} Всего добавлено участников: <b>{stats['total_added']}</b>\n"
            f"{EMOJI_DOT} Вышедших участников: <b>{stats['total_left']}</b>\n"
            f"{EMOJI_DOT} Учтенных пользователей: <b>{stats['total_members']}</b>\n\n"
            f"<i>Лимит: <code>/set 5</code> | Канал: <code>/setchannel @канал</code> | Язык: <code>/lang</code></i>"
        )
    elif lang == "en":
        service_msg = "Enabled" if is_service else "Disabled"
        anticheat = "Enabled (Points deducted on leave)" if is_anticheat else "Disabled"
        captcha_status = "Enabled (5 min math challenge)" if is_captcha else "Disabled"
        channel_info = f"{ch_title} (@{ch_user})" if ch_title else "Not connected"
        text = (
            f"{EMOJI_CHART} <b>Group Settings & Statistics:</b>\n\n"
            f"🏷 <b>Group:</b> {message.chat.title}\n"
            f"🌐 <b>Group language:</b> <b>{lang_display}</b>\n"
            f"{EMOJI_PEOPLE} <b>Required member invites:</b> <b>{limit} members</b>\n"
            f"{EMOJI_CHANNEL} <b>Mandatory channel:</b> <b>{channel_info}</b>\n"
            f"🧹 <b>Clean service messages:</b> {service_msg}\n"
            f"{EMOJI_SHIELD} <b>Anti-Cheat:</b> {anticheat}\n"
            f"🧩 <b>Math Captcha:</b> {captcha_status}\n\n"
            f"{EMOJI_CHART_UP} <b>Overall Statistics:</b>\n"
            f"{EMOJI_DOT} Total members added: <b>{stats['total_added']}</b>\n"
            f"{EMOJI_DOT} Members left: <b>{stats['total_left']}</b>\n"
            f"{EMOJI_DOT} Registered users: <b>{stats['total_members']}</b>\n\n"
            f"<i>Limit: <code>/set 5</code> | Channel: <code>/setchannel @channel</code> | Language: <code>/lang</code></i>"
        )
    elif lang == "uz":
        service_msg = "Yoqilgan" if is_service else "O'chirilgan"
        anticheat = "Yoqilgan (Chiqsa ball kamayadi)" if is_anticheat else "O'chirilgan"
        captcha_status = "Yoqilgan (5 daqiqali misol)" if is_captcha else "O'chirilgan"
        channel_info = f"{ch_title} (@{ch_user})" if ch_title else "Ulanmagan"
        text = (
            f"{EMOJI_CHART} <b>Guruh sozlamalari va statistikasi:</b>\n\n"
            f"🏷 <b>Guruh:</b> {message.chat.title}\n"
            f"🌐 <b>Guruh tili:</b> <b>{lang_display}</b>\n"
            f"{EMOJI_PEOPLE} <b>Majburiy a'zo limiti:</b> <b>{limit} ta odam</b>\n"
            f"{EMOJI_CHANNEL} <b>Majburiy kanal:</b> <b>{channel_info}</b>\n"
            f"🧹 <b>Xizmat xabarlarini tozalash:</b> {service_msg}\n"
            f"{EMOJI_SHIELD} <b>Anti-Cheat:</b> {anticheat}\n"
            f"🧩 <b>Matematik Captcha:</b> {captcha_status}\n\n"
            f"{EMOJI_CHART_UP} <b>Umumiy statistika:</b>\n"
            f"{EMOJI_DOT} Jami qo'shilgan a'zolar: <b>{stats['total_added']}</b> ta\n"
            f"{EMOJI_DOT} Chiqib ketganlar: <b>{stats['total_left']}</b> ta\n"
            f"{EMOJI_DOT} Hisoblangan foydalanuvchilar: <b>{stats['total_members']}</b> ta\n\n"
            f"<i>Limit: <code>/set 5</code> | Kanal: <code>/setchannel @kanal</code> | Til: <code>/lang</code></i>"
        )
    else: # qr
        service_msg = "Қосылған" if is_service else "Өширилген"
        anticheat = "Қосылған (Шықса балл алынады)" if is_anticheat else "Өширилген"
        captcha_status = "Қосылған (5 минутлы мысал)" if is_captcha else "Өширилген"
        channel_info = f"{ch_title} (@{ch_user})" if ch_title else "Жалғанбаған"
        text = (
            f"{EMOJI_CHART} <b>Топар параметрлери ҳәм статистикасы:</b>\n\n"
            f"🏷 <b>Топар:</b> {message.chat.title}\n"
            f"🌐 <b>Топар тили:</b> <b>{lang_display}</b>\n"
            f"{EMOJI_PEOPLE} <b>Мәжбүрий адам лимити:</b> <b>{limit} адам</b>\n"
            f"{EMOJI_CHANNEL} <b>Мәжбүрий канал:</b> <b>{channel_info}</b>\n"
            f"🧹 <b>Хызмет хабарларын тазалаў:</b> {service_msg}\n"
            f"{EMOJI_SHIELD} <b>Anti-Cheat:</b> {anticheat}\n"
            f"🧩 <b>Математикалық Captcha:</b> {captcha_status}\n\n"
            f"{EMOJI_CHART_UP} <b>Улыўма статистика:</b>\n"
            f"{EMOJI_DOT} Жәми қосылған ағзалар: <b>{stats['total_added']}</b>\n"
            f"{EMOJI_DOT} Шығып кеткенлер: <b>{stats['total_left']}</b>\n"
            f"{EMOJI_DOT} Есапланған пайдаланыўшылар: <b>{stats['total_members']}</b>\n\n"
            f"<i>Лимит: <code>/set 5</code> | Канал: <code>/setchannel @kanal</code> | Тил: <code>/lang</code></i>"
        )
    await send_admin_response(message, bot, text, delay=25)


@router.message(Command(commands=["anticheat", "antifraud"]))
async def cmd_toggle_anticheat(message: Message, bot: Bot):
    """Guruhdan chiqib ketganlar hisobdan ayirilsinmi: /anticheat on/off"""
    group = await db.get_or_create_group(message.chat.id, message.chat.title or "")
    lang = group.get("language") or "qr"

    args = message.text.split()
    if len(args) < 2 or args[1].lower() not in ["on", "off"]:
        if lang == "ru":
            text = (
                f"{EMOJI_WARN} <b>Неверный формат!</b>\n\n"
                f"{EMOJI_DOT} <code>/anticheat on</code> — Если приглашенный выходит, у пригласившего снимается 1 балл.\n"
                f"{EMOJI_DOT} <code>/anticheat off</code> — Вышедшие участники не вычитаются."
            )
        elif lang == "en":
            text = (
                f"{EMOJI_WARN} <b>Invalid format!</b>\n\n"
                f"{EMOJI_DOT} <code>/anticheat on</code> — Deduct 1 point when invited member leaves.\n"
                f"{EMOJI_DOT} <code>/anticheat off</code> — Do not deduct points."
            )
        elif lang == "uz":
            text = (
                f"{EMOJI_WARN} <b>Noto'g'ri format!</b>\n\n"
                f"{EMOJI_DOT} <code>/anticheat on</code> — Agar qo'shilgan odam guruhdan chiqib ketsa, uni taklif qilgandan 1 ball ayiriladi.\n"
                f"{EMOJI_DOT} <code>/anticheat off</code> — Chiqib ketganlar hisobdan ayirilmaydi."
            )
        else: # qr
            text = (
                f"{EMOJI_WARN} <b>Надурыс формат!</b>\n\n"
                f"{EMOJI_DOT} <code>/anticheat on</code> — Егер қосылған адам топардан шығып кетсе, оны мирәт еткеннен 1 балл алынады.\n"
                f"{EMOJI_DOT} <code>/anticheat off</code> — Шығып кеткенлер есаптан алынбайды."
            )
        await send_admin_response(message, bot, text, delay=10)
        return

    turn_on = args[1].lower() == "on"
    await db.toggle_anticheat(message.chat.id, turn_on)
    cache.invalidate_group_settings(message.chat.id)

    if lang == "ru":
        status_str = "<b>Включен</b> (при выходе участника снимается балл)" if turn_on else "<b>Выключен</b>"
        text = f"{EMOJI_SHIELD} <b>Anti-Cheat:</b> {status_str}"
    elif lang == "en":
        status_str = "<b>Enabled</b> (points deducted when member leaves)" if turn_on else "<b>Disabled</b>"
        text = f"{EMOJI_SHIELD} <b>Anti-Cheat:</b> {status_str}"
    elif lang == "uz":
        status_str = "<b>Yoqildi</b> (a'zo chiqsa ball ayiriladi)" if turn_on else "<b>Ochirildi</b>"
        text = f"{EMOJI_SHIELD} <b>Anti-Cheat:</b> {status_str}"
    else: # qr
        status_str = "<b>Қосылды</b> (ағза шықса балл алынады)" if turn_on else "<b>Өширилди</b>"
        text = f"{EMOJI_SHIELD} <b>Anti-Cheat:</b> {status_str}"
    await send_admin_response(message, bot, text, delay=10)


@router.message(Command(commands=["check", "tekshir", "userinfo"]))
async def cmd_check_user(message: Message, bot: Bot):
    """Admin tomonidan ma'lum a'zo kimlarni qo'shganini tekshirish"""
    group = await db.get_or_create_group(message.chat.id, message.chat.title or "")
    lang = group.get("language") or "qr"

    target_user_id = None
    target_name = ""

    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
        target_user_id = target_user.id
        target_name = target_user.full_name
    else:
        args = message.text.split()
        if len(args) >= 2 and args[1].isdigit():
            target_user_id = int(args[1])
            target_name = f"ID: {target_user_id}"

    if not target_user_id:
        err_msg = {
            "ru": f"{EMOJI_WARN} Ответьте на сообщение пользователя <code>/check</code> или укажите ID: <code>/check 12345678</code>",
            "en": f"{EMOJI_WARN} Reply to user's message with <code>/check</code> or provide ID: <code>/check 12345678</code>",
            "uz": f"{EMOJI_WARN} Foydalanuvchi xabariga reply qilib <code>/check</code> yozing yoki ID kiriting: <code>/check 12345678</code>",
            "qr": f"{EMOJI_WARN} Пайдаланыўшы хабарына reply етип <code>/check</code> жазың ямаса ID киргизиң: <code>/check 12345678</code>"
        }.get(lang, f"{EMOJI_WARN} Пайдаланыўшы хабарына reply етип <code>/check</code> жазың ямаса ID киргизиң: <code>/check 12345678</code>")
        await send_admin_response(message, bot, err_msg, delay=8)
        return

    member = await db.get_member_stats(message.chat.id, target_user_id)
    added = member.get("added_count", 0) if member else 0
    is_exempt = member.get("is_exempt", 0) if member else 0

    referrals = await db.get_user_referrals(message.chat.id, target_user_id, limit=20)

    if lang == "ru":
        text = (
            f"{EMOJI_SEARCH} <b>Проверка пользователя:</b>\n"
            f"👤 <b>Имя:</b> {target_name}\n"
            f"🆔 <b>ID:</b> <code>{target_user_id}</code>\n"
            f"{EMOJI_CHART} <b>Приглашено участников:</b> <b>{added}</b>\n"
            f"{EMOJI_SHIELD} <b>Белый список:</b> {'Да' if is_exempt else 'Нет'}\n\n"
        )
        if referrals:
            text += f"{EMOJI_PEOPLE} <b>Последние {len(referrals)} приглашенных участников:</b>\n"
            for idx, ref in enumerate(referrals, 1):
                name = ref.get("joined_user_name") or f"ID: {ref['joined_user_id']}"
                status = f" ({EMOJI_BAN} Вышел)" if ref.get("is_left") else f" ({EMOJI_CHECK} В группе)"
                date = ref.get("joined_at", "")[:10]
                text += f"{idx}. {name}{status} — <i>{date}</i>\n"
        else:
            text += "<i>Этот пользователь еще никого не пригласил.</i>"
    elif lang == "en":
        text = (
            f"{EMOJI_SEARCH} <b>User inspection:</b>\n"
            f"👤 <b>Name:</b> {target_name}\n"
            f"🆔 <b>ID:</b> <code>{target_user_id}</code>\n"
            f"{EMOJI_CHART} <b>Members invited:</b> <b>{added}</b>\n"
            f"{EMOJI_SHIELD} <b>Whitelisted:</b> {'Yes' if is_exempt else 'No'}\n\n"
        )
        if referrals:
            text += f"{EMOJI_PEOPLE} <b>Last {len(referrals)} invited members:</b>\n"
            for idx, ref in enumerate(referrals, 1):
                name = ref.get("joined_user_name") or f"ID: {ref['joined_user_id']}"
                status = f" ({EMOJI_BAN} Left)" if ref.get("is_left") else f" ({EMOJI_CHECK} In group)"
                date = ref.get("joined_at", "")[:10]
                text += f"{idx}. {name}{status} — <i>{date}</i>\n"
        else:
            text += "<i>This user hasn't invited anyone yet.</i>"
    elif lang == "uz":
        text = (
            f"{EMOJI_SEARCH} <b>Foydalanuvchi tekshiruvi:</b>\n"
            f"👤 <b>Ismi:</b> {target_name}\n"
            f"🆔 <b>ID:</b> <code>{target_user_id}</code>\n"
            f"{EMOJI_CHART} <b>Qo'shgan odamlari soni:</b> <b>{added}</b> ta\n"
            f"{EMOJI_SHIELD} <b>Oq ro'yxat:</b> {'Ha' if is_exempt else 'Yoq'}\n\n"
        )
        if referrals:
            text += f"{EMOJI_PEOPLE} <b>U qo'shgan oxirgi {len(referrals)} ta a'zo:</b>\n"
            for idx, ref in enumerate(referrals, 1):
                name = ref.get("joined_user_name") or f"ID: {ref['joined_user_id']}"
                status = f" ({EMOJI_BAN} Chiqib ketgan)" if ref.get("is_left") else f" ({EMOJI_CHECK} Guruhda)"
                date = ref.get("joined_at", "")[:10]
                text += f"{idx}. {name}{status} — <i>{date}</i>\n"
        else:
            text += "<i>Ushbu foydalanuvchi hali guruhga odam qo'shmagan.</i>"
    else: # qr
        text = (
            f"{EMOJI_SEARCH} <b>Пайдаланыўшы тексериўи:</b>\n"
            f"👤 <b>Аты:</b> {target_name}\n"
            f"🆔 <b>ID:</b> <code>{target_user_id}</code>\n"
            f"{EMOJI_CHART} <b>Қосқан адамлары саны:</b> <b>{added}</b>\n"
            f"{EMOJI_SHIELD} <b>Ақ дизим:</b> {'Аўа' if is_exempt else 'Яқ'}\n\n"
        )
        if referrals:
            text += f"{EMOJI_PEOPLE} <b>Ол қосқан ақырғы {len(referrals)} ағза:</b>\n"
            for idx, ref in enumerate(referrals, 1):
                name = ref.get("joined_user_name") or f"ID: {ref['joined_user_id']}"
                status = f" ({EMOJI_BAN} Шығып кеткен)" if ref.get("is_left") else f" ({EMOJI_CHECK} Топарда)"
                date = ref.get("joined_at", "")[:10]
                text += f"{idx}. {name}{status} — <i>{date}</i>\n"
        else:
            text += "<i>Бул пайдаланыўшы еле топарға адам қосқан жоқ.</i>"

    await send_admin_response(message, bot, text, delay=25)


@router.message(Command(commands=["top", "top10"]))
async def cmd_top(message: Message, bot: Bot):
    """Guruhda eng ko'p odam qo'shgan a'zolar ro'yxati"""
    group = await db.get_or_create_group(message.chat.id, message.chat.title or "")
    lang = group.get("language") or "qr"

    top_members = await db.get_top_members(message.chat.id, limit=10)
    if not top_members:
        no_mem_text = {
            "ru": f"{EMOJI_CHART_DOWN} В группе еще никто не пригласил участников.",
            "en": f"{EMOJI_CHART_DOWN} No members have invited anyone yet.",
            "uz": f"{EMOJI_CHART_DOWN} Guruhda hali hech kim odam qo'shmagan.",
            "qr": f"{EMOJI_CHART_DOWN} Топарда еле ҳеш ким адам қоспаған."
        }.get(lang, f"{EMOJI_CHART_DOWN} Топарда еле ҳеш ким адам қоспаған.")
        await send_admin_response(message, bot, no_mem_text, delay=10)
        return

    titles = {
        "ru": f"{EMOJI_START_TROPHY} <b>ТОП-10 участников по приглашениям:</b>\n\n",
        "en": f"{EMOJI_START_TROPHY} <b>TOP-10 member inviters:</b>\n\n",
        "uz": f"{EMOJI_START_TROPHY} <b>Guruhda eng ko'p odam qo'shgan a'zolar (TOP-10):</b>\n\n",
        "qr": f"{EMOJI_START_TROPHY} <b>Топарда ең көп адам қосқан ағзалар (ТОП-10):</b>\n\n"
    }
    text = titles.get(lang, titles["qr"])
    medals = [EMOJI_MEDAL_1, EMOJI_MEDAL_2, EMOJI_MEDAL_3, "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    unit = {"ru": "чел.", "en": "users", "uz": "ta", "qr": ""}.get(lang, "")

    for idx, mem in enumerate(top_members):
        medal = medals[idx] if idx < len(medals) else f"{idx+1}."
        name = mem.get("full_name") or "Noma'lum"
        count = mem.get("added_count", 0)
        username = f" (@{mem['username']})" if mem.get("username") else ""
        text += f"{medal} <b>{name}</b>{username} — <b>{count}</b> {unit}\n"

    await send_admin_response(message, bot, text, delay=20)


@router.message(Command(commands=["whitelist", "imtiyoz", "ruxsat", "unrestrict"]))
async def cmd_whitelist(message: Message, bot: Bot):
    """Foydalanuvchini oq ro'yxatga kiritish (imtiyoz berish va cheklovni yechish)"""
    group = await db.get_or_create_group(message.chat.id, message.chat.title or "")
    lang = group.get("language") or "qr"

    target_user_id = None
    target_name = ""

    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
        target_user_id = target_user.id
        target_name = target_user.full_name
    else:
        args = message.text.split()
        if len(args) >= 2 and args[1].isdigit():
            target_user_id = int(args[1])
            target_name = f"ID: {target_user_id}"

    if not target_user_id:
        err_msg = {
            "ru": f"{EMOJI_WARN} Ответьте на сообщение пользователя <code>/imtiyoz</code> или введите ID: <code>/imtiyoz 12345678</code>",
            "en": f"{EMOJI_WARN} Reply to user message with <code>/imtiyoz</code> or enter ID: <code>/imtiyoz 12345678</code>",
            "uz": f"{EMOJI_WARN} Foydalanuvchining xabariga reply qilib <code>/imtiyoz</code> deb yozing yoki uning ID sini kiriting: <code>/imtiyoz 12345678</code>",
            "qr": f"{EMOJI_WARN} Пайдаланыўшы хабарына reply етип <code>/imtiyoz</code> деп жазың ямаса оның ID син киргизиң: <code>/imtiyoz 12345678</code>"
        }.get(lang, f"{EMOJI_WARN} Пайдаланыўшы хабарына reply етип <code>/imtiyoz</code> деп жазың ямаса оның ID син киргизиң: <code>/imtiyoz 12345678</code>")
        await send_admin_response(message, bot, err_msg, delay=8)
        return

    # Bazaga va keshga saqlaymiz
    await db.set_exempt(message.chat.id, target_user_id, True, target_name)
    cache.add_allowed_user(message.chat.id, target_user_id)
    cache.remove_muted(message.chat.id, target_user_id)

    # Agar mute qilingan bo'lsa, muteni Telegram darajasida yechamiz
    try:
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target_user_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
    except Exception:
        pass

    mention = get_user_mention(target_user_id, target_name)
    if lang == "ru":
        text = f"{EMOJI_STAR} {mention} <b>получил иммунитет!</b>\nВсе ограничения сняты, теперь он может писать без добавления людей."
    elif lang == "en":
        text = f"{EMOJI_STAR} {mention} <b>granted immunity!</b>\nAll restrictions removed, posting access unlocked."
    elif lang == "uz":
        text = f"{EMOJI_STAR} {mention} ga <b>imtiyoz berildi!</b>\nBarcha cheklovlar yechildi, endi u odam qo'shmasdan bemalol yoza oladi."
    else:
        text = f"{EMOJI_STAR} {mention} ға <b>жеңиллик берилди!</b>\nБарлық шеклеўлер алып тасланды, енди ол адам қоспастан арқайын жаза алады."
    await send_admin_response(message, bot, text, delay=12)


@router.message(Command(commands=["unwhitelist", "taqiq", "restrict"]))
async def cmd_unwhitelist(message: Message, bot: Bot):
    """Foydalanuvchini oq ro'yxatdan chiqarish (imtiyozni bekor qilish)"""
    group = await db.get_or_create_group(message.chat.id, message.chat.title or "")
    lang = group.get("language") or "qr"

    target_user_id = None
    target_name = ""

    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
        target_user_id = target_user.id
        target_name = target_user.full_name
    else:
        args = message.text.split()
        if len(args) >= 2 and args[1].isdigit():
            target_user_id = int(args[1])
            target_name = f"ID: {target_user_id}"

    if not target_user_id:
        err_msg = {
            "ru": f"{EMOJI_WARN} Ответьте на сообщение пользователя или укажите ID: <code>/unwhitelist 12345678</code>",
            "en": f"{EMOJI_WARN} Reply to user message or provide ID: <code>/unwhitelist 12345678</code>",
            "uz": f"{EMOJI_WARN} Foydalanuvchining xabariga reply qiling yoki ID sini kiriting: <code>/unwhitelist 12345678</code>",
            "qr": f"{EMOJI_WARN} Пайдаланыўшы хабарына reply етиң ямаса ID син киргизиң: <code>/unwhitelist 12345678</code>"
        }.get(lang, f"{EMOJI_WARN} Пайдаланыўшы хабарына reply етиң ямаса ID син киргизиң: <code>/unwhitelist 12345678</code>")
        await send_admin_response(message, bot, err_msg, delay=8)
        return

    await db.set_exempt(message.chat.id, target_user_id, False, target_name)
    cache.remove_allowed_user(message.chat.id, target_user_id)

    mention = get_user_mention(target_user_id, target_name)
    if lang == "ru":
        text = f"{EMOJI_BAN} У {mention} отозван иммунитет. Теперь действуют общие правила группы."
    elif lang == "en":
        text = f"{EMOJI_BAN} Immunity revoked for {mention}. General group requirements apply."
    elif lang == "uz":
        text = f"{EMOJI_BAN} {mention} dan imtiyoz olib tashlandi. Unga yana umumiy guruh cheklovi amal qiladi."
    else:
        text = f"{EMOJI_BAN} {mention} дан жеңиллик алып тасланды. Оған және улыўма топар шеклеўи әмел етеди."
    await send_admin_response(message, bot, text, delay=10)


@router.message(Command(commands=["reset"]))
async def cmd_reset_member(message: Message, bot: Bot):
    """A'zoning hisoblagichini 0 ga tushirish"""
    group = await db.get_or_create_group(message.chat.id, message.chat.title or "")
    lang = group.get("language") or "qr"

    target_user_id = None
    target_name = ""
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user_id = message.reply_to_message.from_user.id
        target_name = message.reply_to_message.from_user.full_name
    else:
        args = message.text.split()
        if len(args) >= 2 and args[1].isdigit():
            target_user_id = int(args[1])
            target_name = f"ID: {target_user_id}"

    if not target_user_id:
        err_msg = {
            "ru": f"{EMOJI_WARN} Ответьте на сообщение пользователя <code>/reset</code> или укажите ID: <code>/reset 12345678</code>",
            "en": f"{EMOJI_WARN} Reply to user message with <code>/reset</code> or enter ID: <code>/reset 12345678</code>",
            "uz": f"{EMOJI_WARN} Foydalanuvchi xabariga reply qilib <code>/reset</code> yozing yoki ID kiriting: <code>/reset 12345678</code>",
            "qr": f"{EMOJI_WARN} Пайдаланыўшы хабарына reply етип <code>/reset</code> жазың ямаса ID киргизиң: <code>/reset 12345678</code>"
        }.get(lang, f"{EMOJI_WARN} Пайдаланыўшы хабарына reply етип <code>/reset</code> жазың ямаса ID киргизиң: <code>/reset 12345678</code>")
        await send_admin_response(message, bot, err_msg, delay=8)
        return

    await db.reset_member(message.chat.id, target_user_id)
    cache.remove_allowed_user(message.chat.id, target_user_id)

    if lang == "ru":
        text = f"{EMOJI_RESET} Счет приглашений пользователя {target_name} сброшен."
    elif lang == "en":
        text = f"{EMOJI_RESET} Invite counter reset for {target_name}."
    elif lang == "uz":
        text = f"{EMOJI_RESET} {target_name} ning qo'shgan odamlari hisobi nollashtirildi."
    else:
        text = f"{EMOJI_RESET} {target_name} диң қосқан адамлар есабы нольленди."
    await send_admin_response(message, bot, text, delay=10)


@router.message(Command(commands=["reset_all"]))
async def cmd_reset_all(message: Message, bot: Bot):
    """Butun guruh statistikasini nollash"""
    group = await db.get_or_create_group(message.chat.id, message.chat.title or "")
    lang = group.get("language") or "qr"

    await db.reset_group(message.chat.id)
    cache.clear_allowed_users(message.chat.id)

    if lang == "ru":
        text = f"{EMOJI_RESET} <b>Счетчики приглашений всех участников успешно сброшены!</b>"
    elif lang == "en":
        text = f"{EMOJI_RESET} <b>Invite counters for all group members reset!</b>"
    elif lang == "uz":
        text = f"{EMOJI_RESET} <b>Barcha a'zolarning odam qo'shish hisoblagichlari nollashtirildi!</b>"
    else:
        text = f"{EMOJI_RESET} <b>Барлық ағзалардың адам қосыў есаплағышлары нольлестирилди!</b>"
    await send_admin_response(message, bot, text, delay=12)


@router.message(Command(commands=["service_msg"]))
async def cmd_toggle_service(message: Message, bot: Bot):
    """Xizmat xabarlarini (kirdi/chiqdi) tozalashni boshqarish: /service_msg on / off"""
    group = await db.get_or_create_group(message.chat.id, message.chat.title or "")
    lang = group.get("language") or "qr"

    args = message.text.split()
    if len(args) < 2 or args[1].lower() not in ["on", "off"]:
        format_err = {
            "ru": f"{EMOJI_WARN} Формат: <code>/service_msg on</code> или <code>/service_msg off</code>",
            "en": f"{EMOJI_WARN} Format: <code>/service_msg on</code> or <code>/service_msg off</code>",
            "uz": f"{EMOJI_WARN} To'g'ri format: <code>/service_msg on</code> yoki <code>/service_msg off</code>",
            "qr": f"{EMOJI_WARN} Дурыс формат: <code>/service_msg on</code> ямаса <code>/service_msg off</code>"
        }.get(lang, f"{EMOJI_WARN} Дурыс формат: <code>/service_msg on</code> ямаса <code>/service_msg off</code>")
        await send_admin_response(message, bot, format_err, delay=8)
        return

    turn_on = args[1].lower() == "on"
    await db.toggle_del_service_msg(message.chat.id, turn_on)
    cache.invalidate_group_settings(message.chat.id)

    if lang == "ru":
        status_str = "Включено" if turn_on else "Выключено"
        text = f"{EMOJI_CHECK} Автоудаление сервисных сообщений: <b>{status_str}</b>"
    elif lang == "en":
        status_str = "Enabled" if turn_on else "Disabled"
        text = f"{EMOJI_CHECK} Auto-clean service messages: <b>{status_str}</b>"
    elif lang == "uz":
        status_str = "Yoqildi" if turn_on else "Ochirildi"
        text = f"{EMOJI_CHECK} Xizmat xabarlarini avtomatik o'chirish: <b>{status_str}</b>"
    else:
        status_str = "Әмелге асырылды" if turn_on else "Өширилди"
        text = f"{EMOJI_CHECK} Хызмет хабарларын автоматик өшириў: <b>{status_str}</b>"
    await send_admin_response(message, bot, text, delay=8)


@router.message(Command(commands=["captcha"]))
async def cmd_toggle_captcha(message: Message, bot: Bot):
    """Yangi a'zolar uchun matematik captchani yoqish/o'chirish: /captcha on yoki /captcha off"""
    group = await db.get_or_create_group(message.chat.id, message.chat.title or "")
    lang = group.get("language") or "qr"

    args = message.text.split()
    if len(args) < 2 or args[1].lower() not in ["on", "off"]:
        if lang == "ru":
            text = (
                f"{EMOJI_WARN} <b>Неверный формат!</b>\n\n"
                f"{EMOJI_DOT} <code>/captcha on</code> — Новые участники должны решить пример (защита от спам-ботов).\n"
                f"{EMOJI_DOT} <code>/captcha off</code> — Отключить капчу."
            )
        elif lang == "en":
            text = (
                f"{EMOJI_WARN} <b>Invalid format!</b>\n\n"
                f"{EMOJI_DOT} <code>/captcha on</code> — New members must solve math problem (anti-bot protection).\n"
                f"{EMOJI_DOT} <code>/captcha off</code> — Disable captcha."
            )
        elif lang == "uz":
            text = (
                f"{EMOJI_WARN} <b>Noto'g'ri format!</b>\n\n"
                f"{EMOJI_DOT} <code>/captcha on</code> — Yangi qo'shilgan a'zolarga matematik misol chiqaradi (robotlardan himoya).\n"
                f"{EMOJI_DOT} <code>/captcha off</code> — Captchani o'chirib qo'yadi."
            )
        else:
            text = (
                f"{EMOJI_WARN} <b>Надурыс формат!</b>\n\n"
                f"{EMOJI_DOT} <code>/captcha on</code> — Жаңа қосылған ағзаларға математикалық мысал шығарады (роботлардан қорғаў).\n"
                f"{EMOJI_DOT} <code>/captcha off</code> — Captchani өширип қояды."
            )
        await send_admin_response(message, bot, text, delay=10)
        return

    turn_on = args[1].lower() == "on"
    await db.toggle_captcha(message.chat.id, turn_on)
    cache.invalidate_group_settings(message.chat.id)

    if lang == "ru":
        status_str = "<b>Включена</b> (новым участникам дается 5 минут на пример)" if turn_on else "<b>Выключена</b>"
        text = f"{EMOJI_SHIELD} <b>Математическая капча:</b> {status_str}"
    elif lang == "en":
        status_str = "<b>Enabled</b> (new members have 5 minutes to solve)" if turn_on else "<b>Disabled</b>"
        text = f"{EMOJI_SHIELD} <b>Math Captcha:</b> {status_str}"
    elif lang == "uz":
        status_str = "<b>Yoqildi</b> (Yangi a'zolar 5 daqiqada misol yechishi shart)" if turn_on else "<b>Ochirildi</b>"
        text = f"{EMOJI_SHIELD} <b>Matematik Captcha:</b> {status_str}"
    else:
        status_str = "<b>Жағылды</b> (Жаңа ағзалар 5 минутта мәселе шешиўи керек)" if turn_on else "<b>Өширилди</b>"
        text = f"{EMOJI_SHIELD} <b>Математикалық Captcha:</b> {status_str}"
    await send_admin_response(message, bot, text, delay=10)


@router.message(Command(commands=["lang", "language", "til"]))
async def cmd_group_lang(message: Message, bot: Bot):
    """Guruh tilini sozlash buyrug'i (Adminlar uchun)"""
    chat_id = message.chat.id
    group = await db.get_or_create_group(chat_id, message.chat.title or "")
    current_lang = group.get("language") or "qr"

    lang_names = {
        "qr": f"{EMOJI_FLAG_QR} Қарақалпақша",
        "uz": f"{EMOJI_FLAG_UZ} O'zbekcha",
        "ru": f"{EMOJI_FLAG_RU} Русский",
        "en": f"{EMOJI_FLAG_EN} English"
    }
    lang_display = lang_names.get(current_lang, f"{EMOJI_FLAG_QR} Қарақалпақша")

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Қарақалпақша", callback_data=f"set_glang:{chat_id}:qr", icon_custom_emoji_id=CUSTOM_ID_FLAG_QR),
                InlineKeyboardButton(text="O'zbekcha", callback_data=f"set_glang:{chat_id}:uz", icon_custom_emoji_id=CUSTOM_ID_FLAG_UZ),
            ],
            [
                InlineKeyboardButton(text="Русский", callback_data=f"set_glang:{chat_id}:ru", icon_custom_emoji_id=CUSTOM_ID_FLAG_RU),
                InlineKeyboardButton(text="English", callback_data=f"set_glang:{chat_id}:en", icon_custom_emoji_id=CUSTOM_ID_FLAG_EN)
            ]
        ]
    )
    current_label = {
        "qr": "Ҳәзирги топар тили",
        "uz": "Hozirgi guruh tili",
        "ru": "Текущий язык группы",
        "en": "Current group language"
    }.get(current_lang, "Ҳәзирги топар тили")

    text = f"{tr('group_lang_title', current_lang)}\n\n🌐 <b>{current_label}:</b> {lang_display}"
    await send_admin_response(message, bot, text, delay=30, reply_markup=keyboard)


@router.callback_query(F.data.startswith("set_glang:"))
async def callback_group_lang(callback: CallbackQuery, bot: Bot):
    """Guruh tili tanlanganda ishlaydigan callback"""
    parts = callback.data.split(":")
    chat_id = int(parts[1])
    lang = parts[2]

    # Faqat guruh admini yoki bot admini bosa oladi
    admins = cache.get_admins(chat_id)
    if not admins:
        try:
            admin_members = await bot.get_chat_administrators(chat_id)
            admins = {m.user.id for m in admin_members}
            cache.set_admins(chat_id, admins)
        except Exception:
            admins = set()

    if callback.from_user.id not in admins and callback.from_user.id not in config.ADMINS:
        await callback.answer(clean_alert_text(tr("admin_only_btn", lang)), show_alert=True)
        return

    chat_title = callback.message.chat.title if callback.message and callback.message.chat else ""
    await db.set_group_language(chat_id, lang, chat_title)
    cache.invalidate_group_settings(chat_id)

    msg_text = tr("group_lang_success", lang)
    await callback.answer(clean_alert_text(msg_text), show_alert=True)

    # 1. Eski til tanlash menyusini o'chiramiz
    try:
        if callback.message:
            await callback.message.delete()
    except Exception:
        pass

    # 2. Yangi tasdiqlovchi xabar yuboramiz (faqat adminga ko'rinadi)
    lang_names = {
        "qr": f"{EMOJI_FLAG_QR} Қарақалпақша",
        "uz": f"{EMOJI_FLAG_UZ} O'zbekcha",
        "ru": f"{EMOJI_FLAG_RU} Русский",
        "en": f"{EMOJI_FLAG_EN} English"
    }
    lang_display = lang_names.get(lang, f"{EMOJI_FLAG_QR} Қарақалпақша")

    confirm_headers = {
        "qr": "Актив топар тили",
        "uz": "Faol guruh tili",
        "ru": "Активный язык группы",
        "en": "Active group language"
    }
    header_text = confirm_headers.get(lang, "Актив топар тили")

    confirm_text = (
        f"{EMOJI_CHECK} <b>{msg_text}</b>\n\n"
        f"🌐 <b>{header_text}:</b> {lang_display}\n\n"
        f"<i>/status | /help</i>"
    )

    try:
        confirm_msg = await bot.send_message(
            chat_id=chat_id,
            text=confirm_text,
            parse_mode="HTML",
            receiver_user_id=callback.from_user.id
        )
        asyncio.create_task(delete_message_delayed(bot, chat_id, confirm_msg.message_id, 15))
    except Exception:
        try:
            if callback.message:
                confirm_msg = await callback.message.answer(confirm_text, parse_mode="HTML")
                asyncio.create_task(delete_message_delayed(bot, chat_id, confirm_msg.message_id, 15))
        except Exception:
            pass


@router.message(Command(commands=["help"]))
async def cmd_admin_help(message: Message, bot: Bot):
    """Guruhda admin uchun /help yoki /help@bot buyrug'i"""
    group = await db.get_or_create_group(message.chat.id, message.chat.title or "")
    lang = group.get("language") or "qr"
    text = tr("help_group_admin", lang)
    await send_admin_response(message, bot, text, delay=35)


