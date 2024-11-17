import os
import json
import sqlite3
import uuid
import telebot
from yookassa import Configuration, Payment
from datetime import datetime
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import schedule
import time
import threading

# Загрузка переменных из .env
load_dotenv()

# Получение данных
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

# Проверка формата ключа
if ENCRYPTION_KEY:
    try:
        cipher_suite = Fernet(ENCRYPTION_KEY.encode())
        print("Ключ успешно загружен и инициализирован.")
    except ValueError as e:
        print(f"Ошибка в формате ENCRYPTION_KEY: {e}")
else:
    print("ENCRYPTION_KEY не найден в .env")

# Получение конфиденциальных данных из переменных окружения
TOKEN_BOT = os.getenv("TOKEN_BOT")
ACCOUNT_ID = os.getenv("ACCOUNT_ID")
SECRET_KEY = os.getenv("SECRET_KEY")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

# Проверка наличия ключей
if not all([TOKEN_BOT, ACCOUNT_ID, SECRET_KEY, ENCRYPTION_KEY]):
    raise ValueError("Отсутствуют необходимые переменные окружения.")

# Конфигурация шифрования
cipher_suite = Fernet(ENCRYPTION_KEY.encode())

# Настройка YooKassa
Configuration.account_id = ACCOUNT_ID
Configuration.secret_key = SECRET_KEY

bot = telebot.TeleBot(TOKEN_BOT)

print("Бот запущен!")

ADMIN_FILE = "admin_ids.json"

if os.path.exists(ADMIN_FILE):
    with open(ADMIN_FILE, "r") as f:
        ADMIN_IDS = json.load(f)
else:
    ADMIN_IDS = [466348470]


def is_admin(user_id):
    return user_id in ADMIN_IDS


def create_payment_for_all(amount, description):
    try:
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        con = sqlite3.connect("database/payments.db")

        cur = con.cursor()

        cur.execute("""
            INSERT INTO payments (description, amount, created_at)
            VALUES (?, ?, ?)
        """, (description, amount, created_at))

        cur.execute("DELETE FROM payment_users")

        users_con = sqlite3.connect("database/chats.db")
        users_cur = users_con.cursor()
        users_cur.execute("SELECT id FROM users")
        users = users_cur.fetchall()
        users_con.close()
        for (user_id,) in users:
            payment = Payment.create({
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": "https://t.me/profspay_bot/pay"
                },
                "capture": True,
                "description": description
            }, uuid.uuid4())
            print(1)

            confirmation_url = payment.confirmation.confirmation_url

            print(2)
            cur.execute("""
                INSERT INTO payment_users (user_id, status, payment_id, confirmation_url, amount, created_at, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, "pending", payment.id, confirmation_url, amount, created_at, description))

            bot.send_message(
                user_id,
                f"Ссылка для оплаты: https://t.me/profspay_bot/pay"
            )

        con.commit()
        con.close()

    except Exception as e:
        return "Произошла ошибка", 500


@bot.message_handler(commands=['start'])
def register_user(message):
    pic = open('database/start_pic.jpg', 'rb')
    bot.send_photo(message.chat.id, photo=pic,
                   caption="Приветствуем в Студенческом профсоюзе СурГУ! 🚀 \n\n  Мы поможем тебе в учёбе и жизни: "
                           "скидки, подкасты, конкурсы, защита твоих прав и материальная поддержка!\n\nВступив (3% "
                           "от стипендии), получишь льготы и доступ к приложению СКС РФ. Пройди наш опрос и обратись "
                           "к профоргу своего института для вступления. Присоединяйся! ❤️\n\n "
                           "Опрос: https://docs.google.com/forms/d/e/1FAIpQLSc-Qp5VzL529")
    try:
        bot.send_message(message.chat.id, "Введите своё ФИО:")
        bot.register_next_step_handler(message, get_full_name)
    except Exception as e:
        bot.send_message(message.chat.id, "Произошла ошибка при регистрации.")
        print(f"Error in /start: {e}")


def get_full_name(message):
    full_name = message.text.strip()
    bot.send_message(message.chat.id, "Введите вашу учебную группу:")
    bot.register_next_step_handler(message, get_group, full_name)


def get_group(message, full_name):
    group = message.text.strip()
    try:
        con = sqlite3.connect("database/chats.db")
        cur = con.cursor()
        cur.execute("""
        INSERT INTO users (id, full_name, group_name) 
        VALUES (?, ?, ?)
        """, (message.chat.id, full_name, group))
        con.commit()
        con.close()

        con = sqlite3.connect("database/payments.db")
        cur = con.cursor()
        cur.execute("""
        INSERT INTO payment_users (user_id, status) 
        VALUES (?, ?)
        """, (message.chat.id, "paid"))
        con.commit()
        con.close()
        bot.send_message(message.chat.id, "Вы успешно зарегистрированы!")
    except Exception as e:
        bot.send_message(message.chat.id, "Произошла ошибка при регистрации.")
        print(f"Error saving user to database: {e}")


@bot.message_handler(commands=['i_paid'])
def verify_payment(message):
    try:
        user_id = message.chat.id

        con = sqlite3.connect("database/payments.db")
        cur = con.cursor()
        cur.execute("""
            SELECT status, payment_id FROM payment_users WHERE user_id = ?
        """, (user_id,))
        user_payment = cur.fetchone()
        con.close()

        if not user_payment:
            bot.send_message(user_id, "Вы не привязаны к текущему платежу.")
            return

        status, payment_id = user_payment

        if status == "paid":
            bot.send_message(user_id, "Вы уже оплатили текущий платёж.")
            return

        payment = Payment.find_one(payment_id)
        if payment.status == "succeeded":
            con = sqlite3.connect("database/payments.db")
            cur = con.cursor()
            cur.execute("""
                UPDATE payment_users
                SET status = 'paid'
                WHERE user_id = ?
            """, (user_id,))
            con.commit()
            con.close()

            bot.send_message(user_id, "Ваш платёж успешно подтверждён. Спасибо!")
            for admin_id in ADMIN_IDS:
                bot.send_message(admin_id, f"Пользователь @{message.from_user.username} оплатил платёж.")
        else:
            bot.send_message(user_id, "Ваш платёж ещё не завершён. Проверьте статус позже.")
    except Exception as e:
        bot.send_message(message.chat.id, "Произошла ошибка при проверке платежа.")
        print(f"Error in /i_paid: {e}")


@bot.message_handler(commands=['who_paid'])
def who_paid(message):
    try:
        if not is_admin(message.chat.id):
            bot.send_message(message.chat.id, "У вас нет прав для использования этой команды.")
            return

        payments_con = sqlite3.connect("database/payments.db")
        payments_cur = payments_con.cursor()

        payments_cur.execute(
            "SELECT id, description, amount, created_at FROM payments ORDER BY created_at DESC LIMIT 1")
        payment = payments_cur.fetchone()

        if not payment:
            bot.send_message(message.chat.id, "В базе данных отсутствуют записи о платежах.")
            payments_con.close()
            return

        payment_id, description, amount, created_at = payment

        payments_cur.execute("""
            SELECT user_id, status FROM payment_users
        """)
        payment_users = payments_cur.fetchall()
        payments_con.close()

        if not payment_users:
            bot.send_message(message.chat.id, "Ни один пользователь не привязан к текущему платежу.")
            return

        chats_con = sqlite3.connect("database/chats.db")
        chats_cur = chats_con.cursor()

        user_details = {}
        chats_cur.execute("SELECT id, full_name FROM users")
        for user_id, full_name in chats_cur.fetchall():
            user_details[user_id] = full_name
        chats_con.close()

        paid_users = []
        pending_users = []
        for user_id, status in payment_users:
            name = user_details.get(user_id, "Неизвестный пользователь")
            if status == "paid":
                paid_users.append(f"{name} ({user_id})")
            else:
                pending_users.append(f"{name} ({user_id})")

        message_text = f"Платёж:\nОписание: {description}\nСумма: {amount} RUB\nДата: {created_at}\n\n"
        message_text += f"**Оплатили:** ({len(paid_users)})\n" + (
            "\n".join(paid_users) if paid_users else "Нет данных") + "\n\n"
        message_text += f"**Не оплатили:** ({len(pending_users)})\n" + (
            "\n".join(pending_users) if pending_users else "Нет данных")

        bot.send_message(message.chat.id, message_text)
    except Exception as e:
        bot.send_message(message.chat.id, "Произошла ошибка при получении списка платежей.")
        print(f"Error in /who_paid: {e}")


def send_payment_reminders():
    try:
        con = sqlite3.connect("database/payments.db")
        cur = con.cursor()

        cur.execute("""
            SELECT id, description, amount, created_at FROM payments ORDER BY created_at DESC LIMIT 1
        """)
        payment = cur.fetchone()

        if not payment:
            print("Нет активных платежей для отправки напоминаний.")
            return

        payment_id, description, amount, created_at = payment

        cur.execute("""
            SELECT user_id, confirmation_url FROM payment_users WHERE status = 'pending'
        """)
        pending_users = cur.fetchall()
        con.close()

        for user_id, confirmation_url in pending_users:
            bot.send_message(
                user_id,
                f"Напоминание: Вы ещё не оплатили платёж.\n"
                f"Сумма: {amount} RUB\n"
                f"Описание: {description}\n"
                f"Ссылка для оплаты: {confirmation_url}"
            )
        print(f"Отправлены напоминания {len(pending_users)} пользователям.")
    except Exception as e:
        print(f"Ошибка при отправке напоминаний: {e}")


def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)


schedule.every(3).days.do(send_payment_reminders)

print("Планировщик напоминаний запущен!")

if __name__ == '__main__':
    bot.polling()
    threading.Thread(target=run_schedule, daemon=True).start()
