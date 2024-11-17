from dotenv import set_key, find_dotenv
import os
import base64


def generate_encryption_key():
    return base64.urlsafe_b64encode(os.urandom(32)).decode()


config_data = {
    "TOKEN_BOT": "7730164056:AAHteTq1BasElO9cbDU0aHzSfLyA3Hw20dU",
    "ACCOUNT_ID": "493373",
    "SECRET_KEY": "test_yYfmHxQmXLFNdozQmMKzAZCaIs8XY1Bj9xC5IaeRAQE",
    "ENCRYPTION_KEY": generate_encryption_key()
}

env_file = find_dotenv() or ".env"

try:
    for key, value in config_data.items():
        set_key(env_file, key, value)
    print(f"Конфигурация успешно сохранена в {env_file}")
except Exception as e:
    print(f"Ошибка при сохранении данных: {e}")
