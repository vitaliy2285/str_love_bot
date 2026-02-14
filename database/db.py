import math
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class Database:
    """SQLite access layer for Str.Love bot."""

    def __init__(self, path: str):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.create_tables()
        self._run_migrations()

    def create_tables(self) -> None:
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                age INTEGER,
                gender TEXT,
                city TEXT,
                latitude REAL,
                longitude REAL,
                photo_id TEXT,
                bio TEXT,
                username TEXT,
                is_active INTEGER DEFAULT 1,
                is_banned INTEGER DEFAULT 0,
                balance INTEGER DEFAULT 0,
                is_vip INTEGER DEFAULT 0,
                vip_end_date TEXT,
                daily_superlikes_left INTEGER DEFAULT 1,
                superlikes_reset_at TEXT,
                boosted_until TEXT,
                min_age INTEGER DEFAULT 18,
                max_age INTEGER DEFAULT 99,
                search_radius INTEGER DEFAULT 50
            )
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                who_id INTEGER,
                whom_id INTEGER,
                reaction TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(who_id, whom_id)
            )
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_a INTEGER,
                user_b INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_a, user_b)
            )
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS blind_queue (
                user_id INTEGER PRIMARY KEY,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS blind_chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_a INTEGER,
                user_b INTEGER,
                is_active INTEGER DEFAULT 1,
                reveal_a INTEGER DEFAULT 0,
                reveal_b INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS blind_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                sender_id INTEGER,
                receiver_id INTEGER,
                receiver_message_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                deleted INTEGER DEFAULT 0
            )
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS shop_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_code TEXT,
                amount INTEGER,
                status TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.commit()

    def _run_migrations(self) -> None:
        self._ensure_column("users", "latitude", "REAL")
        self._ensure_column("users", "longitude", "REAL")
        self._ensure_column("users", "is_banned", "INTEGER DEFAULT 0")
        self._ensure_column("users", "boosted_until", "TEXT")
        self._ensure_column("users", "min_age", "INTEGER DEFAULT 18")
        self._ensure_column("users", "max_age", "INTEGER DEFAULT 99")
        self._ensure_column("users", "search_radius", "INTEGER DEFAULT 50")
        self.conn.commit()

    def _ensure_column(self, table: str, column: str, ddl: str) -> None:
        self.cursor.execute(f"PRAGMA table_info({table})")
        cols = {row["name"] for row in self.cursor.fetchall()}
        if column not in cols:
            self.cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")

    def add_user(self, user_data: Tuple) -> None:
        self.cursor.execute(
            """
            INSERT OR REPLACE INTO users (
                user_id, name, age, gender, city, latitude, longitude, photo_id, bio, username,
                is_active, is_banned, balance, is_vip, vip_end_date, daily_superlikes_left,
                superlikes_reset_at, boosted_until, min_age, max_age, search_radius
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?, ?, ?, ?, ?, ?, 18, 99, 50)
            """,
            user_data,
        )
        self.conn.commit()

    def update_search_preferences(self, user_id: int, min_age: int, max_age: int, search_radius: int) -> None:
        self.cursor.execute(
            "UPDATE users SET min_age = ?, max_age = ?, search_radius = ? WHERE user_id = ?",
            (min_age, max_age, search_radius, user_id),
        )
        self.conn.commit()

    def get_user(self, user_id: int) -> Optional[sqlite3.Row]:
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone()

    def get_users_count(self) -> int:
        self.cursor.execute("SELECT COUNT(*) FROM users")
        return self.cursor.fetchone()[0]

    def get_active_users_count(self) -> int:
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1 AND is_banned = 0")
        return self.cursor.fetchone()[0]

    def get_vip_count(self) -> int:
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE is_vip = 1")
        return self.cursor.fetchone()[0]

    def get_revenue(self) -> int:
        self.cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM shop_orders WHERE status = 'paid'")
        return self.cursor.fetchone()[0]

    def get_all_user_ids(self) -> List[int]:
        self.cursor.execute("SELECT user_id FROM users WHERE is_banned = 0")
        return [row[0] for row in self.cursor.fetchall()]

    def ban_user(self, user_id: int) -> bool:
        self.cursor.execute("UPDATE users SET is_banned = 1, is_active = 0 WHERE user_id = ?", (user_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def get_who_liked_me(self, user_id: int) -> List[sqlite3.Row]:
        self.cursor.execute(
            """
            SELECT u.* FROM likes l
            JOIN users u ON u.user_id = l.who_id
            WHERE l.whom_id = ?
              AND l.reaction IN ('like', 'superlike')
              AND l.who_id NOT IN (
                SELECT whom_id FROM likes WHERE who_id = ? AND reaction IN ('like', 'superlike')
              )
            ORDER BY l.created_at DESC
            """,
            (user_id, user_id),
        )
        return self.cursor.fetchall()

    @staticmethod
    def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        radius = 6371.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return 2 * radius * math.asin(math.sqrt(a))

    def has_liked(self, who_id: int, whom_id: int) -> bool:
        self.cursor.execute(
            """
            SELECT 1 FROM likes
            WHERE who_id = ?
              AND whom_id = ?
              AND reaction IN ('like', 'superlike')
            """,
            (who_id, whom_id),
        )
        return self.cursor.fetchone() is not None

    def get_candidate(self, user_id: int) -> Optional[Tuple[sqlite3.Row, Optional[float], bool]]:
        me = self.get_user(user_id)
        if not me:
            return None

        target_gender = "female" if me["gender"] == "male" else "male"
        min_age = me["min_age"] or 18
        max_age = me["max_age"] or 99
        search_radius = me["search_radius"] or 50

        self.cursor.execute(
            """
            SELECT * FROM users
            WHERE user_id != ?
              AND is_active = 1
              AND is_banned = 0
              AND gender = ?
              AND age BETWEEN ? AND ?
              AND user_id NOT IN (SELECT whom_id FROM likes WHERE who_id = ?)
            ORDER BY
              CASE
                WHEN boosted_until IS NOT NULL AND boosted_until > CURRENT_TIMESTAMP THEN 0
                WHEN is_vip = 1 THEN 1
                ELSE 2
              END,
              RANDOM()
            LIMIT 80
            """,
            (user_id, target_gender, min_age, max_age, user_id),
        )
        candidates = self.cursor.fetchall()
        if not candidates:
            return None

        has_my_location = me["latitude"] is not None and me["longitude"] is not None
        filtered: List[Tuple[sqlite3.Row, Optional[float]]] = []

        for row in candidates:
            if not has_my_location or row["latitude"] is None or row["longitude"] is None:
                filtered.append((row, None))
                continue

            distance = self.haversine_km(me["latitude"], me["longitude"], row["latitude"], row["longitude"])
            if distance <= search_radius:
                filtered.append((row, distance))

        if not filtered:
            return None

        if has_my_location:
            filtered.sort(key=lambda item: (item[1] is None, item[1] if item[1] is not None else 10 ** 9))

        candidate, distance_km = filtered[0]
        liked_me = self.has_liked(candidate["user_id"], user_id)
        return candidate, distance_km, liked_me

    def add_reaction(self, who_id: int, whom_id: int, reaction: str) -> None:
        self.cursor.execute(
            "INSERT OR REPLACE INTO likes (who_id, whom_id, reaction) VALUES (?, ?, ?)",
            (who_id, whom_id, reaction),
        )
        self.conn.commit()

    def delete_reaction(self, who_id: int, whom_id: int) -> None:
        self.cursor.execute("DELETE FROM likes WHERE who_id = ? AND whom_id = ?", (who_id, whom_id))
        self.conn.commit()

    def check_match(self, who_id: int, whom_id: int) -> bool:
        return self.has_liked(whom_id, who_id)

    def create_match(self, user_1: int, user_2: int) -> None:
        user_a, user_b = sorted([user_1, user_2])
        self.cursor.execute(
            "INSERT OR IGNORE INTO matches (user_a, user_b) VALUES (?, ?)",
            (user_a, user_b),
        )
        self.conn.commit()

    def change_balance(self, user_id: int, delta: int) -> bool:
        user = self.get_user(user_id)
        if not user:
            return False
        new_balance = user["balance"] + delta
        if new_balance < 0:
            return False
        self.cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
        self.conn.commit()
        return True

    def make_vip(self, user_id: int, vip_end_date: str) -> None:
        self.cursor.execute(
            "UPDATE users SET is_vip = 1, vip_end_date = ?, daily_superlikes_left = 6 WHERE user_id = ?",
            (vip_end_date, user_id),
        )
        self.conn.commit()

    def activate_boost(self, user_id: int, hours: int = 1) -> None:
        boosted_until = (datetime.utcnow() + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("UPDATE users SET boosted_until = ? WHERE user_id = ?", (boosted_until, user_id))
        self.conn.commit()

    def create_shop_order(self, user_id: int, item_code: str, amount: int, status: str = "paid") -> None:
        self.cursor.execute(
            "INSERT INTO shop_orders (user_id, item_code, amount, status) VALUES (?, ?, ?, ?)",
            (user_id, item_code, amount, status),
        )
        self.conn.commit()

    def queue_blind_chat(self, user_id: int) -> None:
        self.cursor.execute("INSERT OR REPLACE INTO blind_queue (user_id) VALUES (?)", (user_id,))
        self.conn.commit()

    def remove_from_blind_queue(self, user_id: int) -> None:
        self.cursor.execute("DELETE FROM blind_queue WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def find_blind_partner(self, user_id: int) -> Optional[int]:
        self.cursor.execute(
            "SELECT user_id FROM blind_queue WHERE user_id != ? ORDER BY created_at LIMIT 1", (user_id,)
        )
        row = self.cursor.fetchone()
        return row[0] if row else None

    def create_blind_chat(self, user_a: int, user_b: int) -> None:
        self.cursor.execute("DELETE FROM blind_queue WHERE user_id IN (?, ?)", (user_a, user_b))
        self.cursor.execute(
            "INSERT INTO blind_chats (user_a, user_b, is_active) VALUES (?, ?, 1)",
            (user_a, user_b),
        )
        self.conn.commit()

    def get_active_blind_chat(self, user_id: int) -> Optional[sqlite3.Row]:
        self.cursor.execute(
            """
            SELECT * FROM blind_chats
            WHERE is_active = 1 AND (user_a = ? OR user_b = ?)
            ORDER BY id DESC LIMIT 1
            """,
            (user_id, user_id),
        )
        return self.cursor.fetchone()


    def set_reveal_consent(self, chat_id: int, user_id: int) -> None:
        chat = self.get_active_blind_chat(user_id)
        if not chat or chat["id"] != chat_id:
            return
        field = "reveal_a" if chat["user_a"] == user_id else "reveal_b"
        self.cursor.execute(f"UPDATE blind_chats SET {field} = 1 WHERE id = ?", (chat_id,))
        self.conn.commit()

    def register_blind_message(self, chat_id: int, sender_id: int, receiver_id: int, receiver_message_id: int) -> None:
        self.save_blind_message_link(chat_id, sender_id, receiver_id, receiver_message_id)

    def close_blind_chat(self, chat_id: int) -> None:
        self.cursor.execute("UPDATE blind_chats SET is_active = 0 WHERE id = ?", (chat_id,))
        self.conn.commit()

    def save_blind_message_link(self, chat_id: int, sender_id: int, receiver_id: int, receiver_message_id: int) -> None:
        self.cursor.execute(
            """
            INSERT INTO blind_messages (chat_id, sender_id, receiver_id, receiver_message_id)
            VALUES (?, ?, ?, ?)
            """,
            (chat_id, sender_id, receiver_id, receiver_message_id),
        )
        self.conn.commit()

    def get_expired_blind_messages(self, ttl_minutes: int = 60, older_than_hours: Optional[int] = None) -> List[sqlite3.Row]:
        self.cursor.execute(
            """
            SELECT * FROM blind_messages
            WHERE deleted = 0
              AND datetime(created_at, ?) <= datetime('now')
            """,
            (f"+{(older_than_hours * 60) if older_than_hours is not None else ttl_minutes} minutes",),
        )
        return self.cursor.fetchall()

    def mark_blind_message_deleted(self, message_id: int) -> None:
        self.cursor.execute("UPDATE blind_messages SET deleted = 1 WHERE id = ?", (message_id,))
        self.conn.commit()

    def reset_superlikes_if_needed(self, user_id: int) -> None:
        user = self.get_user(user_id)
        if not user:
            return

        now = datetime.utcnow()
        reset_at_str = user["superlikes_reset_at"]
        should_reset = not reset_at_str
        if reset_at_str:
            try:
                should_reset = now >= datetime.strptime(reset_at_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                should_reset = True

        if should_reset:
            daily_limit = 6 if user["is_vip"] else 1
            next_reset = (now + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                "UPDATE users SET daily_superlikes_left = ?, superlikes_reset_at = ? WHERE user_id = ?",
                (daily_limit, next_reset, user_id),
            )
            self.conn.commit()

    def decrement_superlike(self, user_id: int) -> bool:
        self.reset_superlikes_if_needed(user_id)
        user = self.get_user(user_id)
        if not user or user["daily_superlikes_left"] <= 0:
            return False
        self.cursor.execute(
            "UPDATE users SET daily_superlikes_left = daily_superlikes_left - 1 WHERE user_id = ?",
            (user_id,),
        )
        self.conn.commit()
        return True
