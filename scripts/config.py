from dotenv import set_key, find_dotenv
import os
import base64

# Генерация Fernet-ключа (32 байта, закодированных в Base64)
def generate_encryption_key():
    return base64.urlsafe_b64encode(os.urandom(32)).decode()

# Данные для сохранения
config_data = {
    "TOKEN_BOT": "7730164056:AAHteTq1BasElO9cbDU0aHzSfLyA3Hw20dU",
    "ACCOUNT_ID": "493373",
    "SECRET_KEY": "test_yYfmHxQmXLFNdozQmMKzAZCaIs8XY1Bj9xC5IaeRAQE",
    "ENCRYPTION_KEY": generate_encryption_key()
}

# Путь к файлу .env
env_file = find_dotenv() or ".env"

# Сохранение данных в файл
try:
    for key, value in config_data.items():
        set_key(env_file, key, value)
    print(f"Конфигурация успешно сохранена в {env_file}")
except Exception as e:
    print(f"Ошибка при сохранении данных: {e}")

# @bot.message_handler(commands=['add_admin'])
# def add_admin(message):
#     try:
#         if not is_admin(message.chat.id):
#             bot.send_message(message.chat.id, "У вас нет прав для использования этой команды.")
#             return
#
#         args = message.text.split(maxsplit=1)
#         if len(args) < 2:
#             bot.send_message(message.chat.id,
#                              "Использование: /add_admin @username или /add_admin https://t.me/username")
#             return
#
#         user_input = args[1].strip()
#
#         if user_input.startswith("@"):
#             username = user_input[1:]
#         elif "t.me/" in user_input:
#             username = user_input.split("t.me/")[-1].strip("/")
#         else:
#             bot.send_message(message.chat.id, "Некорректный формат. Укажите @username или ссылку на профиль.")
#             return
#
#         try:
#             user = bot.get_chat(username)
#         except telebot.apihelper.ApiTelegramException as e:
#             if "chat not found" in str(e):
#                 bot.send_message(
#                     message.chat.id,
#                     "Не удалось найти пользователя. Убедитесь, что он уже взаимодействовал с ботом (отправьте любое сообщение боту)."
#                 )
#             else:
#                 bot.send_message(message.chat.id, "Произошла ошибка при получении информации о пользователе.")
#             print(f"Error resolving username: {e}")
#             return
#
#         new_admin_id = user.id
#         if new_admin_id in ADMIN_IDS:
#             bot.send_message(message.chat.id, "Этот пользователь уже является администратором.")
#             return
#
#         ADMIN_IDS.append(new_admin_id)
#         save_admin_ids()  # Save the updated admin list
#
#         bot.send_message(message.chat.id,
#                          f"Пользователь {user.first_name} (@{username}) успешно добавлен как администратор.")
#         bot.send_message(new_admin_id, "Вас назначили администратором бота. Добро пожаловать!")
#
#     except Exception as e:
#         bot.send_message(message.chat.id, "Произошла ошибка при добавлении администратора.")
#         print(f"Error in /add_admin: {e}")