import uuid
import sqlite3
import cowsay
import telebot
from yookassa import Configuration, Payment
from datetime import datetime

# Token for Telegram bot
from config import token_bot

# Configure Yookassa
Configuration.account_id = "493373"
Configuration.secret_key = "test_yYfmHxQmXLFNdozQmMKzAZCaIs8XY1Bj9xC5IaeRAQE"

# Define admin IDs (replace with actual Telegram user IDs of admins)
ADMIN_IDS = [466348470]  # Replace with real admin IDs

bot = telebot.TeleBot(token_bot)  # Replace with your bot token

# Start message
print(cowsay.get_output_string('turtle', "Бот запущен!"))
print(" " * 10, "##" * 12)
print("", end='\n')


def is_admin(user_id):
    """Check if a user is an admin."""
    return user_id in ADMIN_IDS


@bot.message_handler(commands=['admin_pay'])
def create_admin_payment(message):
    try:
        # Check if the user is an admin
        if not is_admin(message.chat.id):
            bot.send_message(message.chat.id, "У вас нет прав для использования этой команды.")
            return

        # Split the command to extract parameters
        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            bot.send_message(message.chat.id,
                             "Пожалуйста, укажите сумму и описание.\nПример: /admin_pay 1500.00 Оплата за услугу")
            return

        try:
            # Parse amount and description
            amount = float(args[1])
            description = args[2]
        except ValueError:
            bot.send_message(message.chat.id, "Некорректная сумма. Укажите число в формате: 1500.00")
            return

        # Create a payment via Yookassa
        payment = Payment.create({
            "amount": {
                "value": f"{amount:.2f}",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "https://t.me/profspay_bot"
            },
            "capture": True,
            "description": description
        }, uuid.uuid4())

        confirmation_url = payment.confirmation.confirmation_url
        payment_id = payment.id

        # Get current date and time
        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        time_now = now.strftime("%H:%M:%S")

        # Store payment details in the database
        con = sqlite3.connect("database/chats.db")
        cur = con.cursor()
        cur.execute("""
            INSERT INTO payments (user_id, first_name, payment_id, date, time, amount, status) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (message.chat.id, message.from_user.first_name, payment_id, date, time_now, amount, "pending"))
        con.commit()
        con.close()

        # Send payment link and payment ID to the admin
        bot.send_message(
            message.chat.id,
            f"Платеж создан.\n"
            f"Сумма: {amount} RUB\n"
            f"Описание: {description}\n"
            f"ID платежа: {payment_id}\n"
            f"Ссылка для оплаты: {confirmation_url}"
        )
    except Exception as e:
        bot.send_message(message.chat.id, "Произошла ошибка при создании платежа.")
        print(f"Error creating admin payment: {e}")


@bot.message_handler(commands=['i_payed'])
def verify_payment(message):
    try:
        # Get payment details from the user
        user_id = message.chat.id

        # Verify payment ID
        con = sqlite3.connect("payments.db")
        cur = con.cursor()
        cur.execute("SELECT payment_id, confirmation_url, description, amount FROM payments WHERE paid_count = 0")
        payment = cur.fetchone()
        con.close()

        if not payment:
            bot.send_message(message.chat.id, "Нет активного платежа для проверки.")
            return

        payment_id, confirmation_url, description, amount = payment

        # Fetch payment details from Yookassa
        yk_payment = Payment.find_one(payment_id)
        if yk_payment.status == "succeeded":
            # Update the paid_count in the database
            con = sqlite3.connect("payments.db")
            cur = con.cursor()
            cur.execute("""
                UPDATE payments SET paid_count = paid_count + 1 WHERE payment_id = ?
            """, (payment_id,))
            con.commit()
            con.close()

            bot.send_message(
                user_id,
                f"Оплата успешно завершена!\n"
                f"ID платежа: {payment_id}\n"
                f"Сумма: {amount} RUB\n"
                f"Описание: {description}"
            )
        else:
            bot.send_message(user_id, f"Оплата еще не завершена. Статус: {yk_payment.status}")
    except Exception as e:
        bot.send_message(message.chat.id, "Произошла ошибка при проверке платежа.")
        print(f"Error verifying payment: {e}")


@bot.message_handler(commands=['who_paid'])
def who_paid(message):
    try:
        if not is_admin(message.chat.id):
            bot.send_message(message.chat.id, "У вас нет прав для использования этой команды.")
            return

        # Query all payments with paid_count > 0
        con = sqlite3.connect("payments.db")
        cur = con.cursor()
        cur.execute("""
            SELECT payment_id, description, amount, paid_count FROM payments WHERE paid_count > 0
        """)
        payments = cur.fetchall()
        con.close()

        if not payments:
            bot.send_message(message.chat.id, "Нет данных об оплатах.")
            return

        # Format and send the list
        response = "Список оплаченных платежей:\n\n"
        for payment_id, description, amount, paid_count in payments:
            response += f"ID: {payment_id}\nОписание: {description}\nСумма: {amount} RUB\nОплатило: {paid_count}\n\n"

        bot.send_message(message.chat.id, response)
    except Exception as e:
        bot.send_message(message.chat.id, "Произошла ошибка при получении списка оплативших.")
        print(f"Error retrieving paid users: {e}")


@bot.message_handler(commands=['broadcast_payment'])
def broadcast_payment(message):
    try:
        if not is_admin(message.chat.id):
            bot.send_message(message.chat.id, "У вас нет прав для использования этой команды.")
            return

        # Get the payment ID from the command
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            bot.send_message(message.chat.id, "Укажите ID платежа для рассылки.")
            return

        payment_id = args[1]

        # Retrieve payment details
        con = sqlite3.connect("payments.db")
        cur = con.cursor()
        cur.execute("""
            SELECT confirmation_url, description, amount FROM payments WHERE payment_id = ?
        """, (payment_id,))
        payment = cur.fetchone()
        con.close()

        if not payment:
            bot.send_message(message.chat.id, "Платеж с указанным ID не найден.")
            return

        confirmation_url, description, amount = payment

        # Retrieve all users from the user database
        con = sqlite3.connect("database/chats.db")
        cur = con.cursor()
        cur.execute("SELECT id FROM id")
        users = cur.fetchall()
        con.close()

        for user in users:
            try:
                bot.send_message(
                    user[0],
                    f"Новый платеж:\nОписание: {description}\nСумма: {amount} RUB\n"
                    f"Оплатить можно по ссылке: {confirmation_url}"
                )
            except Exception as e:
                print(f"Error sending message to user {user[0]}: {e}")

        bot.send_message(message.chat.id, "Рассылка платежа завершена.")
    except Exception as e:
        bot.send_message(message.chat.id, "Произошла ошибка при рассылке.")
        print(f"Error broadcasting payment: {e}")


if __name__ == '__main__':
    bot.polling()
