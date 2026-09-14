import os

from flask import Flask, request
import requests

app = Flask(__name__)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(chat_id, text):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "reply_markup": {
                "keyboard": [
                    [{"text": "🏊 Записаться"}],
                    [{"text": "🎟 Мой абонемент"}, {"text": "📅 Мои записи"}],
                    [{"text": "💬 Связаться с нами"}]
                ],
                "resize_keyboard": True
            }
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
                "Здесь можно записаться на занятие, посмотреть свои записи "
                "и узнать информацию об абонементе."
            )
        else:
            send_message(chat_id, "Выберите нужный раздел 👇")

    return "ok", 200
