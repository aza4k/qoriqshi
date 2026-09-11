import aiosqlite
import os
import json
import logging
from typing import Optional, List, Dict, Any, Tuple

from config import config

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = None, db_url: str = None):
        self.db_path = db_path or config.DB_PATH
        self.db_url = db_url or config.DATABASE_URL
        self.is_postgres = bool(self.db_url)
        self.pool = None

    def _to_pg(self, sql: str) -> str:
        """SQLite '?' parametrlarini PostgreSQL '$1, $2...' parametrlariga aylantirish"""
        parts = sql.split('?')
        if len(parts) == 1:
            return sql
        res = []
        for i, part in enumerate(parts[:-1]):
            res.append(part)
            res.append(f"${i + 1}")
        res.append(parts[-1])
        return "".join(res)

    async def init_db(self):
        """Ma'lumotlar bazasi va jadvallarni yaratish"""
        if self.is_postgres:
            try:
                import asyncpg
                logger.info("PostgreSQL (DATABASE_URL) aniqlandi. asyncpg connection pool yaratilmoqda...")
                self.pool = await asyncpg.create_pool(
                    dsn=self.db_url,
                    min_size=2,
                    max_size=20,
                    command_timeout=60
                )
                await self._init_postgres()
                return
            except Exception as e:
                logger.error(f"PostgreSQL ulanishida xatolik: {e}. SQLite rejimiga o'tilmoqda.")
                self.is_postgres = False

        # SQLite fallback
        await self._init_sqlite()

    async def _init_postgres(self):
        """PostgreSQL sxemasi va indekslarini yaratish"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    chat_id BIGINT PRIMARY KEY,
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
                );

                CREATE TABLE IF NOT EXISTS group_members (
                    chat_id BIGINT,
                    user_id BIGINT,
                    full_name TEXT,
                    username TEXT,
                    added_count INTEGER DEFAULT 0,
                    is_exempt INTEGER DEFAULT 0,
                    PRIMARY KEY (chat_id, user_id)
                );

                CREATE TABLE IF NOT EXISTS referral_history (
                    id BIGSERIAL PRIMARY KEY,
                    chat_id BIGINT,
                    referrer_id BIGINT,
                    joined_user_id BIGINT,
                    joined_user_name TEXT DEFAULT '',
                    joined_user_username TEXT DEFAULT '',
                    is_left INTEGER DEFAULT 0,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(chat_id, joined_user_id)
                );

                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id BIGINT PRIMARY KEY,
                    language TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    full_name TEXT,
                    username TEXT,
                    language TEXT DEFAULT 'qr',
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_members_chat_user ON group_members(chat_id, user_id);
                CREATE INDEX IF NOT EXISTS idx_ref_chat_joined ON referral_history(chat_id, joined_user_id);
                CREATE INDEX IF NOT EXISTS idx_ref_chat_ref ON referral_history(chat_id, referrer_id);
                CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);
            """)
        logger.info("PostgreSQL sxemasi va indekslari muvaffaqiyatli ishga tushirildi.")

    async def _init_sqlite(self):
        """SQLite sxemasi, WAL rejimi va indekslarni yaratish"""
        dirname = os.path.dirname(self.db_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode = WAL;")
            await db.execute("PRAGMA synchronous = NORMAL;")
            await db.execute("PRAGMA cache_size = 10000;")

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

            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY,
                    language TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

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

            await db.execute("CREATE INDEX IF NOT EXISTS idx_members_chat_user ON group_members(chat_id, user_id);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_ref_chat_joined ON referral_history(chat_id, joined_user_id);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_ref_chat_ref ON referral_history(chat_id, referrer_id);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);")
            await db.commit()

            # Migrations for SQLite
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

            logger.info("SQLite ma'lumotlar bazasi WAL va indekslar bilan ishga tushirildi.")

    # ─── UNIVERSAL SQL QUERY HELPERS ───

    async def execute(self, sql: str, *args):
        """Ma'lumot yozish / yangilash / o'chirish so'rovi"""
        if self.is_postgres:
            sql_pg = self._to_pg(sql)
            return await self.pool.execute(sql_pg, *args)
        else:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(sql, args)
                await db.commit()

    async def fetchone(self, sql: str, *args) -> Optional[Dict[str, Any]]:
        """Bitta qatorni dict formatida olish"""
        if self.is_postgres:
            sql_pg = self._to_pg(sql)
            row = await self.pool.fetchrow(sql_pg, *args)
            return dict(row) if row else None
        else:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(sql, args)
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def fetchall(self, sql: str, *args) -> List[Dict[str, Any]]:
        """Barcha qatorlarni dict ro'yxati formatida olish"""
        if self.is_postgres:
            sql_pg = self._to_pg(sql)
            rows = await self.pool.fetch(sql_pg, *args)
            return [dict(row) for row in rows]
        else:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(sql, args)
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def fetchval(self, sql: str, *args) -> Any:
        """Bitta qiymat (masalan COUNT(*)) ni olish"""
        if self.is_postgres:
            sql_pg = self._to_pg(sql)
            return await self.pool.fetchval(sql_pg, *args)
        else:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(sql, args)
                row = await cursor.fetchone()
                return row[0] if row else None

    # ─── GURUH SOZLAMALARI VA BOSHQARUVI ───

    async def get_or_create_group(self, chat_id: int, title: str = "") -> Dict[str, Any]:
        """Guruh ma'lumotlarini olish yoki yangisini yaratish"""
        row = await self.fetchone("SELECT * FROM groups WHERE chat_id = ?", chat_id)
        if not row:
            await self.execute(
                "INSERT INTO groups (chat_id, title, required_count, is_active, del_service_msg, language) VALUES (?, ?, 0, 1, 1, 'qr')",
                chat_id, title
            )
            row = await self.fetchone("SELECT * FROM groups WHERE chat_id = ?", chat_id)
        elif title and row["title"] != title:
            await self.execute("UPDATE groups SET title = ? WHERE chat_id = ?", title, chat_id)
            row["title"] = title
        res = dict(row) if row else {}
        if not res.get("language"):
            res["language"] = "qr"
        return res

    async def set_group_limit(self, chat_id: int, limit: int, title: str = ""):
        """Guruh uchun majburiy a'zolar sonini o'rnatish"""
        await self.get_or_create_group(chat_id, title)
        await self.execute("UPDATE groups SET required_count = ? WHERE chat_id = ?", limit, chat_id)

    async def toggle_group_active(self, chat_id: int, is_active: bool):
        """Guruhda bot faoliyatini yoqish/o'chirish"""
        await self.execute("UPDATE groups SET is_active = ? WHERE chat_id = ?", 1 if is_active else 0, chat_id)

    async def set_group_channel(self, chat_id: int, channel_id: str, channel_username: str = "", channel_title: str = ""):
        """Guruh uchun majburiy obuna kanalini o'rnatish"""
        await self.execute(
            "UPDATE groups SET channel_id = ?, channel_username = ?, channel_title = ? WHERE chat_id = ?",
            str(channel_id), channel_username, channel_title, chat_id
        )

    async def del_group_channel(self, chat_id: int):
        """Guruhdan majburiy kanalni o'chirish"""
        await self.execute(
            "UPDATE groups SET channel_id = '', channel_username = '', channel_title = '' WHERE chat_id = ?",
            chat_id
        )

    async def toggle_del_service_msg(self, chat_id: int, del_service_msg: bool):
        """Xizmat xabarlarini tozalashni yoqish/o'chirish"""
        await self.execute("UPDATE groups SET del_service_msg = ? WHERE chat_id = ?", 1 if del_service_msg else 0, chat_id)

    async def toggle_captcha(self, chat_id: int, captcha: bool):
        """Yangi a'zolar uchun captchani yoqish/o'chirish"""
        await self.execute("UPDATE groups SET captcha = ? WHERE chat_id = ?", 1 if captcha else 0, chat_id)

    async def toggle_anticheat(self, chat_id: int, anticheat: bool):
        """Chiqib ketganlar hisobdan ayirilsinmi yoqish/o'chirish"""
        await self.execute("UPDATE groups SET anticheat = ? WHERE chat_id = ?", 1 if anticheat else 0, chat_id)

    async def get_or_create_member(self, chat_id: int, user_id: int, full_name: str = "", username: str = "") -> Dict[str, Any]:
        """A'zo ma'lumotlarini olish yoki yaratish"""
        row = await self.fetchone("SELECT * FROM group_members WHERE chat_id = ? AND user_id = ?", chat_id, user_id)
        if not row:
            await self.execute(
                "INSERT INTO group_members (chat_id, user_id, full_name, username, added_count, is_exempt) VALUES (?, ?, ?, ?, 0, 0)",
                chat_id, user_id, full_name, username
            )
            row = await self.fetchone("SELECT * FROM group_members WHERE chat_id = ? AND user_id = ?", chat_id, user_id)
        elif (full_name and row["full_name"] != full_name) or (username and row["username"] != username):
            await self.execute(
                "UPDATE group_members SET full_name = ?, username = ? WHERE chat_id = ? AND user_id = ?",
                full_name, username, chat_id, user_id
            )
            row["full_name"] = full_name
            row["username"] = username
        return dict(row) if row else {}

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
        """
        # 1. Avval bu joined_user_id shu guruhda oldin qo'shilganmi tekshiramiz
        exists = await self.fetchone(
            "SELECT referrer_id FROM referral_history WHERE chat_id = ? AND joined_user_id = ?",
            chat_id, joined_user_id
        )
        if exists:
            current_cnt = (await self.fetchval(
                "SELECT added_count FROM group_members WHERE chat_id = ? AND user_id = ?",
                chat_id, referrer_id
            )) or 0
            if exists["referrer_id"] == referrer_id:
                return False, "already_exists_same_user", current_cnt
            else:
                return False, "already_exists_other", current_cnt

        # 2. Yangi qo'shilgan deb tarixga yozamiz
        await self.execute("""
            INSERT INTO referral_history 
            (chat_id, referrer_id, joined_user_id, joined_user_name, joined_user_username, is_left)
            VALUES (?, ?, ?, ?, ?, 0)
        """, chat_id, referrer_id, joined_user_id, joined_user_name, joined_user_username)

        # 3. Foydalanuvchi ballini 1 taga oshiramiz (UPSERT ANSI SQL)
        await self.execute("""
            INSERT INTO group_members (chat_id, user_id, full_name, username, added_count, is_exempt)
            VALUES (?, ?, ?, ?, 1, 0)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET
                added_count = group_members.added_count + 1,
                full_name = excluded.full_name,
                username = excluded.username
        """, chat_id, referrer_id, referrer_name, referrer_username)

        new_cnt = (await self.fetchval(
            "SELECT added_count FROM group_members WHERE chat_id = ? AND user_id = ?",
            chat_id, referrer_id
        )) or 1
        return True, "added_success", new_cnt

    async def handle_member_left(self, chat_id: int, left_user_id: int) -> Tuple[bool, Optional[int], int]:
        """Guruhdan a'zo chiqib ketganda anticheat orqali ball ayirish"""
        anticheat = (await self.fetchval("SELECT anticheat FROM groups WHERE chat_id = ?", chat_id)) or 0
        ref_row = await self.fetchone(
            "SELECT referrer_id, is_left FROM referral_history WHERE chat_id = ? AND joined_user_id = ?",
            chat_id, left_user_id
        )
        if not ref_row:
            return False, None, 0

        referrer_id, is_left = ref_row["referrer_id"], ref_row["is_left"]
        await self.execute(
            "UPDATE referral_history SET is_left = 1 WHERE chat_id = ? AND joined_user_id = ?",
            chat_id, left_user_id
        )

        # ANSI SQL: CASE WHEN added_count > 0 THEN added_count - 1 ELSE 0 END (har ikki DBda bir xil ishlaydi)
        if anticheat and is_left == 0:
            await self.execute(
                "UPDATE group_members SET added_count = CASE WHEN added_count > 0 THEN added_count - 1 ELSE 0 END WHERE chat_id = ? AND user_id = ?",
                chat_id, referrer_id
            )
            new_cnt = (await self.fetchval(
                "SELECT added_count FROM group_members WHERE chat_id = ? AND user_id = ?",
                chat_id, referrer_id
            )) or 0
            return True, referrer_id, new_cnt

        return False, referrer_id, 0

    async def get_member_referral_history(self, chat_id: int, user_id: int, limit: int = 15) -> List[Dict[str, Any]]:
        """A'zo tomonidan qo'shilgan oxirgi a'zolar ro'yxati"""
        return await self.fetchall("""
            SELECT joined_user_id, joined_user_name, joined_user_username, is_left, joined_at
            FROM referral_history
            WHERE chat_id = ? AND referrer_id = ?
            ORDER BY joined_at DESC LIMIT ?
        """, chat_id, user_id, limit)

    async def get_user_all_groups_stats(self, user_id: int) -> List[Dict[str, Any]]:
        """Foydalanuvchining barcha guruhlardagi statistikasi"""
        return await self.fetchall("""
            SELECT g.chat_id, g.title, g.required_count, m.added_count, m.is_exempt
            FROM group_members m
            JOIN groups g ON m.chat_id = g.chat_id
            WHERE m.user_id = ?
        """, user_id)

    async def get_group_total_stats(self, chat_id: int) -> Dict[str, Any]:
        """Guruh umumiy statistikasi"""
        total_members = (await self.fetchval("SELECT COUNT(*) FROM group_members WHERE chat_id = ?", chat_id)) or 0
        total_added = (await self.fetchval("SELECT COUNT(*) FROM referral_history WHERE chat_id = ?", chat_id)) or 0
        total_left = (await self.fetchval("SELECT COUNT(*) FROM referral_history WHERE chat_id = ? AND is_left = 1", chat_id)) or 0

        return {
            "total_members": total_members,
            "total_added": total_added,
            "total_left": total_left
        }

    async def get_member_stats(self, chat_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Foydalanuvchi statistikasini olish"""
        return await self.fetchone("SELECT * FROM group_members WHERE chat_id = ? AND user_id = ?", chat_id, user_id)

    async def get_top_members(self, chat_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Guruhda eng ko'p odam qo'shgan TOP a'zolar"""
        return await self.fetchall(
            "SELECT full_name, username, added_count FROM group_members WHERE chat_id = ? AND added_count > 0 ORDER BY added_count DESC LIMIT ?",
            chat_id, limit
        )

    async def set_exempt(self, chat_id: int, user_id: int, is_exempt: bool, full_name: str = "", username: str = ""):
        """Foydalanuvchini oq ro'yxatga kiritish yoki chiqarish"""
        await self.execute("""
            INSERT INTO group_members (chat_id, user_id, full_name, username, added_count, is_exempt)
            VALUES (?, ?, ?, ?, 0, ?)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET
                is_exempt = excluded.is_exempt
        """, chat_id, user_id, full_name, username, 1 if is_exempt else 0)

    async def reset_member(self, chat_id: int, user_id: int):
        """A'zoning hisoblagichini va referral tarixini nollash"""
        await self.execute("UPDATE group_members SET added_count = 0 WHERE chat_id = ? AND user_id = ?", chat_id, user_id)
        await self.execute("DELETE FROM referral_history WHERE chat_id = ? AND referrer_id = ?", chat_id, user_id)

    async def reset_group(self, chat_id: int):
        """Butun guruh statistikasini nollash"""
        await self.execute("UPDATE group_members SET added_count = 0 WHERE chat_id = ?", chat_id)
        await self.execute("DELETE FROM referral_history WHERE chat_id = ?", chat_id)

    async def get_user_language(self, user_id: int) -> Optional[str]:
        """Foydalanuvchining tanlagan tilini olish"""
        return await self.fetchval("SELECT language FROM user_settings WHERE user_id = ?", user_id)

    async def set_user_language(self, user_id: int, lang: str):
        """Foydalanuvchi tilini saqlash"""
        await self.execute("""
            INSERT INTO user_settings (user_id, language) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET language = excluded.language
        """, user_id, lang)

    async def set_group_language(self, chat_id: int, lang: str, title: str = ""):
        """Guruh tilini saqlash"""
        await self.get_or_create_group(chat_id, title)
        await self.execute("UPDATE groups SET language = ? WHERE chat_id = ?", lang, chat_id)

    # ─── ADMIN PANEL VA RASSILKA METODLARI ───

    async def register_user(self, user_id: int, full_name: str = "", username: str = "", language: str = "qr"):
        """Foydalanuvchini bazaga qo'shish yoki ma'lumotlarini yangilash"""
        await self.execute("""
            INSERT INTO users (user_id, full_name, username, language, is_active)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(user_id) DO UPDATE SET
                full_name = excluded.full_name,
                username = excluded.username,
                is_active = 1
        """, user_id, full_name, username, language)

    async def set_user_active_status(self, user_id: int, is_active: bool):
        """Foydalanuvchi botni bloklagan bo'lsa yoki aktiv bo'lsa yangilash"""
        await self.execute("UPDATE users SET is_active = ? WHERE user_id = ?", 1 if is_active else 0, user_id)

    async def get_global_system_stats(self) -> Dict[str, Any]:
        """Tizimning global statistikasini hisoblash (Admin Panel uchun)"""
        row_g = await self.fetchone("SELECT COUNT(*) AS total, COALESCE(SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END), 0) AS active FROM groups")
        total_groups = int(row_g["total"]) if row_g and row_g.get("total") else 0
        active_groups = int(row_g["active"]) if row_g and row_g.get("active") else 0
        inactive_groups = total_groups - active_groups

        row_u = await self.fetchone("SELECT COUNT(*) AS total, COALESCE(SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END), 0) AS active FROM users")
        total_users = int(row_u["total"]) if row_u and row_u.get("total") else 0
        active_users = int(row_u["active"]) if row_u and row_u.get("active") else 0

        total_referrals = int((await self.fetchval("SELECT COUNT(*) FROM referral_history")) or 0)

        if self.is_postgres:
            today_groups = int((await self.fetchval("SELECT COUNT(*) FROM groups WHERE DATE(created_at) = CURRENT_DATE")) or 0)
            today_users = int((await self.fetchval("SELECT COUNT(*) FROM users WHERE DATE(created_at) = CURRENT_DATE")) or 0)
            db_size_mb = 0.0
            try:
                size_bytes = await self.fetchval("SELECT pg_database_size(current_database())")
                if size_bytes:
                    db_size_mb = round(size_bytes / (1024 * 1024), 2)
            except Exception:
                pass
        else:
            today_groups = int((await self.fetchval("SELECT COUNT(*) FROM groups WHERE DATE(created_at) = DATE('now')")) or 0)
            today_users = int((await self.fetchval("SELECT COUNT(*) FROM users WHERE DATE(created_at) = DATE('now')")) or 0)
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
            "engine": "PostgreSQL" if self.is_postgres else "SQLite"
        }

    async def get_all_user_ids(self) -> List[int]:
        """Barcha aktiv foydalanuvchilar ID ro'yxati (rassilka uchun)"""
        rows = await self.fetchall("SELECT user_id FROM users WHERE is_active = 1")
        return [r["user_id"] for r in rows]

    async def get_all_group_ids(self) -> List[int]:
        """Barcha aktiv guruhlar ID ro'yxati (rassilka uchun)"""
        rows = await self.fetchall("SELECT chat_id FROM groups WHERE is_active = 1")
        return [r["chat_id"] for r in rows]

    async def get_recent_groups(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """Guruhlar ro'yxatini olish (pagination bilan)"""
        return await self.fetchall("SELECT * FROM groups ORDER BY created_at DESC LIMIT ? OFFSET ?", limit, offset)

    async def count_total_groups(self) -> int:
        """Guruhlar umumiy soni"""
        return int((await self.fetchval("SELECT COUNT(*) FROM groups")) or 0)

    async def search_groups(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Guruh nomi yoki chat_id bo'yicha qidirish"""
        return await self.fetchall(
            "SELECT * FROM groups WHERE title LIKE ? OR CAST(chat_id AS TEXT) LIKE ? LIMIT ?",
            f"%{query}%", f"%{query}%", limit
        )

    async def get_group_by_id(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Guruh ma'lumotlarini chat_id orqali olish"""
        return await self.fetchone("SELECT * FROM groups WHERE chat_id = ?", chat_id)

    async def export_database_dump(self) -> str:
        """PostgreSQL yoki SQLite ma'lumotlarini JSON formatida zaxira nusxaga eksport qilish"""
        data = {
            "engine": "PostgreSQL" if self.is_postgres else "SQLite",
            "groups": await self.fetchall("SELECT * FROM groups"),
            "users": await self.fetchall("SELECT * FROM users"),
            "group_members": await self.fetchall("SELECT * FROM group_members"),
            "referral_history": await self.fetchall("SELECT * FROM referral_history"),
            "user_settings": await self.fetchall("SELECT * FROM user_settings")
        }
        # Sana va vaqtlarni string formatga o'tkazamiz
        dump_path = os.path.join(os.path.dirname(self.db_path) or ".", "backup_export.json")
        with open(dump_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        return dump_path

db = Database()
