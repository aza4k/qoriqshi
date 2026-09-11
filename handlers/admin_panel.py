import asyncio
import os
import time
import logging
from typing import List, Optional

from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup,
    InlineKeyboardButton, FSInputFile
)
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError, TelegramBadRequest

from config import config
from database.db import db
from utils.cache import cache
from utils.i18n import clean_alert_text
from filters.chat_type import ChatTypeFilter

logger = logging.getLogger(__name__)

router = Router()

# Faqat shaxsiy chatda va bot egalari (config.ADMINS) uchun ishlaydi
class IsBotAdminFilter:
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user
        return bool(user and user.id in config.ADMINS)

router.message.filter(ChatTypeFilter("private"), IsBotAdminFilter())
router.callback_query.filter(ChatTypeFilter("private"), IsBotAdminFilter())


class BroadcastState(StatesGroup):
    target = State()              # "users" yoki "groups"
    waiting_for_message = State() # Admin xabar yuborishi kutilmoqda
    waiting_for_confirm = State() # Tasdiqlash tugmasi


def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Admin panel bosh menyusi tugmalari"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats"),
                InlineKeyboardButton(text="📢 Xabar tarqatish", callback_data="admin_broadcast_menu")
            ],
            [
                InlineKeyboardButton(text="🏢 Guruhlar", callback_data="admin_groups:0"),
                InlineKeyboardButton(text="💾 Baza yuklab olish", callback_data="admin_backup")
            ],
            [
                InlineKeyboardButton(text="🔄 Keshni tozalash", callback_data="admin_clear_cache")
            ],
            [
                InlineKeyboardButton(text="❌ Yopish", callback_data="admin_close")
            ]
        ]
    )


async def build_dashboard_text() -> str:
    """Global statistika dashboard matni"""
    stats = await db.get_global_system_stats()
    return (
        "👑 <b>Boshqaruv Paneli (Admin Panel)</b>\n\n"
        "📊 <b>Tizim statistikasi:</b>\n"
        f"👤 Jami foydalanuvchilar: <b>{stats['total_users']}</b> ta (Faol: {stats['active_users']})\n"
        f"👤 Bugun qo'shilganlar: <b>+{stats['today_users']}</b> ta\n\n"
        f"🏢 Jami guruhlar: <b>{stats['total_groups']}</b> ta (Faol: {stats['active_groups']})\n"
        f"🏢 Bugun ulangan guruhlar: <b>+{stats['today_groups']}</b> ta\n\n"
        f"🔗 Jami taklif qilingan a'zolar: <b>{stats['total_referrals']}</b> ta\n"
        f"💾 Ma'lumotlar bazasi hajmi: <b>{stats['db_size_mb']} MB</b>\n"
        "⚡ Tizim holati: <b>🟢 Faol / Barqaror</b>\n"
    )


@router.message(Command(commands=["admin", "panel"]))
async def cmd_admin_panel(message: Message, state: FSMContext):
    """Admin panelni ochish buyrug'i"""
    await state.clear()
    text = await build_dashboard_text()
    await message.answer(text, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "admin_open_panel")
async def cb_admin_open_panel(callback: CallbackQuery, state: FSMContext):
    """Admin panel bosh sahifasiga qaytish"""
    await state.clear()
    await callback.answer()
    text = await build_dashboard_text()
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    """Statistikani yangilash"""
    await callback.answer("Yangilanmoqda...")
    text = await build_dashboard_text()
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data == "admin_close")
async def cb_admin_close(callback: CallbackQuery, state: FSMContext):
    """Admin panelni yopish"""
    await state.clear()
    await callback.answer("Yopildi")
    try:
        await callback.message.delete()
    except Exception:
        pass


# ─── BAZA ZAXIRA NUSXASINI YUKLASH (BACKUP) ───

@router.callback_query(F.data == "admin_backup")
async def cb_admin_backup(callback: CallbackQuery):
    """Ma'lumotlar bazasini yuklab olish"""
    await callback.answer("Baza tayyorlanmoqda...")
    if not os.path.exists(config.DB_PATH):
        await callback.message.answer("❌ Ma'lumotlar bazasi fayli topilmadi!")
        return

    size_mb = round(os.path.getsize(config.DB_PATH) / (1024 * 1024), 2)
    filename = f"backup_{int(time.time())}.db"
    file = FSInputFile(config.DB_PATH, filename=filename)

    caption = (
        "💾 <b>Ma'lumotlar bazasi zaxira nusxasi</b>\n"
        f"📅 Sana: <code>{time.strftime('%Y-%m-%d %H:%M:%S')}</code>\n"
        f"📦 Hajmi: <b>{size_mb} MB</b>"
    )
    await callback.message.answer_document(file, caption=caption, parse_mode="HTML")


# ─── KESHNI TOZALASH ───

@router.callback_query(F.data == "admin_clear_cache")
async def cb_admin_clear_cache(callback: CallbackQuery):
    """Operativ xotiradagi barcha keshni tozalash"""
    cache.clear_all()
    await callback.answer(clean_alert_text("✅ Tizim keshi muvaffaqiyatli tozalandi!"), show_alert=True)


# ─── GURUHLAR BOSHQARUVI ───

@router.callback_query(F.data.startswith("admin_groups:"))
async def cb_admin_groups_list(callback: CallbackQuery):
    """Guruhlar ro'yxatini ko'rish (pagination)"""
    await callback.answer()
    offset = int(callback.data.split(":")[1])
    limit = 6

    total = await db.count_total_groups()
    groups = await db.get_recent_groups(limit=limit, offset=offset)

    if not groups:
        text = "🏢 <b>Hozircha hech qanday guruh mavjud emas.</b>"
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_open_panel")]]
        )
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        return

    text = f"🏢 <b>Guruhlar ro'yxati (Jami: {total} ta):</b>\n\n"
    buttons = []

    for g in groups:
        title = g.get("title") or "Nomsiz guruh"
        cid = g.get("chat_id")
        is_active = "🟢" if g.get("is_active") else "🔴"
        req = g.get("required_count", 0)
        buttons.append([
            InlineKeyboardButton(
                text=f"{is_active} {title[:22]} (limit: {req})",
                callback_data=f"admin_grp_view:{cid}"
            )
        ])

    # Pagination tugmalari
    nav_buttons = []
    if offset > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"admin_groups:{max(0, offset - limit)}"))
    if offset + limit < total:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"admin_groups:{offset + limit}"))

    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([InlineKeyboardButton(text="⬅️ Admin Panelga qaytish", callback_data="admin_open_panel")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("admin_grp_view:"))
async def cb_admin_group_view(callback: CallbackQuery):
    """Tanlangan guruh haqida batafsil ma'lumot"""
    await callback.answer()
    chat_id = int(callback.data.split(":")[1])
    grp = await db.get_group_by_id(chat_id)

    if not grp:
        await callback.answer("Guruh topilmadi!", show_alert=True)
        return

    stats = await db.get_group_total_stats(chat_id)
    title = grp.get("title") or "Nomsiz guruh"
    status_str = "🟢 Faol" if grp.get("is_active") else "🔴 Nofaol"
    channel_str = grp.get("channel_username") or grp.get("channel_title") or grp.get("channel_id") or "Ulanmagan"

    text = (
        f"🏢 <b>Guruh ma'lumotlari:</b>\n\n"
        f"🏷 Nomi: <b>{title}</b>\n"
        f"🆔 ID: <code>{chat_id}</code>\n"
        f"⚡ Holati: <b>{status_str}</b>\n"
        f"🎯 Belgilangan limit: <b>{grp.get('required_count', 0)}</b> ta\n"
        f"📢 Majburiy kanal: <b>{channel_str}</b>\n"
        f"🌐 Tili: <b>{grp.get('language', 'qr').upper()}</b>\n"
        f"🛡 Anti-cheat: <b>{'Yoqilgan' if grp.get('anticheat') else 'O\'chirilgan'}</b>\n"
        f"🤖 Captcha: <b>{'Yoqilgan' if grp.get('captcha') else 'O\'chirilgan'}</b>\n\n"
        f"📊 <b>Guruh a'zolari:</b>\n"
        f"• Bazadagi a'zolar: <b>{stats['total_members']}</b> ta\n"
        f"• Qo'shilgan takliflar: <b>{stats['total_added']}</b> ta\n"
        f"• Chiqib ketganlar: <b>{stats['total_left']}</b> ta"
    )

    toggle_text = "🔴 Nofaol qilish" if grp.get("is_active") else "🟢 Faollashtirish"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=toggle_text, callback_data=f"admin_grp_toggle:{chat_id}"),
                InlineKeyboardButton(text="🚪 Guruhdan chiqish", callback_data=f"admin_grp_leave:{chat_id}")
            ],
            [
                InlineKeyboardButton(text="⬅️ Guruhlar ro'yxatiga qaytish", callback_data="admin_groups:0")
            ]
        ]
    )
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("admin_grp_toggle:"))
async def cb_admin_group_toggle(callback: CallbackQuery):
    """Guruhni faol/nofaol qilish"""
    chat_id = int(callback.data.split(":")[1])
    grp = await db.get_group_by_id(chat_id)
    if not grp:
        await callback.answer("Guruh topilmadi!", show_alert=True)
        return

    new_status = not bool(grp.get("is_active"))
    await db.toggle_group_active(chat_id, new_status)
    cache.invalidate_group_settings(chat_id)

    status_msg = "faollashtirildi" if new_status else "nofaol qilindi"
    await callback.answer(f"Guruh {status_msg}!", show_alert=True)
    await cb_admin_group_view(callback)


@router.callback_query(F.data.startswith("admin_grp_leave:"))
async def cb_admin_group_leave(callback: CallbackQuery, bot: Bot):
    """Botning guruhni tark etishi"""
    chat_id = int(callback.data.split(":")[1])
    try:
        await bot.leave_chat(chat_id)
        await db.toggle_group_active(chat_id, False)
        cache.invalidate_group_settings(chat_id)
        await callback.answer("✅ Bot guruhdan chiqdi!", show_alert=True)
    except Exception as e:
        logger.error(f"Error leaving chat {chat_id}: {e}")
        await callback.answer(f"Xatolik yuz berdi: {e}", show_alert=True)

    await cb_admin_groups_list(callback)


# ─── XABAR TARQATISH (RASSILKA) ───

@router.callback_query(F.data == "admin_broadcast_menu")
async def cb_admin_broadcast_menu(callback: CallbackQuery, state: FSMContext):
    """Xabar tarqatish yo'nalishini tanlash menyusi"""
    await state.clear()
    await callback.answer()

    total_users = len(await db.get_all_user_ids())
    total_groups = len(await db.get_all_group_ids())

    text = (
        "📢 <b>Xabar tarqatish (Rassilka) bo'limi</b>\n\n"
        "Xabarni kimlarga yubormoqchisiz?\n\n"
        f"👤 <b>Foydalanuvchilarga</b> — jami ~{total_users} ta faol foydalanuvchi\n"
        f"🏢 <b>Guruhlarga</b> — jami ~{total_groups} ta faol guruh\n\n"
        "<i>Kerakli bo'limni tanlang:</i>"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"👤 Foydalanuvchilarga ({total_users})", callback_data="admin_bc_target:users")
            ],
            [
                InlineKeyboardButton(text=f"🏢 Guruhlarga ({total_groups})", callback_data="admin_bc_target:groups")
            ],
            [
                InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_open_panel")
            ]
        ]
    )
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("admin_bc_target:"))
async def cb_admin_bc_select_target(callback: CallbackQuery, state: FSMContext):
    """Target tanlangandan keyin xabar qabul qilish bosqichi"""
    await callback.answer()
    target = callback.data.split(":")[1] # "users" yoki "groups"
    await state.update_data(target=target)
    await state.set_state(BroadcastState.waiting_for_message)

    target_name = "foydalanuvchilarga (lichkaga)" if target == "users" else "barcha guruhlarga"

    text = (
        f"📢 <b>Xabar yuborish: {target_name}</b>\n\n"
        "Endi yubormoqchi bo'lgan xabaringizni yuboring.\n"
        "<i>(Xabar matn, rasm, video, audio, hujjat yoki istalgan kanaldan forward xabar bo'lishi mumkin)</i>"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_bc_cancel")]
        ]
    )
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "admin_bc_cancel")
async def cb_admin_bc_cancel(callback: CallbackQuery, state: FSMContext):
    """Xabar tarqatishni bekor qilish"""
    await state.clear()
    await callback.answer("Bekor qilindi")
    text = await build_dashboard_text()
    await callback.message.edit_text(
        "❌ <b>Xabar tarqatish bekor qilindi.</b>\n\n" + text,
        reply_markup=get_admin_main_keyboard(),
        parse_mode="HTML"
    )


@router.message(BroadcastState.waiting_for_message)
async def process_broadcast_message(message: Message, state: FSMContext, bot: Bot):
    """Admin yuborgan xabarni qabul qilish va tasdiqlash uchun ko'rsatish"""
    data = await state.get_data()
    target = data.get("target", "users")
    target_name = "Foydalanuvchilarga (Lichka)" if target == "users" else "Guruhlarga"

    await state.update_data(
        from_chat_id=message.chat.id,
        message_id=message.message_id
    )
    await state.set_state(BroadcastState.waiting_for_confirm)

    count = len(await db.get_all_user_ids() if target == "users" else await db.get_all_group_ids())

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, yuborishni boshlash", callback_data="admin_bc_start"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_bc_cancel")
            ]
        ]
    )

    await message.reply(
        f"👆 <b>Xabaringiz yuqorida qabul qilindi.</b>\n\n"
        f"🎯 <b>Nishon:</b> {target_name}\n"
        f"👥 <b>Qabul qiluvchilar soni:</b> ~{count} ta\n\n"
        "Rassilkani boshlashni tasdiqlaysizmi?",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_bc_start")
async def cb_admin_bc_start(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Xabar tarqatish jarayonini xavfsiz boshlash"""
    data = await state.get_data()
    await state.clear()
    await callback.answer()

    target = data.get("target", "users")
    from_chat_id = data.get("from_chat_id")
    message_id = data.get("message_id")

    if not from_chat_id or not message_id:
        await callback.message.edit_text("❌ Xabar ma'lumotlari yo'qolgan. Qaytadan urinib ko'ring.")
        return

    ids = await db.get_all_user_ids() if target == "users" else await db.get_all_group_ids()
    total = len(ids)

    if total == 0:
        await callback.message.edit_text("❌ Yuborish uchun faol qabul qiluvchilar topilmadi.")
        return

    target_name = "foydalanuvchilarga" if target == "users" else "guruhlarga"
    status_msg = await callback.message.answer(
        f"⏳ <b>Xabar tarqatilmoqda ({target_name})...</b>\n\n"
        f"📊 Jami: <b>{total}</b> ta\n"
        "✅ Yetkazildi: <b>0</b>\n"
        "🚫 Bloklagan/Mavjud emas: <b>0</b>\n"
        "❌ Xatolik: <b>0</b>",
        parse_mode="HTML"
    )

    success = 0
    blocked = 0
    failed = 0
    start_time = time.time()
    last_update_time = time.time()

    for idx, target_id in enumerate(ids):
        try:
            await bot.copy_message(
                chat_id=target_id,
                from_chat_id=from_chat_id,
                message_id=message_id
            )
            success += 1
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await bot.copy_message(
                    chat_id=target_id,
                    from_chat_id=from_chat_id,
                    message_id=message_id
                )
                success += 1
            except Exception:
                failed += 1
        except TelegramForbiddenError:
            blocked += 1
            if target == "users":
                await db.set_user_active_status(target_id, False)
        except TelegramBadRequest as e:
            failed += 1
            if target == "groups" and ("chat not found" in str(e).lower() or "bot was kicked" in str(e).lower()):
                await db.toggle_group_active(target_id, False)
        except Exception as e:
            failed += 1
            logger.warning(f"Broadcast to {target_id} failed: {e}")

        # Telegram Flood cheklovlaridan saqlanish (25 xabar/sekund)
        await asyncio.sleep(0.04)

        # Har 25 ta xabarda yoki 3 sekundda statusni yangilaymiz
        if (idx + 1) % 25 == 0 or (time.time() - last_update_time) > 3.0:
            last_update_time = time.time()
            try:
                await status_msg.edit_text(
                    f"⏳ <b>Xabar tarqatilmoqda ({target_name})...</b>\n\n"
                    f"📊 Progress: <b>{idx + 1}/{total}</b> ({int((idx + 1) / total * 100)}%)\n"
                    f"✅ Yetkazildi: <b>{success}</b>\n"
                    f"🚫 Bloklagan/Mavjud emas: <b>{blocked}</b>\n"
                    f"❌ Xatolik: <b>{failed}</b>",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    elapsed = round(time.time() - start_time, 1)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👑 Admin Panelga qaytish", callback_data="admin_open_panel")]
        ]
    )

    await status_msg.edit_text(
        f"✅ <b>Xabar tarqatish muvaffaqiyatli yakunlandi!</b>\n\n"
        f"🎯 Nishon: <b>{target_name.capitalize()}</b>\n"
        f"📊 Jami nishon: <b>{total}</b> ta\n"
        f"✅ Yetkazildi: <b>{success}</b> ta\n"
        f"🚫 Bloklagan/Mavjud emas: <b>{blocked}</b> ta\n"
        f"❌ Xatoliklar: <b>{failed}</b> ta\n"
        f"⏱ Sarflangan vaqt: <b>{elapsed} soniya</b>",
        reply_markup=kb,
        parse_mode="HTML"
    )
