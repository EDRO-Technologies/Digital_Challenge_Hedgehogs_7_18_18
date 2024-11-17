import functools
import sqlite3
import traceback
import uuid
from datetime import datetime

from main import ACCOUNT_ID, bot, create_payment_for_all
from flask import Flask, render_template, request, session, jsonify, redirect
from yookassa import Payment

from main import is_admin, bot

app = Flask(__name__, template_folder='./templates')


def error_handler(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            error_message = f"Error: {str(e)}\n{traceback.format_exc()}"
            return {'status': 'error', 'message': 'An error occurred'}, 500

    return decorated_function


app.secret_key = 'your_secret_key'  # Настройте секретный ключ для сессий

@app.route('/save_user_id', methods=['POST'])
def save_user_id():
    try:
        data = request.get_json()
        user_id = data.get('user_id')

        if user_id:
            session['user_id'] = user_id

            return jsonify({'status': 'success', 'user_id': user_id}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Invalid user_id'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'trace': traceback.format_exc()}), 500


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/payment')
def payment():
    user_id = session['user_id']
    if not is_admin(user_id):
        con = sqlite3.connect("database/payments.db")
        cur = con.cursor()
        cur.execute("""
            SELECT confirmation_url, payment_id, amount, description, status FROM payment_users WHERE user_id = ?
        """, (user_id,))
        user_payment = cur.fetchone()
        con.close()

        if user_payment:
            confirmation_url, payment_id, amount, description, status = user_payment

            if payment_id:
                payment = Payment.find_one(payment_id)
                if payment.status == "succeeded":
                    return render_template('finishPayment.html')
            else:
                return render_template('finishPayment.html')

            return render_template(
                'payment.html',
                cost_price=amount,
                info_text_org_title="Название организации",
                info_text_org="Профсоюз",
                info_text_aim_title="Цель сборов",
                info_text_aim=description,
                payment_link=confirmation_url,
                button_text="Оплатить"
            )
        else:
            return "Пользователь не найден", 404
    else:
        return redirect('/admin')


@app.route('/admin', methods=['GET', 'POST'])
def create_payment():
    user_id = session['user_id']
    if is_admin(user_id):
        return render_template('fee.html')
    else:
        return "У вас нет прав для просмотра этой страницы", 403


@app.route('/finishFee', methods=['POST', 'GET'])
def finish_fee():
    if request.method == 'POST':
        data = request.json
        session["cost"] = data.get('cost')
        session["org"] = data.get('org')
        session["aim"] = data.get('aim')

        return jsonify({'message': 'Data received successfully'})

    if request.method == 'GET':
        return render_template('finishFee.html')


@app.route('/spamFee', methods=['POST', 'GET'])
def spam_fee():
    if request.method == 'POST':
        data = request.json
        return jsonify({'message': 'Data received successfully'})
    if request.method == 'GET':
        c = session["cost"]
        a = session["aim"]
        create_payment_for_all(c, a)
        return render_template('finishFinishFee.html')


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port='5000')
