from datetime import datetime, time
from typing import Optional


def is_blind_chat_time(now: Optional[datetime] = None) -> bool:
    """Пятница 20:00 - суббота 02:00 по серверному времени."""
    now = now or datetime.now()
    weekday = now.weekday()  # Пн=0 ... Вс=6
    current_time = now.time()

    friday_start = time(20, 0)
    saturday_end = time(2, 0)

    return (weekday == 4 and current_time >= friday_start) or (weekday == 5 and current_time <= saturday_end)
