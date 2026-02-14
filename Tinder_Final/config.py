import os
from typing import List

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

_raw_admins = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: List[int] = [int(x) for x in _raw_admins.split(",") if x.strip().isdigit()]

DATABASE_PATH = os.getenv("DATABASE_PATH", "tinder_final.sqlite3")
DEFAULT_CITY = "Sterlitamak"
DEFAULT_LAT = 53.63
DEFAULT_LON = 55.95
