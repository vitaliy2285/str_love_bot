import sqlite3
from datetime import datetime
from typing import List, Optional, Tuple


class Database:
    """Слой доступа к sqlite3 для дейтинг-бота."""

    def __init__(self, path: str):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self) -> None:
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                age INTEGER,
                gender TEXT,
                city TEXT,
                photo_id TEXT,
                bio TEXT,
                username TEXT,
                is_active INTEGER DEFAULT 1,
                balance INTEGER DEFAULT 0,
                is_vip INTEGER DEFAULT 0,
                vip_end_date TEXT,
                daily_superlikes_left INTEGER DEFAULT 1,
                superlikes_reset_at TEXT
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

    def add_user(self, user_data: Tuple) -> None:
        self.cursor.execute(
            """
            INSERT OR REPLACE INTO users (
                user_id, name, age, gender, city, photo_id, bio, username, is_active,
                balance, is_vip, vip_end_date, daily_superlikes_left, superlikes_reset_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
            """,
            user_data,
        )
        self.conn.commit()

    def get_user(self, user_id: int) -> Optional[sqlite3.Row]:
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone()

    def get_users_count(self) -> int:
        self.cursor.execute("SELECT COUNT(*) FROM users")
        return self.cursor.fetchone()[0]

    def get_vip_count(self) -> int:
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE is_vip = 1")
        return self.cursor.fetchone()[0]

    def get_all_user_ids(self) -> List[int]:
        self.cursor.execute("SELECT user_id FROM users")
        return [row[0] for row in self.cursor.fetchall()]

    def get_candidate(self, user_id: int) -> Optional[sqlite3.Row]:
        me = self.get_user(user_id)
        if not me:
            return None
        target_gender = "female" if me["gender"] == "male" else "male"
        self.cursor.execute(
            """
            SELECT * FROM users
            WHERE user_id != ?
              AND is_active = 1
              AND gender = ?
              AND user_id NOT IN (SELECT whom_id FROM likes WHERE who_id = ?)
            ORDER BY RANDOM()
            LIMIT 1
            """,
            (user_id, target_gender, user_id),
        )
        return self.cursor.fetchone()

    def add_reaction(self, who_id: int, whom_id: int, reaction: str) -> None:
        self.cursor.execute(
            "INSERT OR REPLACE INTO likes (who_id, whom_id, reaction) VALUES (?, ?, ?)",
            (who_id, whom_id, reaction),
        )
        self.conn.commit()

    def check_match(self, who_id: int, whom_id: int) -> bool:
        self.cursor.execute(
            "SELECT 1 FROM likes WHERE who_id = ? AND whom_id = ? AND reaction = 'like'",
            (whom_id, who_id),
        )
        return self.cursor.fetchone() is not None

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
        self.cursor.execute("SELECT user_a, user_b FROM blind_chats WHERE id = ?", (chat_id,))
        row = self.cursor.fetchone()
        if not row:
            return
        col = "reveal_a" if row["user_a"] == user_id else "reveal_b"
        self.cursor.execute(f"UPDATE blind_chats SET {col} = 1 WHERE id = ?", (chat_id,))
        self.conn.commit()

    def close_blind_chat(self, chat_id: int) -> None:
        self.cursor.execute("UPDATE blind_chats SET is_active = 0 WHERE id = ?", (chat_id,))
        self.conn.commit()

    def reset_daily_superlikes_if_needed(self, user_id: int) -> None:
        user = self.get_user(user_id)
        if not user:
            return
        now_day = datetime.utcnow().strftime("%Y-%m-%d")
        if user["superlikes_reset_at"] == now_day:
            return
        base = 6 if user["is_vip"] else 1
        self.cursor.execute(
            "UPDATE users SET daily_superlikes_left = ?, superlikes_reset_at = ? WHERE user_id = ?",
            (base, now_day, user_id),
        )
        self.conn.commit()

    def decrement_superlike(self, user_id: int) -> bool:
        self.reset_daily_superlikes_if_needed(user_id)
        user = self.get_user(user_id)
        if not user or user["daily_superlikes_left"] <= 0:
            return False
        self.cursor.execute(
            "UPDATE users SET daily_superlikes_left = daily_superlikes_left - 1 WHERE user_id = ?",
            (user_id,),
        )
        self.conn.commit()
        return True
