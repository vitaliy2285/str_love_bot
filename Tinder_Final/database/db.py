import math
import random
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class Database:
    def __init__(self, path: str):
        self.path = path
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row

    def init(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                age INTEGER,
                gender TEXT,
                bio TEXT,
                photo_id TEXT,
                username TEXT,
                city TEXT DEFAULT 'Sterlitamak',
                lat REAL DEFAULT 53.63,
                lon REAL DEFAULT 55.95,
                is_active INTEGER DEFAULT 1,
                is_banned INTEGER DEFAULT 0,
                balance INTEGER DEFAULT 0,
                is_vip INTEGER DEFAULT 0,
                vip_end_date TEXT,
                rating_score REAL DEFAULT 1000,
                likes_received INTEGER DEFAULT 0,
                settings_min_age INTEGER DEFAULT 18,
                settings_max_age INTEGER DEFAULT 60,
                settings_radius_km INTEGER DEFAULT 30,
                last_active TEXT,
                created_at TEXT,
                looking_for_gender TEXT DEFAULT 'any',
                superlikes_left INTEGER DEFAULT 0,
                total_swipes INTEGER DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user INTEGER NOT NULL,
                to_user INTEGER NOT NULL,
                is_superlike INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                UNIQUE(from_user, to_user)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user1 INTEGER NOT NULL,
                user2 INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user1, user2)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS blind_queue (
                user_id INTEGER PRIMARY KEY,
                gender TEXT,
                looking_for TEXT,
                joined_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS blind_pairs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user1 INTEGER UNIQUE,
                user2 INTEGER UNIQUE,
                created_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS swipe_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                target_user INTEGER,
                action TEXT,
                created_at TEXT
            )
            """
        )
        self.conn.commit()

    def upsert_user(self, user_id: int, username: Optional[str] = None) -> None:
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            """
            INSERT INTO users (user_id, username, last_active, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                last_active=excluded.last_active,
                is_active=1
            """,
            (user_id, username, now, now),
        )
        self.conn.commit()

    def complete_profile(self, user_id: int, data: Dict) -> None:
        fields = [
            "name", "age", "gender", "city", "lat", "lon", "photo_id", "bio", "looking_for_gender"
        ]
        values = [data.get(k) for k in fields]
        values.append(datetime.utcnow().isoformat())
        values.append(user_id)
        self.conn.execute(
            f"UPDATE users SET {', '.join([f'{f}=?' for f in fields])}, last_active=? WHERE user_id=?",
            values,
        )
        self.conn.commit()

    def get_user(self, user_id: int) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()

    def deactivate_user(self, user_id: int) -> None:
        self.conn.execute("UPDATE users SET is_active=0 WHERE user_id=?", (user_id,))
        self.conn.commit()

    @staticmethod
    def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return r * c

    def get_candidates(self, user_id: int, limit: int = 30) -> List[sqlite3.Row]:
        user = self.get_user(user_id)
        if not user:
            return []

        seen = self.conn.execute("SELECT to_user FROM likes WHERE from_user=?", (user_id,)).fetchall()
        seen_ids = {x[0] for x in seen}

        rows = self.conn.execute(
            """
            SELECT * FROM users
            WHERE user_id != ?
              AND is_active = 1
              AND is_banned = 0
              AND age BETWEEN ? AND ?
            ORDER BY rating_score DESC, last_active DESC
            LIMIT 300
            """,
            (user_id, user["settings_min_age"], user["settings_max_age"]),
        ).fetchall()

        out = []
        for row in rows:
            if row["user_id"] in seen_ids:
                continue
            if user["looking_for_gender"] != "any" and row["gender"] != user["looking_for_gender"]:
                continue
            dist = self.haversine_km(user["lat"], user["lon"], row["lat"], row["lon"])
            if dist <= user["settings_radius_km"]:
                out.append(row)
            if len(out) >= limit:
                break
        return out

    def add_like(self, from_user: int, to_user: int, is_superlike: int = 0) -> bool:
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            "INSERT OR REPLACE INTO likes(from_user, to_user, is_superlike, created_at) VALUES (?, ?, ?, ?)",
            (from_user, to_user, is_superlike, now),
        )
        self.conn.execute("UPDATE users SET likes_received = likes_received + 1 WHERE user_id=?", (to_user,))
        self.conn.execute(
            "INSERT INTO swipe_history(user_id, target_user, action, created_at) VALUES (?, ?, ?, ?)",
            (from_user, to_user, "superlike" if is_superlike else "like", now),
        )
        self.conn.execute("UPDATE users SET total_swipes = total_swipes + 1 WHERE user_id=?", (from_user,))
        is_match = self.conn.execute("SELECT 1 FROM likes WHERE from_user=? AND to_user=?", (to_user, from_user)).fetchone()
        if is_match:
            a, b = sorted([from_user, to_user])
            self.conn.execute(
                "INSERT OR IGNORE INTO matches(user1, user2, created_at) VALUES (?, ?, ?)",
                (a, b, now),
            )
        self.conn.commit()
        return bool(is_match)

    def add_dislike(self, from_user: int, to_user: int) -> None:
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            "INSERT INTO swipe_history(user_id, target_user, action, created_at) VALUES (?, ?, 'dislike', ?)",
            (from_user, to_user, now),
        )
        self.conn.execute("UPDATE users SET total_swipes = total_swipes + 1 WHERE user_id=?", (from_user,))
        self.conn.commit()

    def rewind_last_swipe(self, user_id: int) -> Optional[int]:
        row = self.conn.execute(
            "SELECT id, target_user, action FROM swipe_history WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,)
        ).fetchone()
        if not row:
            return None
        self.conn.execute("DELETE FROM swipe_history WHERE id=?", (row["id"],))
        if row["action"] in {"like", "superlike"}:
            self.conn.execute("DELETE FROM likes WHERE from_user=? AND to_user=?", (user_id, row["target_user"]))
        self.conn.commit()
        return row["target_user"]

    def who_liked_me(self, user_id: int) -> List[sqlite3.Row]:
        return self.conn.execute(
            """
            SELECT u.* FROM likes l
            JOIN users u ON u.user_id = l.from_user
            WHERE l.to_user = ?
            ORDER BY l.created_at DESC
            """,
            (user_id,),
        ).fetchall()

    def add_balance(self, user_id: int, amount: int) -> None:
        self.conn.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
        self.conn.commit()

    def buy_superlikes(self, user_id: int, count: int, price: int) -> bool:
        row = self.get_user(user_id)
        if not row or row["balance"] < price:
            return False
        self.conn.execute(
            "UPDATE users SET balance = balance - ?, superlikes_left = superlikes_left + ? WHERE user_id=?",
            (price, count, user_id),
        )
        self.conn.commit()
        return True

    def set_vip(self, user_id: int, days: int) -> None:
        end_date = datetime.utcnow().timestamp() + days * 86400
        self.conn.execute("UPDATE users SET is_vip=1, vip_end_date=? WHERE user_id=?", (str(end_date), user_id))
        self.conn.commit()

    def enqueue_blind(self, user_id: int, gender: str, looking_for: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO blind_queue(user_id, gender, looking_for, joined_at) VALUES (?, ?, ?, ?)",
            (user_id, gender, looking_for, datetime.utcnow().isoformat()),
        )
        self.conn.commit()

    def try_match_blind(self, user_id: int) -> Optional[Tuple[int, int]]:
        me = self.conn.execute("SELECT * FROM blind_queue WHERE user_id=?", (user_id,)).fetchone()
        if not me:
            return None
        candidates = self.conn.execute(
            "SELECT * FROM blind_queue WHERE user_id!=? ORDER BY joined_at ASC", (user_id,)
        ).fetchall()
        for row in candidates:
            if (me["looking_for"] in ("any", row["gender"])) and (row["looking_for"] in ("any", me["gender"])):
                a, b = sorted([user_id, row["user_id"]])
                self.conn.execute("DELETE FROM blind_queue WHERE user_id IN (?, ?)", (a, b))
                self.conn.execute(
                    "INSERT INTO blind_pairs(user1, user2, created_at) VALUES (?, ?, ?)",
                    (a, b, datetime.utcnow().isoformat()),
                )
                self.conn.commit()
                return a, b
        return None

    def blind_partner(self, user_id: int) -> Optional[int]:
        row = self.conn.execute("SELECT user1, user2 FROM blind_pairs WHERE user1=? OR user2=?", (user_id, user_id)).fetchone()
        if not row:
            return None
        return row["user2"] if row["user1"] == user_id else row["user1"]

    def stop_blind(self, user_id: int) -> None:
        self.conn.execute("DELETE FROM blind_queue WHERE user_id=?", (user_id,))
        self.conn.execute("DELETE FROM blind_pairs WHERE user1=? OR user2=?", (user_id, user_id))
        self.conn.commit()

    def stats(self) -> Dict[str, int]:
        return {
            "users": self.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            "active": self.conn.execute("SELECT COUNT(*) FROM users WHERE is_active=1").fetchone()[0],
            "matches": self.conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0],
            "likes": self.conn.execute("SELECT COUNT(*) FROM likes").fetchone()[0],
        }
