from aiogram import executor

from loader import db, dp
import handlers  # noqa: F401


def main():
    db.init()
    executor.start_polling(dp, skip_updates=True)


if __name__ == "__main__":
    main()
