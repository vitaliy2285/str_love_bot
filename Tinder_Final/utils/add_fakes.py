import random
import sqlite3
from datetime import datetime

DB_PATH = "tinder_final.sqlite3"
CENTER_LAT = 53.63
CENTER_LON = 55.95

MALE_NAMES = ["Artem", "Ivan", "Max", "Daniil", "Roman", "Egor", "Nikita", "Kirill"]
FEMALE_NAMES = ["Anna", "Maria", "Daria", "Elena", "Vika", "Sofia", "Alina", "Polina"]
BIOS = [
    "Love coffee and long walks.",
    "Sport, books, and dogs.",
    "Looking for real chemistry.",
    "Music addict and traveler.",
    "Let's meet for tea.",
]


def rand_coord(center: float) -> float:
    return center + random.uniform(-0.15, 0.15)


def main():
    conn = sqlite3.connect(DB_PATH)
    now = datetime.utcnow().isoformat()
    for i in range(50):
        gender = "M" if i % 2 == 0 else "F"
        name = random.choice(MALE_NAMES if gender == "M" else FEMALE_NAMES)
        user_id = 900000 + i
        looking_for = "f" if gender == "M" else "m"
        conn.execute(
            """
            INSERT OR REPLACE INTO users (
                user_id, name, age, gender, bio, photo_id, username,
                city, lat, lon, is_active, is_banned, balance, is_vip, vip_end_date,
                rating_score, likes_received, settings_min_age, settings_max_age,
                settings_radius_km, last_active, created_at, looking_for_gender,
                superlikes_left, total_swipes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, 200, 0, NULL, ?, 0, 18, 60, 80, ?, ?, ?, 3, 0)
            """,
            (
                user_id,
                name,
                random.randint(18, 40),
                gender,
                random.choice(BIOS),
                "AgACAgIAAxkBAAIB",
                f"fake_{user_id}",
                "Sterlitamak",
                rand_coord(CENTER_LAT),
                rand_coord(CENTER_LON),
                random.uniform(900, 1300),
                now,
                now,
                looking_for,
            ),
        )
    conn.commit()
    conn.close()
    print("Added/updated 50 fake users")


if __name__ == "__main__":
    main()
