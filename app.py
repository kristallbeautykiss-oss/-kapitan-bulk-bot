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
        timeout=15
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
    return {
        "inline_keyboard": [
            [
                {
                    "text": f"🏊 Записаться — {branch_name}",
                    "url": BRANCHES[branch_name]["booking_url"]
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
# YCLIENTS
# =========================

def yclients_headers():
    return {
        "Authorization": f"Bearer {YCLIENTS_USER_TOKEN}",
        "Accept": "application/vnd.yclients.v2+json",
        "Content-Type": "application/json"
    }


def search_client_in_branch(company_id, phone):
    url = f"{YCLIENTS_API}/company/{company_id}/clients/search"

    body = {
        "page": 1,
        "page_size": 10,
        "fields": [
            "id",
            "name",
            "phone"
        ],
        "operation": "AND",
        "filters": [
            {
                "type": "quick_search",
                "state": {
                    "value": phone
                }
            }
        ]
    }

    try:
        response = requests.post(
            url,
            headers=yclients_headers(),
            json=body,
            timeout=15
        )

        if response.status_code != 200:
            return {
                "ok": False,
                "status": response.status_code,
                "clients": []
            }

        data = response.json()

        clients = []

        if isinstance(data, dict):
            raw_clients = data.get("data", [])

            if isinstance(raw_clients, dict):
                raw_clients = raw_clients.get("items", [])

            if isinstance(raw_clients, list):
                clients = raw_clients

        return {
            "ok": True,
            "status": 200,
            "clients": clients
        }

    except Exception:
        return {
            "ok": False,
            "status": 0,
            "clients": []
        }


def find_client_everywhere(phone):
    found = []
    errors = []

    for branch_name, branch in BRANCHES.items():
        result = search_client_in_branch(
            branch["company_id"],
            phone
        )

        if not result["ok"]:
            errors.append(
                f'{branch_name}: {result["status"]}'
            )
            continue

        for client in result["clients"]:
            client_phone = normalize_phone(
                str(client.get("phone", ""))
            )

            if client_phone == phone:
                found.append({
                    "branch": branch_name,
                    "company_id": branch["company_id"],
                    "client_id": client.get("id"),
                    "name": client.get("name") or "Клиент"
                })

    return found, errors


# =========================
# HEALTH CHECK
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

    chat_id = message.get("chat", {}).get("id")

    if not chat_id:
        return "ok", 200

    text = message.get("text", "")
    contact = message.get("contact")


    # -------------------------
    # ПОЛУЧИЛИ ТЕЛЕФОН
    # -------------------------

    if contact:
        phone = normalize_phone(
            contact.get("phone_number")
        )

        if not phone:
            send_message(
                chat_id,
                "Не получилось определить номер телефона.",
                phone_keyboard()
            )
            return "ok", 200

        send_message(
            chat_id,
            "Ищу вас в базе Капитана Булька… 🦭"
        )

        clients, errors = find_client_everywhere(phone)

        if clients:
            branches = []

            for client in clients:
                branches.append(
                    f'• {client["branch"]}'
                )

            branches_text = "\n".join(branches)

            send_message(
                chat_id,
                "Нашёл вас в YCLIENTS ✅\n\n"
                f"{branches_text}\n\n"
                "Отлично! Теперь можем подключать "
                "ваши будущие записи.",
                main_keyboard()
            )

        elif errors:
            error_text = "\n".join(errors)

            send_message(
                chat_id,
                "YCLIENTS пока не дал получить клиентскую базу.\n\n"
                "Коды ответа:\n"
                f"{error_text}\n\n"
                "Пришлите мне этот экран — "
                "по коду сразу поймём, что нужно поправить.",
                main_keyboard()
            )

        else:
            send_message(
                chat_id,
                "Не нашёл клиента с таким номером "
                "ни в одном из четырёх филиалов.\n\n"
                "Проверьте, что в YCLIENTS указан "
                "тот же номер телефона.",
                main_keyboard()
            )

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
            "посмотреть свои записи и узнать "
            "информацию об абонементе.",
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
    # ФИЛИАЛ
    # -------------------------

    if text.startswith("📍 "):
        branch_name = text.replace(
            "📍 ",
            "",
            1
        ).strip()

        if branch_name in BRANCHES:
            send_message(
                chat_id,
                f"Вы выбрали филиал «{branch_name}» 🦭\n\n"
                "Нажмите кнопку ниже, чтобы перейти к записи:",
                booking_button(branch_name)
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
