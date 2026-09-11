import time
from typing import Dict, Set, Any, Tuple, Optional

class MemoryCache:
    def __init__(self):
        # Guruh adminlari keshi: chat_id -> (set(admin_ids), expire_time)
        self._admins: Dict[int, Tuple[Set[int], float]] = {}
        
        # Ruxsat olgan foydalanuvchilar (limitni bajargan yoki oq ro'yxatdagilar): chat_id -> set(user_ids)
        self._allowed_users: Dict[int, Set[int]] = {}

        # Guruh sozlamalari keshi: chat_id -> (settings_dict, expire_time)
        self._group_settings: Dict[int, Tuple[Dict[str, Any], float]] = {}

        # Yaqinda mute qilingan foydalanuvchilar: (chat_id, user_id) -> expire_time
        # (Telegram API ga qayta-qayta restrict so'rov yubormaslik uchun)
        self._muted_users: Dict[Tuple[int, int], float] = {}

        # Foydalanuvchi tanlagan tili: user_id -> lang
        self._user_languages: Dict[int, str] = {}

        # Yaqinda qo'shilganlar keshi (duplicate eventlarni oldini olish): (chat_id, user_id) -> expire_time
        self._recently_joined: Dict[Tuple[int, int], float] = {}

    # --- QO'SHILGANLAR KESHI ---
    def is_recently_joined(self, chat_id: int, user_id: int) -> bool:
        exp = self._recently_joined.get((chat_id, user_id))
        return bool(exp and exp > time.time())

    def set_recently_joined(self, chat_id: int, user_id: int, ttl: int = 15):
        self._recently_joined[(chat_id, user_id)] = time.time() + ttl

    # --- FOYDALANUVCHI TILI KESHI ---
    def get_user_language(self, user_id: int) -> Optional[str]:
        return self._user_languages.get(user_id)

    def set_user_language(self, user_id: int, lang: str):
        self._user_languages[user_id] = lang

    # --- ADMIN KESHI ---
    def get_admins(self, chat_id: int) -> Optional[Set[int]]:
        data = self._admins.get(chat_id)
        if data and data[1] > time.time():
            return data[0]
        return None

    def set_admins(self, chat_id: int, admin_ids: Set[int], ttl: int = 300):
        self._admins[chat_id] = (admin_ids, time.time() + ttl)

    def invalidate_admins(self, chat_id: int):
        self._admins.pop(chat_id, None)

    # --- RUXSAT ETILGAN A'ZOLAR KESHI ---
    def is_user_allowed(self, chat_id: int, user_id: int) -> bool:
        allowed = self._allowed_users.get(chat_id)
        return user_id in allowed if allowed else False

    def add_allowed_user(self, chat_id: int, user_id: int):
        if chat_id not in self._allowed_users:
            self._allowed_users[chat_id] = set()
        self._allowed_users[chat_id].add(user_id)

    def remove_allowed_user(self, chat_id: int, user_id: int):
        allowed = self._allowed_users.get(chat_id)
        if allowed and user_id in allowed:
            allowed.remove(user_id)

    def clear_allowed_users(self, chat_id: int):
        self._allowed_users.pop(chat_id, None)

    # --- GURUH SOZLAMALARI KESHI ---
    def get_group_settings(self, chat_id: int) -> Optional[Dict[str, Any]]:
        data = self._group_settings.get(chat_id)
        if data and data[1] > time.time():
            return data[0]
        return None

    def set_group_settings(self, chat_id: int, settings: Dict[str, Any], ttl: int = 120):
        self._group_settings[chat_id] = (settings, time.time() + ttl)

    def invalidate_group_settings(self, chat_id: int):
        self._group_settings.pop(chat_id, None)

    # --- MUTE QILINGANLAR KESHI (FloodWait dan himoya) ---
    def is_recently_muted(self, chat_id: int, user_id: int) -> bool:
        expire = self._muted_users.get((chat_id, user_id))
        if expire and expire > time.time():
            return True
        return False

    def set_recently_muted(self, chat_id: int, user_id: int, ttl: int = 540):
        # 9-10 daqiqa keshda saqlaymiz
        self._muted_users[(chat_id, user_id)] = time.time() + ttl

    def remove_muted(self, chat_id: int, user_id: int):
        self._muted_users.pop((chat_id, user_id), None)

    def clear_all(self):
        """Barcha kesh xotiralarini tozalash"""
        self._admins.clear()
        self._allowed_users.clear()
        self._group_settings.clear()
        self._muted_users.clear()
        self._user_languages.clear()
        self._recently_joined.clear()

cache = MemoryCache()
