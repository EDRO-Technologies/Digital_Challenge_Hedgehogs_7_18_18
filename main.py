import uuid
import sqlite3
import telebot
from yookassa import Configuration, Payment
from datetime import datetime
from config import token_bot

Configuration.account_id = "493373"
Configuration.secret_key = "test_yYfmHxQmXLFNdozQmMKzAZCaIs8XY1Bj9xC5IaeRAQE"

ADMIN_IDS = [466348470]
bot = telebot.TeleBot(token_bot)

print("Бот запущен!")


def is_admin(user_id):
    return user_id in ADMIN_IDS


@bot.message_handler(commands=['start'])
def register_user(message):
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
        bot.send_message(message.chat.id, "Вы успешно зарегистрированы!")
    except Exception as e:
        bot.send_message(message.chat.id, "Произошла ошибка при регистрации.")
        print(f"Error saving user to database: {e}")


@bot.message_handler(commands=['create_payment'])
def create_payment_for_all(message):
    try:
        if not is_admin(message.chat.id):
            bot.send_message(message.chat.id, "У вас нет прав для использования этой команды.")
            return

        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            bot.send_message(
                message.chat.id,
                "Укажите сумму и описание.\nПример: /create_payment 1500.00 Оплата за услугу"
            )
            return

        amount = float(args[1])
        description = args[2]

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
        users_cur.execute("SELECT id, full_name FROM users")
        users = users_cur.fetchall()
        users_con.close()

        for user_id, full_name in users:
            payment = Payment.create({
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": "https://t.me/profspay_bot?i_paid"
                },
                "capture": True,
                "description": description
            }, uuid.uuid4())

            confirmation_url = payment.confirmation.confirmation_url

            cur.execute("""
                INSERT INTO payment_users (user_id, status, payment_id, confirmation_url, amount, created_at, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, "pending", payment.id, confirmation_url, amount, created_at, description))

            bot.send_message(
                user_id,
                f"Для вас создан новый платёж:\n"
                f"Сумма: {amount} RUB\n"
                f"Описание: {description}\n"
                f"Ссылка для оплаты: {confirmation_url}"
            )

        con.commit()
        con.close()

        bot.send_message(message.chat.id, "Платёж успешно создан и отправлен всем пользователям.")
    except Exception as e:
        bot.send_message(message.chat.id, "Произошла ошибка при создании платежа.")
        print(f"Error in /create_payment_for_all: {e}")


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


if __name__ == '__main__':
    bot.polling()
