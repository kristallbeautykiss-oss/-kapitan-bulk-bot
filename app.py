import os
from flask import Flask, request
import requests

app = Flask(__name__)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

BRANCH_URLS = {
    "Нагатинская": "https://n591306.yclients.ru",
    "Беломорская": "https://n685581.yclients.ru",
    "Базовская": "https://n629339.yclients.ru",
    "Истринская": "https://n731690.yclients.ru",
}


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


def send_message(chat_id, text, keyboard=None, inline_keyboard=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if inline_keyboard:
        payload["reply_markup"] = {
            "inline_keyboard": inline_keyboard
        }
    else:
        if keyboard is None:
            keyboard = MAIN_KEYBOARD

        payload["reply_markup"] = keyboard

    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json=payload,
        timeout=10
    )


@app.get("/")
def home():
    return "Kapitan Bulk bot is running", 200


@app.post("/telegram")
def telegram_webhook():
    update = request.get_json(silent=True) or {}
    message = update.get("message")

    if not message:
        return "ok", 200

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

    elif text.startswith("📍 "):
        branch = text.replace("📍 ", "")

        if branch in BRANCH_URLS:
            send_message(
                chat_id,
                f"Вы выбрали филиал «{branch}» 🦭\n\n"
                "Нажмите кнопку ниже, чтобы перейти к записи:",
                inline_keyboard=[
                    [
                        {
                            "text": f"🏊 Записаться — {branch}",
                            "url": BRANCH_URLS[branch]
                        }
                    ]
                ]
            )
        else:
            send_message(
                chat_id,
                "Не удалось найти этот филиал.",
                BRANCH_KEYBOARD
            )

    elif text == "🎟 Мой абонемент":
        send_message(
            chat_id,
            "Скоро здесь можно будет посмотреть остаток занятий по абонементу 🦭"
        )

    elif text == "📅 Мои записи":
        send_message(
            chat_id,
            "Скоро здесь будут отображаться ваши ближайшие записи 🦭"
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
