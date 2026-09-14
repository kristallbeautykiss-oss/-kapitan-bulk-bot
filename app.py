import os
import re
import requests

from flask import Flask, request


app = Flask(__name__)


# =========================
# НАСТРОЙКИ
# =========================

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
YCLIENTS_USER_TOKEN = os.environ["YCLIENTS_USER_TOKEN"]

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

YCLIENTS_API = "https://api.yclients.ru/api/v1"


BRANCHES = {
    "Нагатинская": {
        "company_id": 558795,
        "booking_url": "https://n591306.yclients.ru"
    },
    "Беломорская": {
        "company_id": 647846,
        "booking_url": "https://n685581.yclients.ru"
    },
    "Базовская": {
        "company_id": 594760,
        "booking_url": "https://n629339.yclients.ru"
    },
    "Истринская": {
        "company_id": 689709,
        "booking_url": "https://n731690.yclients.ru"
    }
}


# =========================
# TELEGRAM
# =========================

def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json=payload,
        timeout=10
    )


def main_keyboard():
    return {
        "keyboard": [
            [
                {"text": "🏊 Записаться"},
                {"text": "🎟️ Мой абонемент"}
            ],
            [
                {"text": "📅 Мои записи"},
                {"text": "💬 Связаться с нами"}
            ]
        ],
        "resize_keyboard": True
    }


def branch_keyboard():
    return {
        "keyboard": [
            [
                {"text": "📍 Нагатинская"},
                {"text": "📍 Беломорская"}
            ],
            [
                {"text": "📍 Базовская"},
                {"text": "📍 Истринская"}
            ],
            [
                {"text": "← Назад"}
            ]
        ],
        "resize_keyboard": True
    }


def phone_keyboard():
    return {
        "keyboard": [
            [
                {
                    "text": "📱 Поделиться номером телефона",
                    "request_contact": True
                }
            ],
            [
                {"text": "← Назад"}
            ]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }


def booking_button(branch_name):
    branch = BRANCHES[branch_name]

    return {
        "inline_keyboard": [
            [
                {
                    "text": f"🏊 Записаться — {branch_name}",
                    "url": branch["booking_url"]
                }
            ]
        ]
    }


def normalize_phone(phone):
    digits = re.sub(r"\D", "", phone or "")

    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]

    if len(digits) == 10:
        digits = "7" + digits

    return digits


# =========================
# СТРАНИЦА ПРОВЕРКИ RENDER
# =========================

@app.route("/", methods=["GET"])
def home():
    return "Kapitan Bulk bot is running", 200


# =========================
# TELEGRAM WEBHOOK
# =========================

@app.route("/telegram", methods=["POST"])
def telegram_webhook():
    update = request.get_json(silent=True) or {}

    message = update.get("message")

    if not message:
        return "ok", 200

    chat = message.get("chat", {})
    chat_id = chat.get("id")

    if not chat_id:
        return "ok", 200

    text = message.get("text", "")
    contact = message.get("contact")


    # -------------------------
    # ПОЛУЧИЛИ НОМЕР ТЕЛЕФОНА
    # -------------------------

    if contact:
        phone = normalize_phone(contact.get("phone_number"))

        if not phone:
            send_message(
                chat_id,
                "Не получилось определить номер телефона. Попробуйте ещё раз.",
                phone_keyboard()
            )

            return "ok", 200

        send_message(
            chat_id,
            "Спасибо! Номер получен ✅\n\n"
            "Следующим шагом подключаем поиск ваших данных в YCLIENTS 🦭",
            main_keyboard()
        )

        # Здесь следующим шагом подключим:
        # 1. поиск клиента по телефону во всех 4 филиалах
        # 2. получение будущих записей
        # 3. получение информации по абонементу

        return "ok", 200


    # -------------------------
    # START
    # -------------------------

    if text == "/start":
        send_message(
            chat_id,
            "Привет! 🦭\n\n"
            "Я Капитан Бульк — ваш помощник 💙\n\n"
            "Здесь можно записаться на занятие, "
            "посмотреть свои записи и узнать информацию об абонементе.",
            main_keyboard()
        )

        return "ok", 200


    # -------------------------
    # ЗАПИСАТЬСЯ
    # -------------------------

    if text == "🏊 Записаться":
        send_message(
            chat_id,
            "Выберите филиал 👇",
            branch_keyboard()
        )

        return "ok", 200


    # -------------------------
    # ВЫБОР ФИЛИАЛА
    # -------------------------

    if text.startswith("📍 "):
        branch_name = text.replace("📍 ", "", 1).strip()

        if branch_name in BRANCHES:
            send_message(
                chat_id,
                f"Вы выбрали филиал «{branch_name}» 🦭\n\n"
                "Нажмите кнопку ниже, чтобы перейти к записи:",
                booking_button(branch_name)
            )

        else:
            send_message(
                chat_id,
                "Не получилось определить филиал.",
                main_keyboard()
            )

        return "ok", 200


    # -------------------------
    # МОИ ЗАПИСИ
    # -------------------------

    if text == "📅 Мои записи":
        send_message(
            chat_id,
            "Чтобы найти вас в YCLIENTS, "
            "поделитесь номером телефона 👇",
            phone_keyboard()
        )

        return "ok", 200


    # -------------------------
    # МОЙ АБОНЕМЕНТ
    # -------------------------

    if text == "🎟️ Мой абонемент":
        send_message(
            chat_id,
            "Чтобы найти ваш абонемент в YCLIENTS, "
            "поделитесь номером телефона 👇",
            phone_keyboard()
        )

        return "ok", 200


    # -------------------------
    # СВЯЗАТЬСЯ
    # -------------------------

    if text == "💬 Связаться с нами":
        send_message(
            chat_id,
            "Напишите нам, и администратор поможет вам 💙",
            main_keyboard()
        )

        return "ok", 200


    # -------------------------
    # НАЗАД
    # -------------------------

    if text == "← Назад":
        send_message(
            chat_id,
            "Главное меню 🦭",
            main_keyboard()
        )

        return "ok", 200


    # -------------------------
    # НЕИЗВЕСТНАЯ КОМАНДА
    # -------------------------

    send_message(
        chat_id,
        "Выберите нужный раздел 👇",
        main_keyboard()
    )

    return "ok", 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
