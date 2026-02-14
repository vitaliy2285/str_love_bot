import random


def generate_fake_profiles(count: int = 20):
    names = ["Алина", "Катя", "Оля", "Вика", "Света", "Даша", "Лена", "Марина", "Кристина", "Настя"]
    bios = ["Люблю кофе", "Ищу парня", "Просто гуляю", "Скучно...", "Хочу на море"]

    for i in range(count):
        yield {
            "user_id": 777000 + i,
            "name": random.choice(names),
            "age": random.randint(18, 30),
            "gender": "female",
            "city": "Стерлитамак",
            "bio": random.choice(bios),
        }
