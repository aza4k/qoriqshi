from aiogram import Router, Bot, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.db import db
from filters.chat_type import ChatTypeFilter
from utils.cache import cache
from utils.i18n import tr, get_user_lang, clean_alert_text
from config import config
from utils.emojis import (
    EMOJI_PIN, EMOJI_POINT_DOWN, EMOJI_CHART, EMOJI_CHECK,
    EMOJI_STAR, EMOJI_GREEN_CIRCLE, EMOJI_HOURGLASS, EMOJI_PEOPLE,
    EMOJI_WAVE, EMOJI_BOT, EMOJI_CROWN, EMOJI_DOT, EMOJI_BOOK,
    CUSTOM_ID_PEOPLE, CUSTOM_ID_CHART, CUSTOM_ID_LANG, CUSTOM_ID_BOOK,
    CUSTOM_ID_FLAG_UZ, CUSTOM_ID_FLAG_QR, CUSTOM_ID_FLAG_RU, CUSTOM_ID_FLAG_EN
)

router = Router()
router.message.filter(ChatTypeFilter("private"))
router.callback_query.filter(ChatTypeFilter("private"))

def get_start_keyboard(bot_username: str, lang: str = "qr", is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=tr("btn_add_group", lang),
                url=f"https://t.me/{bot_username}?startgroup=true&admin=post_messages+delete_messages+restrict_members",
                icon_custom_emoji_id=CUSTOM_ID_PEOPLE
            )
        ],
        [
            InlineKeyboardButton(
                text=tr("btn_my_stats", lang),
                callback_data="user_global_stats",
                icon_custom_emoji_id=CUSTOM_ID_CHART
            ),
            InlineKeyboardButton(
                text=tr("btn_change_lang", lang),
                callback_data="user_select_lang",
                icon_custom_emoji_id=CUSTOM_ID_LANG
            )
        ],
        [
            InlineKeyboardButton(
                text=tr("btn_help", lang),
                callback_data="user_help",
                icon_custom_emoji_id=CUSTOM_ID_BOOK
            )
        ]
    ]
    if is_admin:
        buttons.append([
            InlineKeyboardButton(
                text="👑 Admin Panel",
                callback_data="admin_open_panel"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Қарақалпақша", callback_data="set_user_lang:qr", icon_custom_emoji_id=CUSTOM_ID_FLAG_QR),
                InlineKeyboardButton(text="O'zbekcha", callback_data="set_user_lang:uz", icon_custom_emoji_id=CUSTOM_ID_FLAG_UZ),
            ],
            [
                InlineKeyboardButton(text="Русский", callback_data="set_user_lang:ru", icon_custom_emoji_id=CUSTOM_ID_FLAG_RU),
                InlineKeyboardButton(text="English", callback_data="set_user_lang:en", icon_custom_emoji_id=CUSTOM_ID_FLAG_EN)
            ]
        ]
    )

@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    """Shaxsiy chatda /start buyrug'i"""
    user = message.from_user
    user_id = user.id
    saved_lang = cache.get_user_language(user_id)
    if not saved_lang:
        saved_lang = await db.get_user_language(user_id)
        if saved_lang:
            cache.set_user_language(user_id, saved_lang)

    # Foydalanuvchini bazaga saqlash / yangilash
    await db.register_user(
        user_id=user_id,
        full_name=user.full_name or "",
        username=user.username or "",
        language=saved_lang or "qr"
    )

    # Agar foydalanuvchi hali til tanlamagan bo'lsa -> Til menyusini chiqaramiz
    if not saved_lang:
        text = tr("choose_lang_title", "qr")
        await message.answer(text, reply_markup=get_language_keyboard(), parse_mode="HTML")
        return

    bot_info = await bot.get_me()
    name = user.full_name
    text = tr("start_message", saved_lang, name=name)
    is_admin = user_id in config.ADMINS
    await message.answer(text, reply_markup=get_start_keyboard(bot_info.username, saved_lang, is_admin=is_admin), parse_mode="HTML")


@router.callback_query(F.data == "user_select_lang")
@router.message(Command(commands=["lang", "language", "til"]))
async def show_lang_selection(event: Message | CallbackQuery):
    """Foydalanuvchi tilini tanlash menyusi"""
    text = tr("choose_lang_title", "qr")
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.edit_text(text, reply_markup=get_language_keyboard(), parse_mode="HTML")
    else:
        await event.answer(text, reply_markup=get_language_keyboard(), parse_mode="HTML")


@router.callback_query(F.data.startswith("set_user_lang:"))
async def process_user_lang_selection(callback: CallbackQuery, bot: Bot):
    """Til tanlanganda ishlaydigan handler"""
    lang = callback.data.split(":")[1]
    user = callback.from_user
    user_id = user.id
    await db.set_user_language(user_id, lang)
    cache.set_user_language(user_id, lang)
    await db.register_user(
        user_id=user_id,
        full_name=user.full_name or "",
        username=user.username or "",
        language=lang
    )
    await callback.answer(clean_alert_text(tr("lang_changed_success", lang)))

    bot_info = await bot.get_me()
    name = user.full_name
    text = tr("start_message", lang, name=name)
    is_admin = user_id in config.ADMINS
    await callback.message.edit_text(text, reply_markup=get_start_keyboard(bot_info.username, lang, is_admin=is_admin), parse_mode="HTML")


@router.message(Command(commands=["mymembers", "my_members", "my", "stat", "mystat"]))
@router.callback_query(F.data == "user_global_stats")
async def show_user_global_stats(event: Message | CallbackQuery, bot: Bot):
    """Foydalanuvchining barcha guruhlardagi statistikasini ko'rsatish"""

    user = event.from_user
    lang = cache.get_user_language(user.id) or await db.get_user_language(user.id) or "qr"
    stats = await db.get_user_all_groups_stats(user.id)

    if not stats:
        if lang == "ru":
            text = (
                f"👤 <b>Уважаемый(ая) {user.full_name}!</b>\n\n"
                f"Вы еще не пригласили участников ни в одну группу с ботом.\n"
                f"Приглашайте друзей в группы и смотрите свои результаты в этом разделе!"
            )
        elif lang == "en":
            text = (
                f"👤 <b>Dear {user.full_name}!</b>\n\n"
                f"You haven't invited any members to any group yet.\n"
                f"Invite your friends to groups and check your stats here!"
            )
        elif lang == "uz":
            text = (
                f"👤 <b>Hurmatli {user.full_name}!</b>\n\n"
                f"Siz hali bot ulangan hech bir guruhda odam qo'shmadingiz.\n"
                f"Guruhlarga do'stlaringizni taklif qiling va ushbu bo'limda natijalaringizni ko'ring!"
            )
        else: # qr
            text = (
                f"👤 <b>Ҳүрметли {user.full_name}!</b>\n\n"
                f"Сиз еле бот байланысқан ҳешбир топарда адам қоспадыңыз.\n"
                f"Топарларға досларыңызды мирәт етиң ҳәм усы бөлимде нәтийжелериңизди көриң!"
            )
    else:
        titles = {
            "qr": f"{EMOJI_CHART} <b>Сизиң топарлардағы статистикаңыз:</b>\n\n",
            "uz": f"{EMOJI_CHART} <b>Sizning guruhlardagi statistikangiz:</b>\n\n",
            "ru": f"{EMOJI_CHART} <b>Ваша статистика по группам:</b>\n\n",
            "en": f"{EMOJI_CHART} <b>Your statistics across groups:</b>\n\n"
        }
        text = titles.get(lang, titles["qr"])

        for idx, g in enumerate(stats, 1):
            title = g.get("title") or ("Белгисиз топар" if lang == "qr" else "Noma'lum guruh")
            req = g.get("required_count", 0)
            added = g.get("added_count", 0)
            is_exempt = g.get("is_exempt", 0)

            if is_exempt:
                if lang == "ru":
                    status = f"{EMOJI_CROWN} <i>Без ограничений (Администратор)</i>"
                elif lang == "en":
                    status = f"{EMOJI_CROWN} <i>Whitelisted (Admin / Exemption)</i>"
                elif lang == "uz":
                    status = f"{EMOJI_CROWN} <i>Cheklovsiz (Admin / Whitelist)</i>"
                else:
                    status = f"{EMOJI_CROWN} <i>Шекленбеген (Админ / Whitelist)</i>"
            elif req == 0:
                if lang == "ru":
                    status = f"{EMOJI_GREEN_CIRCLE} <i>Нет ограничений</i>"
                elif lang == "en":
                    status = f"{EMOJI_GREEN_CIRCLE} <i>No restrictions</i>"
                elif lang == "uz":
                    status = f"{EMOJI_GREEN_CIRCLE} <i>Cheklov yo'q</i>"
                else:
                    status = f"{EMOJI_GREEN_CIRCLE} <i>Шеклеў жоқ</i>"
            elif added >= req:
                if lang == "ru":
                    status = f"{EMOJI_CHECK} <i>Лимит выполнен</i>"
                elif lang == "en":
                    status = f"{EMOJI_CHECK} <i>Requirement fulfilled</i>"
                elif lang == "uz":
                    status = f"{EMOJI_CHECK} <i>Limit bajarilgan</i>"
                else:
                    status = f"{EMOJI_CHECK} <i>Лимит орынланған</i>"
            else:
                remains = req - added
                if lang == "ru":
                    status = f"{EMOJI_HOURGLASS} <i>Осталось пригласить: {remains}</i>"
                elif lang == "en":
                    status = f"{EMOJI_HOURGLASS} <i>Need {remains} more</i>"
                elif lang == "uz":
                    status = f"{EMOJI_HOURGLASS} <i>Yana {remains} ta kerak</i>"
                else:
                    status = f"{EMOJI_HOURGLASS} <i>Және {remains} керек</i>"

            if lang == "ru":
                text += (
                    f"{idx}. <b>{title}</b>\n"
                    f"   {EMOJI_PEOPLE} Приглашено: <b>{added}</b> (Лимит: {req})\n"
                    f"   🏷 Статус: {status}\n\n"
                )
            elif lang == "en":
                text += (
                    f"{idx}. <b>{title}</b>\n"
                    f"   {EMOJI_PEOPLE} Invited: <b>{added}</b> (Limit: {req})\n"
                    f"   🏷 Status: {status}\n\n"
                )
            elif lang == "uz":
                text += (
                    f"{idx}. <b>{title}</b>\n"
                    f"   {EMOJI_PEOPLE} Qo'shganlaringiz: <b>{added}</b> ta (Limit: {req})\n"
                    f"   🏷 Holat: {status}\n\n"
                )
            else: # qr
                text += (
                    f"{idx}. <b>{title}</b>\n"
                    f"   {EMOJI_PEOPLE} Қосқанларыңыз: <b>{added}</b> (Лимит: {req})\n"
                    f"   🏷 Жағдай: {status}\n\n"
                )

    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.answer(text, parse_mode="HTML")
    else:
        await event.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "user_help")
async def callback_help(callback: CallbackQuery):
    """Qo'llanma inline"""
    await callback.answer()
    user_id = callback.from_user.id
    lang = cache.get_user_language(user_id) or await db.get_user_language(user_id) or "qr"
    text = tr("help_group_admin", lang)
    await callback.message.answer(text, parse_mode="HTML")


@router.message(Command(commands=["help"]))
async def cmd_help(message: Message):
    """Barcha buyruqlar va qo'llanma"""
    user_id = message.from_user.id
    lang = cache.get_user_language(user_id) or await db.get_user_language(user_id) or "qr"
    text = tr("help_group_admin", lang)
    await message.answer(text, parse_mode="HTML")

