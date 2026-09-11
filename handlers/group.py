import asyncio
import logging
import time
from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, JOIN_TRANSITION, LEAVE_TRANSITION
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup,
    InlineKeyboardButton, ChatPermissions, ChatMemberUpdated
)
from database.db import db
from config import config
from filters.chat_type import ChatTypeFilter
from utils.helpers import get_user_mention, delete_message_delayed
from utils.cache import cache
from utils.i18n import tr, get_user_lang, clean_alert_text
from utils.captcha import (
    generate_math_captcha, kick_user_soft,
    captcha_timeout_handler, active_captchas
)
from utils.emojis import (
    EMOJI_BAN, EMOJI_PIN, EMOJI_POINT_DOWN, EMOJI_CHART,
    EMOJI_CHECK, EMOJI_STAR, EMOJI_GREEN_CIRCLE, EMOJI_PARTY,
    EMOJI_HOURGLASS, EMOJI_WARN, EMOJI_LIST, EMOJI_PEOPLE,
    EMOJI_WAVE, EMOJI_CHANNEL, EMOJI_SHIELD, EMOJI_CROSS, EMOJI_CHANNEL_LOUD,
    CUSTOM_ID_CHECK, CUSTOM_ID_BOOK, CUSTOM_ID_LOUDSPEAKER
)

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(ChatTypeFilter(["group", "supergroup"]))
router.callback_query.filter(ChatTypeFilter(["group", "supergroup"]))
router.chat_member.filter(ChatTypeFilter(["group", "supergroup"]))

async def clear_captcha_restriction(bot: Bot, chat_id: int, user_id: int):
    """Captcha yechilganda Telegram cheklovini bekor qilish (odam qo'shish huquqi bilan birga)"""
    try:
        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
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
                can_add_web_page_previews=True,
                can_invite_users=True
            )
        )
        cache.remove_muted(chat_id, user_id)
    except Exception as e:
        logger.warning(f"Clear captcha restriction error: {e}")

async def unrestrict_user(bot: Bot, chat_id: int, user_id: int):
    """Foydalanuvchining guruhda yozish huquqini to'liq ochish"""
    try:
        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
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
                can_add_web_page_previews=True,
                can_invite_users=True
            )
        )
        cache.remove_muted(chat_id, user_id)
        cache.add_allowed_user(chat_id, user_id)
    except Exception as e:
        logger.warning(f"Unrestrict error: {e}")

async def mute_user_10min(bot: Bot, chat_id: int, user_id: int):
    """Foydalanuvchini 10 daqiqaga mute qilish (lekin odam qo'shish huquqi ochiq qoladi)"""
    if cache.is_recently_muted(chat_id, user_id):
        return
    try:
        until_date = int(time.time() + 600)  # 10 daqiqa
        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(
                can_send_messages=False,
                can_invite_users=True
            ),
            until_date=until_date
        )
        cache.set_recently_muted(chat_id, user_id, ttl=540)
    except Exception as e:
        logger.warning(f"Mute error (Bot admin huquqi yo'qmi?): {e}")



@router.message(Command(commands=["mymembers", "my_members", "members", "odamlarim", "my", "stat"]))
async def cmd_my_members(message: Message, bot: Bot):
    """Foydalanuvchining o'zi qo'shgan a'zolari ro'yxati (ixcham)"""
    user = message.from_user
    if not user:
        return

    group = await db.get_or_create_group(message.chat.id, message.chat.title or "")
    required = group.get("required_count", 0)

    member = await db.get_or_create_member(
        message.chat.id, user.id, user.full_name, user.username or ""
    )
    added_count = member.get("added_count", 0)
    is_exempt = member.get("is_exempt", 0)

    referrals = await db.get_user_referrals(message.chat.id, user.id, limit=30)
    mention = get_user_mention(user.id, user.full_name, user.username)

    lang = group.get("language") or "qr"

    if lang == "ru":
        if is_exempt:
            status_text = f"{EMOJI_STAR} Предоставлен иммунитет (Без ограничений)"
        elif required == 0:
            status_text = f"{EMOJI_GREEN_CIRCLE} Без ограничений"
        elif added_count >= required:
            status_text = f"{EMOJI_CHECK} Доступ к написанию открыт"
        else:
            status_text = f"{EMOJI_HOURGLASS} Нужно добавить еще {required - added_count} друзей"

        text = (
            f"{EMOJI_CHART} {mention} — ваш счет: <b>{added_count}/{required}</b>\n"
            f"🏷 Статус: <i>{status_text}</i>\n\n"
        )
        if referrals:
            text += f"{EMOJI_LIST} <b>Добавленные вами участники ({len(referrals)}):</b>\n"
            for idx, ref in enumerate(referrals, 1):
                name = ref.get("joined_user_name") or f"ID: {ref['joined_user_id']}"
                status = f"{EMOJI_BAN} Вышел" if ref.get("is_left") else f"{EMOJI_CHECK} В группе"
                text += f"{idx}. {EMOJI_PEOPLE} <b>{name}</b> — <i>{status}</i>\n"
        else:
            text += "<i>Вы еще никого не пригласили.</i>"
    elif lang == "en":
        if is_exempt:
            status_text = f"{EMOJI_STAR} Whitelisted (No restrictions)"
        elif required == 0:
            status_text = f"{EMOJI_GREEN_CIRCLE} No restrictions"
        elif added_count >= required:
            status_text = f"{EMOJI_CHECK} Posting access granted"
        else:
            status_text = f"{EMOJI_HOURGLASS} Need {required - added_count} more friends"

        text = (
            f"{EMOJI_CHART} {mention} — your score: <b>{added_count}/{required}</b>\n"
            f"🏷 Status: <i>{status_text}</i>\n\n"
        )
        if referrals:
            text += f"{EMOJI_LIST} <b>Members invited by you ({len(referrals)}):</b>\n"
            for idx, ref in enumerate(referrals, 1):
                name = ref.get("joined_user_name") or f"ID: {ref['joined_user_id']}"
                status = f"{EMOJI_BAN} Left" if ref.get("is_left") else f"{EMOJI_CHECK} In group"
                text += f"{idx}. {EMOJI_PEOPLE} <b>{name}</b> — <i>{status}</i>\n"
        else:
            text += "<i>You haven't invited anyone yet.</i>"
    elif lang == "uz":
        if is_exempt:
            status_text = f"{EMOJI_STAR} Imtiyoz berilgan (Cheklovsiz)"
        elif required == 0:
            status_text = f"{EMOJI_GREEN_CIRCLE} Cheklov yo'q"
        elif added_count >= required:
            status_text = f"{EMOJI_CHECK} Yozish huquqi mavjud"
        else:
            status_text = f"{EMOJI_HOURGLASS} Yana {required - added_count} ta do'st kerak"

        text = (
            f"{EMOJI_CHART} {mention} — sizning hisobingiz: <b>{added_count}/{required}</b>\n"
            f"🏷 Holat: <i>{status_text}</i>\n\n"
        )
        if referrals:
            text += f"{EMOJI_LIST} <b>Qo'shgan a'zolaringiz ({len(referrals)} ta):</b>\n"
            for idx, ref in enumerate(referrals, 1):
                name = ref.get("joined_user_name") or f"ID: {ref['joined_user_id']}"
                status = f"{EMOJI_BAN} Chiqib ketgan" if ref.get("is_left") else f"{EMOJI_CHECK} Guruhda"
                text += f"{idx}. {EMOJI_PEOPLE} <b>{name}</b> — <i>{status}</i>\n"
        else:
            text += "<i>Siz hali hech kimni qo'shmadingiz.</i>"
    else:
        if is_exempt:
            status_text = f"{EMOJI_STAR} Жеңиллик берилген (Шеклеўсиз)"
        elif required == 0:
            status_text = f"{EMOJI_GREEN_CIRCLE} Шеклеў жоқ"
        elif added_count >= required:
            status_text = f"{EMOJI_CHECK} Жазыў ҳуқықы бар"
        else:
            status_text = f"{EMOJI_HOURGLASS} Және {required - added_count} дос керек"

        text = (
            f"{EMOJI_CHART} {mention} — сизиң есабыңыз: <b>{added_count}/{required}</b>\n"
            f"🏷 Жағдай: <i>{status_text}</i>\n\n"
        )
        if referrals:
            text += f"{EMOJI_LIST} <b>Қосқан ағзаларыңыз ({len(referrals)}):</b>\n"
            for idx, ref in enumerate(referrals, 1):
                name = ref.get("joined_user_name") or f"ID: {ref['joined_user_id']}"
                status = f"{EMOJI_BAN} Шығып кеткен" if ref.get("is_left") else f"{EMOJI_CHECK} Топарда"
                text += f"{idx}. {EMOJI_PEOPLE} <b>{name}</b> — <i>{status}</i>\n"
        else:
            text += "<i>Сиз еле ҳеш кимди қоспадыңыз.</i>"

    try:
        msg = await bot.send_message(
            chat_id=message.chat.id,
            text=text,
            parse_mode="HTML",
            receiver_user_id=user.id
        )
    except Exception:
        msg = await message.reply(text, parse_mode="HTML")

    asyncio.create_task(delete_message_delayed(bot, message.chat.id, msg.message_id, 25))
    try:
        await message.delete()
    except Exception:
        pass


@router.callback_query(F.data.startswith("check_my_status:"))
async def callback_check_status(callback: CallbackQuery, bot: Bot):
    """'✅ Men odam qo'shdim' tugmasi tekshiruvi"""
    target_user_id = int(callback.data.split(":")[1])
    user = callback.from_user

    group = await db.get_or_create_group(callback.message.chat.id, callback.message.chat.title or "")
    lang = group.get("language") or get_user_lang(user.language_code)

    if user.id != target_user_id:
        await callback.answer(clean_alert_text(tr("admin_only_btn", lang=lang)), show_alert=True)
        return
    required = group.get("required_count", 0)
    ch_id = group.get("channel_id")

    member = await db.get_or_create_member(
        callback.message.chat.id, user.id, user.full_name, user.username or ""
    )
    added = member.get("added_count", 0)
    is_exempt = member.get("is_exempt", 0)

    # 1. Odam qo'shish sharti bajarilganmi?
    if is_exempt or required == 0 or added >= required:
        # 2. Agar kanal bor bo'lsa, kanalga a'zolik tekshiriladi
        if ch_id:
            try:
                ch_member = await bot.get_chat_member(ch_id, user.id)
                if ch_member.status in ["member", "administrator", "creator"]:
                    await unrestrict_user(bot, callback.message.chat.id, user.id)
                    await callback.answer(clean_alert_text(tr("sub_success", lang=lang)), show_alert=True)
                    try:
                        await callback.message.delete()
                    except Exception:
                        pass
                    return
            except Exception:
                pass

            # Odam qo'shgan, lekin kanalga a'zo emas
            await callback.answer(clean_alert_text(tr("add_member_success_need_channel", lang=lang)), show_alert=True)
            return

        # Kanal yo'q bo'lsa — ruxsat berildi
        await unrestrict_user(bot, callback.message.chat.id, user.id)
        msg_ok = {
            "qr": f"✅ Сиз {added}/{required} адам қосқансыз. Енди топарда биймәлел жаза аласыз!",
            "uz": f"✅ Siz {added}/{required} ta odam qo'shgansiz. Endi guruhda bemalol yoza olasiz!",
            "ru": "✅ Вы выполнили условие! Теперь можете писать в группе.",
            "en": "✅ You met the requirement! You can now post."
        }.get(lang, f"✅ Сиз {added}/{required} адам қосқансыз. Енди топарда биймәлел жаза аласыз!")
        await callback.answer(clean_alert_text(msg_ok), show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass
    else:
        remains = required - added
        await callback.answer(clean_alert_text(tr("add_member_remains", lang=lang, added=added, required=required, remains=remains)), show_alert=True)


@router.callback_query(F.data.startswith("check_sub:"))
async def callback_check_subscription(callback: CallbackQuery, bot: Bot):
    """'✅ Obunani tekshirish' tugmasi tekshiruvi (Aynan rasmdagidek)"""
    target_user_id = int(callback.data.split(":")[1])
    user = callback.from_user

    group = await db.get_or_create_group(callback.message.chat.id, callback.message.chat.title or "")
    lang = group.get("language") or get_user_lang(user.language_code)

    if user.id != target_user_id:
        await callback.answer(clean_alert_text(tr("admin_only_btn", lang=lang)), show_alert=True)
        return
    ch_id = group.get("channel_id")

    if not ch_id:
        await unrestrict_user(bot, callback.message.chat.id, user.id)
        await callback.answer(clean_alert_text(tr("sub_success", lang=lang)), show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass
        return

    try:
        ch_member = await bot.get_chat_member(ch_id, user.id)
        if ch_member.status in ["member", "administrator", "creator"]:
            await unrestrict_user(bot, callback.message.chat.id, user.id)
            await callback.answer(clean_alert_text(tr("sub_success", lang=lang)), show_alert=True)
            try:
                await callback.message.delete()
            except Exception:
                pass
            return
        else:
            await callback.answer(clean_alert_text(tr("sub_failed", lang=lang)), show_alert=True)
    except Exception as e:
        logger.error(f"Channel sub check error: {e}")
        # Agar kanal tekshiruvida xatolik bo'lsa (masalan bot admin qilinmagan bo'lsa), foydalanuvchini bloklamaymiz
        await unrestrict_user(bot, callback.message.chat.id, user.id)
        await callback.answer(clean_alert_text(tr("sub_success", lang=lang)), show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass


@router.callback_query(F.data.startswith("give_access:"))
async def callback_give_access(callback: CallbackQuery, bot: Bot):
    """'⭐ Imtiyoz berish' tugmasi (faqat adminlar uchun)"""
    target_user_id = int(callback.data.split(":")[1])
    clicker_id = callback.from_user.id
    lang = get_user_lang(callback.from_user.language_code)

    # Admin ekanligini keshdan tekshiramiz
    is_admin = False
    if clicker_id in config.ADMINS:
        is_admin = True
    else:
        cached_admins = cache.get_admins(callback.message.chat.id)
        if cached_admins and clicker_id in cached_admins:
            is_admin = True
        else:
            try:
                admins = await bot.get_chat_administrators(callback.message.chat.id)
                admin_ids = {a.user.id for a in admins}
                cache.set_admins(callback.message.chat.id, admin_ids, ttl=300)
                is_admin = clicker_id in admin_ids
            except Exception:
                pass

    if not is_admin:
        await callback.answer(clean_alert_text(tr("admin_only_btn", lang=lang)), show_alert=True)
        return

    await db.set_exempt(callback.message.chat.id, target_user_id, True)
    await unrestrict_user(bot, callback.message.chat.id, target_user_id)
    access_msg = {
        "qr": "⭐ Пайдаланыўшыға шекленбеген жазиў абзаллығы берилди ҳәм блок шешилди!",
        "uz": "⭐ Foydalanuvchiga cheklovsiz yozish imtiyozi berildi va blok yechildi!",
        "ru": "⭐ Пользователю предоставлен иммунитет и ограничения сняты!",
        "en": "⭐ User granted immunity and restrictions removed!"
    }.get(lang, "⭐ Пайдаланыўшыға шекленбеген жазиў абзаллығы берилди ҳәм блок шешилди!")
    await callback.answer(clean_alert_text(access_msg), show_alert=True)

    try:
        await callback.message.delete()
    except Exception:
        pass


@router.callback_query(F.data.startswith("captcha_ans:"))
async def callback_captcha_answer(callback: CallbackQuery, bot: Bot):
    """Matematik Captcha javobi tekshiruvi (4 ta variant, 3 ta urinish)"""
    data_parts = callback.data.split(":")
    target_user_id = int(data_parts[1])
    selected_ans = int(data_parts[2])
    user = callback.from_user
    chat_id = callback.message.chat.id
    lang = get_user_lang(user.language_code)

    # 1. Faqat shu yangi a'zo bosa oladi
    if user.id != target_user_id:
        await callback.answer(clean_alert_text(tr("captcha_not_for_you", lang=lang)), show_alert=True)
        return

    captcha_info = active_captchas.get((chat_id, user.id))
    if not captcha_info:
        expired_msg = "⚠️ Тексериў мүддети тамамланған." if lang == "qr" else ("⚠️ Tekshiruv muddati tugagan." if lang == "uz" else "⚠️ Время проверки истекло.")
        await callback.answer(clean_alert_text(expired_msg), show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass
        return

    # Tez-tez bosish (double-click/race condition) dan himoya
    if captcha_info.get("processing"):
        await callback.answer()
        return
    captcha_info["processing"] = True

    try:
        correct_ans = captcha_info["correct"]

        if selected_ans == correct_ans:
            # ✅ TO'G'RI JAVOB!
            timeout_task = captcha_info.get("task")
            if timeout_task:
                timeout_task.cancel()
            active_captchas.pop((chat_id, user.id), None)

            await callback.answer(clean_alert_text(tr("captcha_success", lang=lang)), show_alert=True)
            try:
                await callback.message.delete()
            except Exception:
                pass

            # Captcha cheklovini Telegramda olib tashlaymiz
            await clear_captcha_restriction(bot, chat_id, user.id)

            # Guruh limit sozlamalarini tekshiramiz
            group = cache.get_group_settings(chat_id)
            if not group:
                group = await db.get_or_create_group(chat_id, callback.message.chat.title or "")

            required = group.get("required_count", 0)
            ch_id = group.get("channel_id")

            # Agar odam qo'shish yoki kanal sharti bo'lmasa -> darhol ruxsat berilganlar keshiga kiritamiz
            if required <= 0 and not ch_id:
                cache.add_allowed_user(chat_id, user.id)
        else:
            # ❌ NOTO'G'RI JAVOB!
            captcha_info["attempts_left"] -= 1
            attempts_left = captcha_info["attempts_left"]

            if attempts_left > 0:
                # Har bir urinishda yangi random misol generatsiya qilamiz! (sum <= 30)
                a, b, new_correct, options = generate_math_captcha()
                captcha_info["correct"] = new_correct

                new_keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text=str(options[0]),
                                callback_data=f"captcha_ans:{user.id}:{options[0]}"
                            ),
                            InlineKeyboardButton(
                                text=str(options[1]),
                                callback_data=f"captcha_ans:{user.id}:{options[1]}"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text=str(options[2]),
                                callback_data=f"captcha_ans:{user.id}:{options[2]}"
                            ),
                            InlineKeyboardButton(
                                text=str(options[3]),
                                callback_data=f"captcha_ans:{user.id}:{options[3]}"
                            )
                        ]
                    ]
                )

                mention = get_user_mention(user.id, user.full_name, user.username)
                new_text = tr("captcha_message", lang=lang, mention=mention, a=a, b=b)

                try:
                    await callback.message.edit_text(new_text, reply_markup=new_keyboard, parse_mode="HTML")
                except Exception as e:
                    logger.warning(f"Captcha edit error: {e}")

                await callback.answer(
                    clean_alert_text(tr("captcha_wrong", lang=lang, attempts=attempts_left)),
                    show_alert=True
                )
            else:
                # 3 marta ham noto'g'ri bo'lsa -> Guruhdan chiqariladi (Kick)
                timeout_task = captcha_info.get("task")
                if timeout_task:
                    timeout_task.cancel()
                active_captchas.pop((chat_id, user.id), None)

                await callback.answer(clean_alert_text(tr("captcha_failed_kick", lang=lang)), show_alert=True)
                try:
                    await callback.message.delete()
                except Exception:
                    pass

                # Guruhdan chiqarish (qora ro'yxatsiz)
                await kick_user_soft(bot, chat_id, user.id)
    finally:
        if (chat_id, user.id) in active_captchas:
            active_captchas[(chat_id, user.id)]["processing"] = False


async def process_member_join(bot: Bot, chat_id: int, chat_title: str, new_user, referrer=None):
    """Yangi a'zo qo'shilganda umumiy qayta ishlash funksiyasi (service message yoki ChatMemberUpdated orqali)"""
    if not new_user or new_user.is_bot:
        return

    # Takroriy hodisalarni kesh orqali filtrlaymiz (masalan yangi xabar + chat_member bir vaqtda kelsa)
    if cache.is_recently_joined(chat_id, new_user.id):
        return
    cache.set_recently_joined(chat_id, new_user.id, ttl=30)

    group = await db.get_or_create_group(chat_id, chat_title or "")
    required = group.get("required_count", 0)
    is_captcha_on = group.get("captcha", 1)
    lang = group.get("language") or get_user_lang(new_user.language_code)

    # Foydalanuvchi guruhga O'ZI qo'shilganmi yoki kimdir taklif qilganmi?
    is_self_joined = (referrer is None) or (referrer.id == new_user.id)

    # ── 1. MATEMATIK CAPTCHA (FAQAT O'ZI QO'SHILGANLAR UCHUN!) ──
    if is_captcha_on and is_self_joined:
        # Yangi a'zoning yozishini cheklaymiz, LEKIN odam qo'shish huquqi ochiq qoladi!
        try:
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=new_user.id,
                permissions=ChatPermissions(
                    can_send_messages=False,
                    can_invite_users=True
                )
            )
        except Exception as e:
            logger.warning(f"Restrict error on captcha join: {e}")

        a, b, correct, options = generate_math_captcha()

        # 2x2 shakldagi 4 ta variant tugmasi
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=str(options[0]),
                        callback_data=f"captcha_ans:{new_user.id}:{options[0]}"
                    ),
                    InlineKeyboardButton(
                        text=str(options[1]),
                        callback_data=f"captcha_ans:{new_user.id}:{options[1]}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=str(options[2]),
                        callback_data=f"captcha_ans:{new_user.id}:{options[2]}"
                    ),
                    InlineKeyboardButton(
                        text=str(options[3]),
                        callback_data=f"captcha_ans:{new_user.id}:{options[3]}"
                    )
                ]
            ]
        )

        new_user_mention = get_user_mention(new_user.id, new_user.full_name, new_user.username)
        captcha_text = tr("captcha_message", lang=lang, mention=new_user_mention, a=a, b=b)

        # MUHIM: receiver_user_id ISHLATILMAYDI! Chunki Telegram API da receiver_user_id bo'lgan
        # xabarlarni editMessageText bilan tahrirlab bo'lmaydi (xato beradi).
        try:
            captcha_msg = await bot.send_message(
                chat_id=chat_id,
                text=captcha_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )

            # 5 daqiqalik timeout (300 soniya)
            timeout_task = asyncio.create_task(
                captcha_timeout_handler(bot, chat_id, new_user.id, delay=300)
            )

            active_captchas[(chat_id, new_user.id)] = {
                "correct": correct,
                "attempts_left": 3,
                "msg_id": captcha_msg.message_id,
                "task": timeout_task,
                "lang": lang,
                "processing": False
            }
        except Exception as e:
            logger.error(f"Send captcha error: {e}")

    # ── 2. AGAR KIMDIR TAKLIF QILGAN BO'LSA -> HISOBGA OLAMIZ ──
    if referrer and referrer.id != new_user.id:
        mention = get_user_mention(referrer.id, referrer.full_name, referrer.username)

        success, reason, current_cnt = await db.add_referral(
            chat_id=chat_id,
            referrer_id=referrer.id,
            joined_user_id=new_user.id,
            referrer_name=referrer.full_name,
            referrer_username=referrer.username or "",
            joined_user_name=new_user.full_name,
            joined_user_username=new_user.username or ""
        )

        new_user_mention = get_user_mention(new_user.id, new_user.full_name, new_user.username)

        if success:
            if required > 0:
                if current_cnt >= required:
                    if lang == "ru":
                        text = (
                            f"{EMOJI_PARTY} {mention}, вы пригласили {new_user_mention}!\n"
                            f"{EMOJI_CHECK} <b>Поздравляем!</b> Лимит приглашений выполнен (<b>{current_cnt}/{required}</b>)."
                        )
                    elif lang == "en":
                        text = (
                            f"{EMOJI_PARTY} {mention}, you invited {new_user_mention}!\n"
                            f"{EMOJI_CHECK} <b>Congratulations!</b> Member limit fulfilled (<b>{current_cnt}/{required}</b>)."
                        )
                    elif lang == "uz":
                        text = (
                            f"{EMOJI_PARTY} {mention}, siz {new_user_mention}ni qo'shdingiz!\n"
                            f"{EMOJI_CHECK} <b>Tabriklaymiz!</b> Odam qo'shish limiti bajarildi (<b>{current_cnt}/{required}</b>)."
                        )
                    else:
                        text = (
                            f"{EMOJI_PARTY} {mention}, сиз {new_user_mention}ди қосдыңыз!\n"
                            f"{EMOJI_CHECK} <b>Қутлықлаймыз!</b> Адам қосыў лимити орынланды (<b>{current_cnt}/{required}</b>)."
                        )
                    # Agar kanal bo'lmasa, darhol unrestrict qilamiz
                    ch_id = group.get("channel_id")
                    if not ch_id:
                        await unrestrict_user(bot, chat_id, referrer.id)
                else:
                    if lang == "ru":
                        text = (
                            f"{EMOJI_PARTY} {mention}, вы пригласили {new_user_mention}!\n"
                            f"{EMOJI_CHART} Ваш счет: <b>{current_cnt}/{required}</b>"
                        )
                    elif lang == "en":
                        text = (
                            f"{EMOJI_PARTY} {mention}, you invited {new_user_mention}!\n"
                            f"{EMOJI_CHART} Your score: <b>{current_cnt}/{required}</b>"
                        )
                    elif lang == "uz":
                        text = (
                            f"{EMOJI_PARTY} {mention}, siz {new_user_mention}ni qo'shdingiz!\n"
                            f"{EMOJI_CHART} Sizning hisobingiz: <b>{current_cnt}/{required}</b>"
                        )
                    else:
                        text = (
                            f"{EMOJI_PARTY} {mention}, сиз {new_user_mention}ди қосдыңыз!\n"
                            f"{EMOJI_CHART} Сизиң есап бетиңиз: <b>{current_cnt}/{required}</b>"
                        )
            else:
                if lang == "ru":
                    text = f"{EMOJI_PARTY} {mention}, вы пригласили {new_user_mention}! (Всего: <b>{current_cnt}</b>)"
                elif lang == "en":
                    text = f"{EMOJI_PARTY} {mention}, you invited {new_user_mention}! (Total: <b>{current_cnt}</b>)"
                elif lang == "uz":
                    text = f"{EMOJI_PARTY} {mention}, {new_user_mention}ni qo'shdingiz! (Jami: <b>{current_cnt}</b>)"
                else:
                    text = f"{EMOJI_PARTY} {mention}, сиз {new_user_mention}ди қосдыңыз! (Жәми: <b>{current_cnt}</b>)"

            try:
                msg = await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
                asyncio.create_task(delete_message_delayed(bot, chat_id, msg.message_id, 8))
            except Exception:
                pass

        elif reason in ["already_exists_same_user", "already_exists_other"]:
            if lang == "ru":
                already_text = (
                    f"{EMOJI_WARN} {mention}, <b>{new_user.full_name}</b> уже был добавлен ранее, поэтому не засчитан!\n"
                    f"{EMOJI_CHART} Ваш счет: <b>{current_cnt}/{required}</b>"
                )
            elif lang == "en":
                already_text = (
                    f"{EMOJI_WARN} {mention}, <b>{new_user.full_name}</b> was already added before, so not counted!\n"
                    f"{EMOJI_CHART} Your score: <b>{current_cnt}/{required}</b>"
                )
            elif lang == "uz":
                already_text = (
                    f"{EMOJI_WARN} {mention}, <b>{new_user.full_name}</b> avval qo'shilgan, shuning uchun hisoblanmadi!\n"
                    f"{EMOJI_CHART} Sizning hisobingiz: <b>{current_cnt}/{required}</b>"
                )
            else:
                already_text = (
                    f"{EMOJI_WARN} {mention}, <b>{new_user.full_name}</b> алдын қосылған, соның ушын есапланбады!\n"
                    f"{EMOJI_CHART} Сизиң есап бетиңиз: <b>{current_cnt}/{required}</b>"
                )
            try:
                msg = await bot.send_message(
                    chat_id=chat_id,
                    text=already_text,
                    parse_mode="HTML"
                )
                asyncio.create_task(delete_message_delayed(bot, chat_id, msg.message_id, 8))
            except Exception:
                pass


@router.message(F.new_chat_members)
async def on_new_chat_members(message: Message, bot: Bot):
    """Guruhga yangi a'zo qo'shilganda tutish va Captcha chiqarish (Service message orqali)"""
    chat_id = message.chat.id
    new_members = message.new_chat_members or []
    referrer = message.from_user

    bot_info = await bot.get_me()
    if any(m.id == bot_info.id for m in new_members):
        welcome_text = (
            f"{EMOJI_WAVE} <b>Ассалаўма алейкум!</b>\n\n"
            f"Бот жедел болыўы ушын топарда <b>Админ (Хабарларды өшириў ҳәм ағзаларды шеклеў ҳуқықы менен)</b> бериң.\n"
            f"{EMOJI_PIN} Лимит орнатыў: <code>/set 5</code>\n"
            f"{EMOJI_CHANNEL} Канал жалғаў: <code>/setchannel @kanal_username</code>\n"
            f"{EMOJI_SHIELD} Captcha: <code>/captcha on/off</code>"
        )
        await message.answer(welcome_text, parse_mode="HTML")
        return

    for new_user in new_members:
        await process_member_join(bot, chat_id, message.chat.title or "", new_user, referrer=referrer)

    group = await db.get_or_create_group(chat_id, message.chat.title or "")
    del_service = group.get("del_service_msg", 1)
    if del_service:
        try:
            await message.delete()
        except Exception:
            pass


@router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def on_chat_member_joined(event: ChatMemberUpdated, bot: Bot):
    """Katta guruhlarda Telegram yangi a'zo xabarlarini yashirganda ham tutib olish"""
    chat_id = event.chat.id
    new_user = event.new_chat_member.user
    referrer = event.from_user

    bot_info = await bot.get_me()
    if new_user.id == bot_info.id:
        return

    await process_member_join(bot, chat_id, event.chat.title or "", new_user, referrer=referrer)


@router.message(F.left_chat_member)
async def on_left_chat_member(message: Message, bot: Bot):
    """Guruhdan a'zo chiqqanda tutish"""
    chat_id = message.chat.id
    left_user = message.left_chat_member
    if left_user and not left_user.is_bot:
        # Faol captcha bo'lsa tozalaymiz
        captcha_info = active_captchas.pop((chat_id, left_user.id), None)
        if captcha_info:
            task = captcha_info.get("task")
            if task:
                task.cancel()
            msg_id = captcha_info.get("msg_id")
            if msg_id:
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                except Exception:
                    pass

        group = await db.get_or_create_group(chat_id, message.chat.title or "")
        required = group.get("required_count", 0)

        penalty, referrer_id, new_count = await db.handle_member_left(chat_id, left_user.id)
        if penalty and referrer_id:
            try:
                referrer_member = await db.get_member_stats(chat_id, referrer_id)
                referrer_name = referrer_member.get("full_name", "Foydalanuvchi") if referrer_member else "Foydalanuvchi"
                mention = get_user_mention(referrer_id, referrer_name)
                cache.remove_allowed_user(chat_id, referrer_id)
                lang = group.get("language") or "qr"
                if lang == "ru":
                    left_text = (
                        f"{EMOJI_WARN} {mention}, приглашенный вами участник (<b>{left_user.full_name}</b>) вышел из группы.\n"
                        f"{EMOJI_CHART} Ваш новый счет: <b>{new_count}/{required}</b>"
                    )
                elif lang == "en":
                    left_text = (
                        f"{EMOJI_WARN} {mention}, the member invited by you (<b>{left_user.full_name}</b>) left the group.\n"
                        f"{EMOJI_CHART} Your new score: <b>{new_count}/{required}</b>"
                    )
                elif lang == "uz":
                    left_text = (
                        f"{EMOJI_WARN} {mention}, siz qo'shgan a'zo (<b>{left_user.full_name}</b>) chiqib ketdi.\n"
                        f"{EMOJI_CHART} Yangi hisobingiz: <b>{new_count}/{required}</b>"
                    )
                else:
                    left_text = (
                        f"{EMOJI_WARN} {mention}, сиз қосқан ағза (<b>{left_user.full_name}</b>) шығып кетти.\n"
                        f"{EMOJI_CHART} Жаңа есап бетиңиз: <b>{new_count}/{required}</b>"
                    )
                msg = await message.answer(left_text, parse_mode="HTML")
                asyncio.create_task(delete_message_delayed(bot, chat_id, msg.message_id, 8))
            except Exception:
                pass

    group = await db.get_or_create_group(chat_id, message.chat.title or "")
    del_service = group.get("del_service_msg", 1)
    if del_service:
        try:
            await message.delete()
        except Exception:
            pass


@router.chat_member(ChatMemberUpdatedFilter(LEAVE_TRANSITION))
async def on_chat_member_left(event: ChatMemberUpdated, bot: Bot):
    """Katta guruhlarda a'zo chiqqanda tutish"""
    chat_id = event.chat.id
    left_user = event.new_chat_member.user
    if not left_user or left_user.is_bot:
        return

    # Faol captcha bo'lsa tozalaymiz
    captcha_info = active_captchas.pop((chat_id, left_user.id), None)
    if captcha_info:
        task = captcha_info.get("task")
        if task:
            task.cancel()
        msg_id = captcha_info.get("msg_id")
        if msg_id:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except Exception:
                pass

    group = await db.get_or_create_group(chat_id, event.chat.title or "")
    required = group.get("required_count", 0)

    penalty, referrer_id, new_count = await db.handle_member_left(chat_id, left_user.id)
    if penalty and referrer_id:
        try:
            referrer_member = await db.get_member_stats(chat_id, referrer_id)
            referrer_name = referrer_member.get("full_name", "Foydalanuvchi") if referrer_member else "Foydalanuvchi"
            mention = get_user_mention(referrer_id, referrer_name)
            cache.remove_allowed_user(chat_id, referrer_id)
            lang = group.get("language") or "qr"
            if lang == "ru":
                left_text = (
                    f"{EMOJI_WARN} {mention}, приглашенный вами участник (<b>{left_user.full_name}</b>) вышел из группы.\n"
                    f"{EMOJI_CHART} Ваш новый счет: <b>{new_count}/{required}</b>"
                )
            elif lang == "en":
                left_text = (
                    f"{EMOJI_WARN} {mention}, the member invited by you (<b>{left_user.full_name}</b>) left the group.\n"
                    f"{EMOJI_CHART} Your new score: <b>{new_count}/{required}</b>"
                )
            elif lang == "uz":
                left_text = (
                    f"{EMOJI_WARN} {mention}, siz qo'shgan a'zo (<b>{left_user.full_name}</b>) chiqib ketdi.\n"
                    f"{EMOJI_CHART} Yangi hisobingiz: <b>{new_count}/{required}</b>"
                )
            else:
                left_text = (
                    f"{EMOJI_WARN} {mention}, сиз қосқан ағза (<b>{left_user.full_name}</b>) шығып кетти.\n"
                    f"{EMOJI_CHART} Жаңа есап бетиңиз: <b>{new_count}/{required}</b>"
                )
            msg = await bot.send_message(chat_id=chat_id, text=left_text, parse_mode="HTML")
            asyncio.create_task(delete_message_delayed(bot, chat_id, msg.message_id, 8))
        except Exception:
            pass


@router.message(Command(commands=["help"]))
async def cmd_member_help(message: Message, bot: Bot):
    """Guruhda oddiy a'zo /help yoki /help@bot yozsa"""
    try:
        await message.delete()
    except Exception:
        pass

    group = await db.get_or_create_group(message.chat.id, message.chat.title or "")
    lang = group.get("language") or get_user_lang(message.from_user.language_code if message.from_user else None)
    text = tr("help_group_user", lang)

    bot_info = await bot.get_me()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=tr("btn_help", lang),
                    url=f"https://t.me/{bot_info.username}?start=help",
                    icon_custom_emoji_id=CUSTOM_ID_BOOK
                )
            ]
        ]
    )
    user_id = message.from_user.id if message.from_user else None
    try:
        if user_id:
            msg = await bot.send_message(
                chat_id=message.chat.id,
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML",
                receiver_user_id=user_id
            )
        else:
            msg = await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        if msg:
            asyncio.create_task(delete_message_delayed(bot, message.chat.id, msg.message_id, 20))
    except Exception:
        pass


@router.message()
async def check_group_message(message: Message, bot: Bot):
    """100k guruhlar uchun yuqori unumdorlikdagi xabarlarni tekshirish va cheklash"""
    user = message.from_user
    if not user or user.is_bot:
        return

    chat_id = message.chat.id

    # 0. Agar xabar buyruq bo'lsa (/set, /setchannel, /help va h.k.) — uni o'chirmaymiz va bloklamaymiz!
    if message.text and message.text.startswith("/"):
        return

    # 0.5. Agar foydalanuvchida faol captcha bo'lsa -> xabarni o'chiramiz va to'xtatamiz
    if (chat_id, user.id) in active_captchas:
        try:
            await message.delete()
        except Exception:
            pass
        return

    # 1. Guruh anonim admini sifatida yozilganda
    if message.sender_chat and message.sender_chat.id == message.chat.id:
        return
    if user.username == "GroupAnonymousBot":
        return

    # 2. Tezkor Kesh tekshiruvi: Agar bu foydalanuvchiga ruxsat berilgan bo'lsa -> DARHOL o'tkazamiz (0.0001 ms)
    if cache.is_user_allowed(chat_id, user.id):
        return

    # Bot adminlari bo'lsa -> o'tkazamiz
    if user.id in config.ADMINS:
        cache.add_allowed_user(chat_id, user.id)
        return

    # Guruh sozlamalarini keshdan olamiz
    group = cache.get_group_settings(chat_id)
    if not group:
        group = await db.get_or_create_group(chat_id, message.chat.title or "")
        cache.set_group_settings(chat_id, group, ttl=120)

    if not group.get("is_active", 1):
        return

    required = group.get("required_count", 0)
    ch_id = group.get("channel_id")
    ch_user = group.get("channel_username")
    ch_title = group.get("channel_title")

    # Agar limit ham 0, kanal ham yo'q bo'lsa -> o'tkazamiz
    if required <= 0 and not ch_id:
        cache.add_allowed_user(chat_id, user.id)
        return

    # Adminlarni keshdan tekshiramiz (Har xabarda Telegram API ga so'rov yubormaslik uchun!)
    cached_admins = cache.get_admins(chat_id)
    if cached_admins is None:
        try:
            admins = await bot.get_chat_administrators(chat_id)
            cached_admins = {a.user.id for a in admins}
            cache.set_admins(chat_id, cached_admins, ttl=300)
        except Exception:
            try:
                m = await bot.get_chat_member(chat_id, user.id)
                if m.status in ["creator", "administrator"]:
                    cache.add_allowed_user(chat_id, user.id)
                    return
            except Exception:
                pass
            cached_admins = set()

    if user.id in cached_admins:
        cache.add_allowed_user(chat_id, user.id)
        return

    # Foydalanuvchini bazadan tekshiramiz
    member = await db.get_or_create_member(chat_id, user.id, user.full_name, user.username or "")
    if member.get("is_exempt", 0):
        cache.add_allowed_user(chat_id, user.id)
        return

    added = member.get("added_count", 0)
    lang = group.get("language") or get_user_lang(user.language_code)
    mention = get_user_mention(user.id, user.full_name, user.username)

    # ── 1-BOSQICH: ODAM QO'SHISH SHARTI ──
    if required > 0 and added < required:
        try:
            await message.delete()
        except Exception as e:
            logger.warning(f"Message delete error: {e}")

        # 10 daqiqaga MUTE qo'yamiz (serverni 100k guruh spamidan qutqaradi!)
        await mute_user_10min(bot, chat_id, user.id)

        warning_text = tr(
            "need_members_warning",
            lang=lang,
            mention=mention,
            required=required,
            added=added
        )

        # Foydalanuvchi talabi: Faqat bitta ixcham tugma qoladi (Imtiyoz tugmasi olib tashlandi)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=tr("btn_i_added", lang=lang),
                        callback_data=f"check_my_status:{user.id}",
                        icon_custom_emoji_id=CUSTOM_ID_CHECK
                    )
                ]
            ]
        )


        try:
            warn_msg = await bot.send_message(
                chat_id=chat_id,
                text=warning_text,
                reply_markup=keyboard,
                parse_mode="HTML",
                receiver_user_id=user.id
            )
            asyncio.create_task(delete_message_delayed(bot, chat_id, warn_msg.message_id, 12))
        except Exception:
            pass
        return

    # ── 2-BOSQICH: KANALGA A'ZO BO'LISH SHARTI (Aynan rasmdagidek) ──
    if ch_id:
        is_subbed = False
        try:
            ch_member = await bot.get_chat_member(ch_id, user.id)
            if ch_member.status in ["member", "administrator", "creator"]:
                is_subbed = True
        except Exception as e:
            logger.error(f"Channel check error: {e}")
            is_subbed = True  # Xatolik bo'lsa foydalanuvchini to'xtatmaymiz

        if not is_subbed:
            try:
                await message.delete()
            except Exception:
                pass

            # 10 daqiqaga MUTE qo'yamiz
            await mute_user_10min(bot, chat_id, user.id)

            channel_url = f"https://t.me/{ch_user}" if ch_user else f"https://t.me/c/{ch_id.replace('-100', '')}/1"
            channel_btn_name = ch_title if ch_title else tr("btn_channel_link", lang=lang)

            warning_text = tr(
                "need_channel_sub",
                lang=lang,
                mention=mention
            )

            # Aynan rasmdagidek 2 ta tugma (premium animatsion ikonka bilan):
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=f"{channel_btn_name}",
                            url=channel_url,
                            icon_custom_emoji_id=CUSTOM_ID_LOUDSPEAKER
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text=tr("btn_check_sub", lang=lang),
                            callback_data=f"check_sub:{user.id}",
                            icon_custom_emoji_id=CUSTOM_ID_CHECK
                        )
                    ]
                ]
            )

            try:
                warn_msg = await bot.send_message(
                    chat_id=chat_id,
                    text=warning_text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                    receiver_user_id=user.id
                )
                asyncio.create_task(delete_message_delayed(bot, chat_id, warn_msg.message_id, 15))
            except Exception:
                pass
            return

    # Barcha shartlar bajarilgan bo'lsa — keshga kiritamiz va muteni yechamiz
    cache.add_allowed_user(chat_id, user.id)
