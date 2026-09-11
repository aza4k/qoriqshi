import aiosqlite
import os
import logging
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = None):
        if not db_path:
            from config import config
            self.db_path = config.DB_PATH
        else:
            self.db_path = db_path

    async def init_db(self):
        """Ma'lumotlar bazasi va jadvallarni yaratish"""
        dirname = os.path.dirname(self.db_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            # 100k guruhlar uchun SQLite optimallashtirish (WAL rejimi)
            await db.execute("PRAGMA journal_mode = WAL;")
            await db.execute("PRAGMA synchronous = NORMAL;")
            await db.execute("PRAGMA cache_size = 10000;")

            # Guruh sozlamalari jadvali
            await db.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    chat_id INTEGER PRIMARY KEY,
                    title TEXT,
                    required_count INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    del_service_msg INTEGER DEFAULT 1,
                    anticheat INTEGER DEFAULT 0,
                    channel_id TEXT DEFAULT '',
                    channel_username TEXT DEFAULT '',
                    channel_title TEXT DEFAULT '',
                    captcha INTEGER DEFAULT 1,
                    language TEXT DEFAULT 'qr',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Guruh a'zolari va ularning ballari jadvali
            await db.execute("""
                CREATE TABLE IF NOT EXISTS group_members (
                    chat_id INTEGER,
                    user_id INTEGER,
                    full_name TEXT,
                    username TEXT,
                    added_count INTEGER DEFAULT 0,
                    is_exempt INTEGER DEFAULT 0,
                    PRIMARY KEY (chat_id, user_id)
                )
            """)

            # Odam qo'shish tarixi (takroriy hisoblashni oldini olish uchun)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS referral_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    referrer_id INTEGER,
                    joined_user_id INTEGER,
                    joined_user_name TEXT DEFAULT '',
                    joined_user_username TEXT DEFAULT '',
                    is_left INTEGER DEFAULT 0,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(chat_id, joined_user_id)
                )
            """)

            # Foydalanuvchi sozlamalari (tanlagan tili)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY,
                    language TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Bot bilan muloqot qilgan barcha foydalanuvchilar (Admin panel va Rassilka uchun)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    full_name TEXT,
                    username TEXT,
                    language TEXT DEFAULT 'qr',
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 100k guruh uchun yuqori tezlikdagi indekslar
            await db.execute("CREATE INDEX IF NOT EXISTS idx_members_chat_user ON group_members(chat_id, user_id);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_ref_chat_joined ON referral_history(chat_id, joined_user_id);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_ref_chat_ref ON referral_history(chat_id, referrer_id);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);")
            await db.commit()

            # ── Migration: Mavjud bazaga yangi ustunlarni qo'shish ──
            migrations = [
                ("groups",           "anticheat INTEGER DEFAULT 0"),
                ("groups",           "channel_id TEXT DEFAULT ''"),
                ("groups",           "channel_username TEXT DEFAULT ''"),
                ("groups",           "channel_title TEXT DEFAULT ''"),
                ("groups",           "captcha INTEGER DEFAULT 1"),
                ("groups",           "language TEXT DEFAULT 'qr'"),
                ("groups",           "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
                ("users",            "language TEXT DEFAULT 'qr'"),
                ("users",            "is_active INTEGER DEFAULT 1"),
                ("users",            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
                ("referral_history", "joined_user_name TEXT DEFAULT ''"),
                ("referral_history", "joined_user_username TEXT DEFAULT ''"),
                ("referral_history", "is_left INTEGER DEFAULT 0"),
            ]

            for table, column_def in migrations:
                col_name = column_def.split()[0]
                try:
                    await db.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")
                    await db.commit()
                except Exception:
                    pass

            logger.info("Ma'lumotlar bazasi WAL va indekslar bilan optimallashtirildi.")



    async def get_or_create_group(self, chat_id: int, title: str = "") -> Dict[str, Any]:
        """Guruh ma'lumotlarini olish yoki yangisini yaratish"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM groups WHERE chat_id = ?", (chat_id,))
            row = await cursor.fetchone()
            if not row:
                await db.execute(
                    "INSERT INTO groups (chat_id, title, required_count, is_active, del_service_msg, language) VALUES (?, ?, 0, 1, 1, 'qr')",
                    (chat_id, title)
                )
                await db.commit()
                cursor = await db.execute("SELECT * FROM groups WHERE chat_id = ?", (chat_id,))
                row = await cursor.fetchone()
            else:
                if title and row["title"] != title:
                    await db.execute("UPDATE groups SET title = ? WHERE chat_id = ?", (title, chat_id))
                    await db.commit()
            res = dict(row)
            if not res.get("language"):
                res["language"] = "qr"
            return res

    async def set_group_limit(self, chat_id: int, limit: int, title: str = ""):
        """Guruh uchun majburiy a'zolar sonini o'rnatish"""
        await self.get_or_create_group(chat_id, title)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE groups SET required_count = ? WHERE chat_id = ?",
                (limit, chat_id)
            )
            await db.commit()

    async def toggle_group_active(self, chat_id: int, is_active: bool):
        """Guruhda bot faoliyatini yoqish/o'chirish"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE groups SET is_active = ? WHERE chat_id = ?",
                (1 if is_active else 0, chat_id)
            )
            await db.commit()

    async def set_group_channel(self, chat_id: int, channel_id: str, channel_username: str = "", channel_title: str = ""):
        """Guruh uchun majburiy obuna kanalini o'rnatish"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE groups SET channel_id = ?, channel_username = ?, channel_title = ? WHERE chat_id = ?",
                (str(channel_id), channel_username, channel_title, chat_id)
            )
            await db.commit()

    async def del_group_channel(self, chat_id: int):
        """Guruhdan majburiy kanalni o'chirish"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE groups SET channel_id = '', channel_username = '', channel_title = '' WHERE chat_id = ?",
                (chat_id,)
            )
            await db.commit()

    async def toggle_del_service_msg(self, chat_id: int, del_service_msg: bool):

        """Xizmat xabarlarini tozalashni yoqish/o'chirish"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE groups SET del_service_msg = ? WHERE chat_id = ?",
                (1 if del_service_msg else 0, chat_id)
            )
            await db.commit()

    async def toggle_captcha(self, chat_id: int, captcha: bool):
        """Yangi a'zolar uchun captchani yoqish/o'chirish"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE groups SET captcha = ? WHERE chat_id = ?",
                (1 if captcha else 0, chat_id)
            )
            await db.commit()

    async def toggle_anticheat(self, chat_id: int, anticheat: bool):

        """Chiqib ketganlar hisobdan ayirilsinmi yoqish/o'chirish"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE groups SET anticheat = ? WHERE chat_id = ?",
                (1 if anticheat else 0, chat_id)
            )
            await db.commit()

    async def get_or_create_member(self, chat_id: int, user_id: int, full_name: str = "", username: str = "") -> Dict[str, Any]:
        """A'zo ma'lumotlarini olish yoki yaratish"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM group_members WHERE chat_id = ? AND user_id = ?",
                (chat_id, user_id)
            )
            row = await cursor.fetchone()
            if not row:
                await db.execute(
                    "INSERT INTO group_members (chat_id, user_id, full_name, username, added_count, is_exempt) VALUES (?, ?, ?, ?, 0, 0)",
                    (chat_id, user_id, full_name, username)
                )
                await db.commit()
                cursor = await db.execute(
                    "SELECT * FROM group_members WHERE chat_id = ? AND user_id = ?",
                    (chat_id, user_id)
                )
                row = await cursor.fetchone()
            else:
                # Ism yoki username yangilangan bo'lsa yangilash
                if (full_name and row["full_name"] != full_name) or (username and row["username"] != username):
                    await db.execute(
                        "UPDATE group_members SET full_name = ?, username = ? WHERE chat_id = ? AND user_id = ?",
                        (full_name, username, chat_id, user_id)
                    )
                    await db.commit()
            return dict(row)

    async def add_referral(
        self,
        chat_id: int,
        referrer_id: int,
        joined_user_id: int,
        referrer_name: str = "",
        referrer_username: str = "",
        joined_user_name: str = "",
        joined_user_username: str = ""
    ) -> Tuple[bool, str, int]:
        """
        Guruhga yangi odam qo'shilganda hisobga olish.
        Qaytaradi: (success: bool, reason: str, current_count: int)
        reason: 'added_success' | 'already_exists_same_user' | 'already_exists_other' | 'error'
        """
        async with aiosqlite.connect(self.db_path) as db:
            # 1. Avval bu joined_user_id shu guruhda qo'shilganmi tekshiramiz
            cursor = await db.execute(
                "SELECT referrer_id FROM referral_history WHERE chat_id = ? AND joined_user_id = ?",
                (chat_id, joined_user_id)
            )
            exists = await cursor.fetchone()
            if exists:
                # Agar allaqachon qo'shilgan bo'lsa (A yana B ni qo'shsa yoki C B ni qo'shsa ham)
                cursor = await db.execute(
                    "SELECT added_count FROM group_members WHERE chat_id = ? AND user_id = ?",
                    (chat_id, referrer_id)
                )
                row = await cursor.fetchone()
                current_cnt = row[0] if row else 0
                if exists[0] == referrer_id:
                    return False, "already_exists_same_user", current_cnt
                else:
                    return False, "already_exists_other", current_cnt

            # 2. Yangi qo'shilgan deb tarixga yozamiz
            await db.execute("""
                INSERT INTO referral_history 
                (chat_id, referrer_id, joined_user_id, joined_user_name, joined_user_username, is_left)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (chat_id, referrer_id, joined_user_id, joined_user_name, joined_user_username))

            # 3. Foydalanuvchi ballini 1 taga oshiramiz
            await db.execute("""
                INSERT INTO group_members (chat_id, user_id, full_name, username, added_count, is_exempt)
                VALUES (?, ?, ?, ?, 1, 0)
                ON CONFLICT(chat_id, user_id) DO UPDATE SET
                    added_count = added_count + 1,
                    full_name = excluded.full_name,
                    username = excluded.username
            """, (chat_id, referrer_id, referrer_name, referrer_username))
            await db.commit()

            cursor = await db.execute(
                "SELECT added_count FROM group_members WHERE chat_id = ? AND user_id = ?",
                (chat_id, referrer_id)
            )
            row = await cursor.fetchone()
            return True, "added_success", (row[0] if row else 1)

    async def handle_member_left(self, chat_id: int, left_user_id: int) -> Tuple[bool, Optional[int], int]:
        """
        Guruhdan a'zo chiqib ketganda ishlaydi.
        Agar guruhda anticheat yoqilgan bo'lsa, taklif qiluvchining ballidan 1 ayiradi.
        Qaytaradi: (penalty_applied: bool, referrer_id: Optional[int], new_count: int)
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Guruh anticheat sozlamasini tekshiramiz
            cursor = await db.execute("SELECT anticheat FROM groups WHERE chat_id = ?", (chat_id,))
            group_row = await cursor.fetchone()
            anticheat = group_row[0] if group_row else 0

            # Bu chiqib ketgan odamni kim qo'shganini aniqlaymiz
            cursor = await db.execute(
                "SELECT referrer_id, is_left FROM referral_history WHERE chat_id = ? AND joined_user_id = ?",
                (chat_id, left_user_id)
            )
            ref_row = await cursor.fetchone()
            if not ref_row:
                return False, None, 0

            referrer_id, is_left = ref_row[0], ref_row[1]

            # referral_history da chiqib ketganini belgilab qo'yamiz
            await db.execute(
                "UPDATE referral_history SET is_left = 1 WHERE chat_id = ? AND joined_user_id = ?",
                (chat_id, left_user_id)
            )

            # Agar anticheat yoqilgan bo'lsa va oldin chiqmagan bo'lsa ballni kamaytiramiz
            if anticheat and is_left == 0:
                await db.execute(
                    "UPDATE group_members SET added_count = MAX(0, added_count - 1) WHERE chat_id = ? AND user_id = ?",
                    (chat_id, referrer_id)
                )
                await db.commit()
                cursor = await db.execute(
                    "SELECT added_count FROM group_members WHERE chat_id = ? AND user_id = ?",
                    (chat_id, referrer_id)
                )
                row = await cursor.fetchone()
                return True, referrer_id, (row[0] if row else 0)

            await db.commit()
            return False, referrer_id, 0

    async def get_user_referrals(self, chat_id: int, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Foydalanuvchi qo'shgan odamlar ro'yxati"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT joined_user_id, joined_user_name, joined_user_username, is_left, joined_at
                FROM referral_history
                WHERE chat_id = ? AND referrer_id = ?
                ORDER BY joined_at DESC LIMIT ?
            """, (chat_id, user_id, limit))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_user_all_groups_stats(self, user_id: int) -> List[Dict[str, Any]]:
        """Foydalanuvchining barcha guruhlardagi statistikasi"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT g.chat_id, g.title, g.required_count, m.added_count, m.is_exempt
                FROM group_members m
                JOIN groups g ON m.chat_id = g.chat_id
                WHERE m.user_id = ?
            """, (user_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_group_total_stats(self, chat_id: int) -> Dict[str, Any]:
        """Guruh umumiy statistikasi"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM group_members WHERE chat_id = ?", (chat_id,))
            total_members = (await cursor.fetchone())[0]

            cursor = await db.execute("SELECT COUNT(*) FROM referral_history WHERE chat_id = ?", (chat_id,))
            total_added = (await cursor.fetchone())[0]

            cursor = await db.execute("SELECT COUNT(*) FROM referral_history WHERE chat_id = ? AND is_left = 1", (chat_id,))
            total_left = (await cursor.fetchone())[0]

            return {
                "total_members": total_members,
                "total_added": total_added,
                "total_left": total_left
            }

    async def get_member_stats(self, chat_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Foydalanuvchi statistikasini olish"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM group_members WHERE chat_id = ? AND user_id = ?",
                (chat_id, user_id)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_top_members(self, chat_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Guruhda eng ko'p odam qo'shgan TOP a'zolar"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT full_name, username, added_count FROM group_members WHERE chat_id = ? AND added_count > 0 ORDER BY added_count DESC LIMIT ?",
                (chat_id, limit)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def set_exempt(self, chat_id: int, user_id: int, is_exempt: bool, full_name: str = "", username: str = ""):
        """Foydalanuvchini oq ro'yxatga kiritish yoki chiqarish"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO group_members (chat_id, user_id, full_name, username, added_count, is_exempt)
                VALUES (?, ?, ?, ?, 0, ?)
                ON CONFLICT(chat_id, user_id) DO UPDATE SET
                    is_exempt = excluded.is_exempt
            """, (chat_id, user_id, full_name, username, 1 if is_exempt else 0))
            await db.commit()

    async def reset_member(self, chat_id: int, user_id: int):
        """A'zoning hisoblagichini va referral tarixini nollash (qayta hisoblash imkoni paydo bo'ladi)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE group_members SET added_count = 0 WHERE chat_id = ? AND user_id = ?",
                (chat_id, user_id)
            )
            # Referral tarixini ham tozalaymiz — shunda bu user qaytadan odam qo'sha oladi
            await db.execute(
                "DELETE FROM referral_history WHERE chat_id = ? AND referrer_id = ?",
                (chat_id, user_id)
            )
            await db.commit()


    async def reset_group(self, chat_id: int):
        """Butun guruh statistikasini nollash"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE group_members SET added_count = 0 WHERE chat_id = ?", (chat_id,))
            await db.execute("DELETE FROM referral_history WHERE chat_id = ?", (chat_id,))
            await db.commit()

    async def get_user_language(self, user_id: int) -> Optional[str]:
        """Foydalanuvchining tanlagan tilini olish"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT language FROM user_settings WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            if row and row[0]:
                return row[0]
            return None

    async def set_user_language(self, user_id: int, lang: str):
        """Foydalanuvchi tilini saqlash"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO user_settings (user_id, language) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET language = ?",
                (user_id, lang, lang)
            )
            await db.commit()

    async def set_group_language(self, chat_id: int, lang: str, title: str = ""):
        """Guruh tilini saqlash"""
        await self.get_or_create_group(chat_id, title)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE groups SET language = ? WHERE chat_id = ?", (lang, chat_id))
            await db.commit()

    # ─── ADMIN PANEL VA RASSILKA METODLARI ───

    async def register_user(self, user_id: int, full_name: str = "", username: str = "", language: str = "qr"):
        """Foydalanuvchini bazaga qo'shish yoki ma'lumotlarini yangilash"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO users (user_id, full_name, username, language, is_active)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(user_id) DO UPDATE SET
                    full_name = excluded.full_name,
                    username = excluded.username,
                    is_active = 1
            """, (user_id, full_name, username, language))
            await db.commit()

    async def set_user_active_status(self, user_id: int, is_active: bool):
        """Foydalanuvchi botni bloklagan bo'lsa yoki aktiv bo'lsa yangilash"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET is_active = ? WHERE user_id = ?", (1 if is_active else 0, user_id))
            await db.commit()

    async def get_global_system_stats(self) -> Dict[str, Any]:
        """Tizimning global statistikasini hisoblash (Admin Panel uchun)"""
        async with aiosqlite.connect(self.db_path) as db:
            # Guruhlar soni
            cursor = await db.execute("SELECT COUNT(*), SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) FROM groups")
            total_groups, active_groups = await cursor.fetchone()
            total_groups = total_groups or 0
            active_groups = active_groups or 0
            inactive_groups = total_groups - active_groups

            # Foydalanuvchilar soni
            cursor = await db.execute("SELECT COUNT(*), SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) FROM users")
            total_users, active_users = await cursor.fetchone()
            total_users = total_users or 0
            active_users = active_users or 0

            # Jami taklif qilingan odamlar soni
            cursor = await db.execute("SELECT COUNT(*) FROM referral_history")
            total_referrals = (await cursor.fetchone())[0] or 0

            # Bugungi yangi guruhlar
            cursor = await db.execute("SELECT COUNT(*) FROM groups WHERE DATE(created_at) = DATE('now')")
            today_groups = (await cursor.fetchone())[0] or 0

            # Bugungi yangi userlar
            cursor = await db.execute("SELECT COUNT(*) FROM users WHERE DATE(created_at) = DATE('now')")
            today_users = (await cursor.fetchone())[0] or 0

            # DB fayl hajmi
            db_size_mb = 0.0
            if os.path.exists(self.db_path):
                db_size_mb = round(os.path.getsize(self.db_path) / (1024 * 1024), 2)

            return {
                "total_groups": total_groups,
                "active_groups": active_groups,
                "inactive_groups": inactive_groups,
                "total_users": total_users,
                "active_users": active_users,
                "total_referrals": total_referrals,
                "today_groups": today_groups,
                "today_users": today_users,
                "db_size_mb": db_size_mb,
            }

    async def get_all_user_ids(self) -> List[int]:
        """Barcha aktiv foydalanuvchilar ID ro'yxati (rassilka uchun)"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT user_id FROM users WHERE is_active = 1")
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def get_all_group_ids(self) -> List[int]:
        """Barcha aktiv guruhlar ID ro'yxati (rassilka uchun)"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT chat_id FROM groups WHERE is_active = 1")
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def get_recent_groups(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """Guruhlar ro'yxatini olish (pagination bilan)"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM groups ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def count_total_groups(self) -> int:
        """Guruhlar umumiy soni"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM groups")
            return (await cursor.fetchone())[0] or 0

    async def search_groups(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Guruh nomi yoki chat_id bo'yicha qidirish"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM groups WHERE title LIKE ? OR CAST(chat_id AS TEXT) LIKE ? LIMIT ?",
                (f"%{query}%", f"%{query}%", limit)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_group_by_id(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Guruh ma'lumotlarini chat_id orqali olish"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM groups WHERE chat_id = ?", (chat_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

db = Database()


