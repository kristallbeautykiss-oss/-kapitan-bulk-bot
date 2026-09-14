import os
from flask import Flask, request
import requests

app = Flask(__name__)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


MAIN_KEYBOARD = {
    "keyboard": [
        [{"text": "🏊 Записаться"}],
        [
            {"text": "🎟 Мой абонемент"},
            {"text": "📅 Мои записи"}
        ],
        [{"text": "💬 Связаться с нами"}]
    ],
    "resize_keyboard": True
}


BRANCH_KEYBOARD = {
    "keyboard": [
        [
            {"text": "📍 Нагатинская"},
            {"text": "📍 Беломорская"}
        ],
        [
            {"text": "📍 Базовская"},
            {"text": "📍 Истринская"}
        ],
        [{"text": "← Назад"}]
    ],
    "resize_keyboard": True
}


def send_message(chat_id, text, keyboard=None):
    if keyboard is None:
        keyboard = MAIN_KEYBOARD

    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "reply_markup": keyboard
        },
        timeout=10
    )


@app.get("/")
def home():
    return "Kapitan Bulk bot is running", 200


@app.post("/telegram")
def telegram_webhook():
    update = request.get_json(silent=True) or {}

    message = update.get("message")

    if message:
        chat_id = message["chat"]["id"]
        text = message.get("text", "")

        if text == "/start":
            send_message(
                chat_id,
                "Привет! 🦭\n"
                "Я Капитан Бульк — ваш помощник 💙\n\n"
                "Здесь можно записаться на занятие, "
                "посмотреть свои записи и узнать "
                "информацию об абонементе."
            )

        elif text == "🏊 Записаться":
            send_message(
                chat_id,
                "Выберите филиал 👇",
                BRANCH_KEYBOARD
            )

        elif text == "← Назад":
            send_message(
                chat_id,
                "Главное меню 👇",
                MAIN_KEYBOARD
            )

        elif text in [
            "📍 Нагатинская",
            "📍 Беломорская",
            "📍 Базовская",
            "📍 Истринская"
        ]:
            branch = text.replace("📍 ", "")

            send_message(
                chat_id,
                f"Вы выбрали филиал «{branch}» 🦭\n\n"
                "Сейчас подключим запись через YCLIENTS.",
                BRANCH_KEYBOARD
            )

        elif text == "🎟 Мой абонемент":
            send_message(
                chat_id,
                "Раздел «Мой абонемент» скоро подключим к YCLIENTS 🦭"
            )

        elif text == "📅 Мои записи":
            send_message(
                chat_id,
                "Раздел «Мои записи» скоро подключим к YCLIENTS 🦭"
            )

        elif text == "💬 Связаться с нами":
            send_message(
                chat_id,
                "Здесь мы добавим контакты «Капитана Булька» 💙"
            )

        else:
            send_message(
                chat_id,
                "Выберите нужный раздел 👇"
            )

    return "ok", 200
