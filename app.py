import os
import re
import requests

from flask import Flask, request


app = Flask(__name__)


# =========================================================
# НАСТРОЙКИ
# =========================================================

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
YCLIENTS_USER_TOKEN = os.environ["YCLIENTS_USER_TOKEN"]

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
YCLIENTS_API = "https://api.yclients.ru/api/v1"


BRANCHES = {
    "Нагатинская": {
        "company_id": 558795,
        "booking_url": "https://n591306.yclients.ru",
    },
    "Беломорская": {
        "company_id": 647846,
        "booking_url": "https://n685581.yclients.ru",
    },
    "Базовская": {
        "company_id": 594760,
        "booking_url": "https://n629339.yclients.ru",
    },
    "Истринская": {
        "company_id": 689709,
        "booking_url": "https://n731690.yclients.ru",
    },
}


# =========================================================
# TELEGRAM
# =========================================================

def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json=payload,
            timeout=15,
        )
    except Exception as e:
        print("Telegram send_message error:", e)


def main_keyboard():
    return {
        "keyboard": [
            [
                {"text": "🏊 Записаться"},
                {"text": "🎟️ Мой абонемент"},
            ],
            [
                {"text": "📅 Мои записи"},
                {"text": "💬 Связаться с нами"},
            ],
        ],
        "resize_keyboard": True,
    }


def branch_keyboard():
    return {
        "keyboard": [
            [
                {"text": "Нагатинская"},
                {"text": "Беломорская"},
            ],
            [
                {"text": "Базовская"},
                {"text": "Истринская"},
            ],
            [
                {"text": "← Назад"},
            ],
        ],
        "resize_keyboard": True,
    }


def phone_keyboard():
    return {
        "keyboard": [
            [
                {
                    "text": "📱 Поделиться номером телефона",
                    "request_contact": True,
                }
            ],
            [
                {"text": "← Назад"},
            ],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }


def booking_button(branch_name):
    branch = BRANCHES[branch_name]

    return {
        "inline_keyboard": [
            [
                {
                    "text": f"Записаться — {branch_name}",
                    "url": branch["booking_url"],
                }
            ]
        ]
    }


# =========================================================
# YCLIENTS
# =========================================================

def normalize_phone(phone):
    digits = re.sub(r"\D", "", phone or "")

    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]

    elif len(digits) == 10:
        digits = "7" + digits

    return digits


def yclients_headers():
    return {
        "Authorization": f"Bearer {YCLIENTS_USER_TOKEN}",
        "Accept": "application/vnd.yclients.v2+json",
        "Content-Type": "application/json",
    }


def search_client_in_branch(company_id, phone):
    url = f"{YCLIENTS_API}/company/{company_id}/clients/search"

    body = {
        "page": 1,
        "page_size": 10,
        "fields": [
            "id",
            "name",
            "phone",
        ],
        "operation": "AND",
        "filters": [
            {
                "type": "quick_search",
                "state": {
                    "value": phone
                },
            }
        ],
    }

    try:
        response = requests.post(
            url,
            headers=yclients_headers(),
            json=body,
            timeout=15,
        )

        result = {
            "ok": response.ok,
            "status": response.status_code,
            "clients": [],
        }

        if not response.ok:
            print(
                "YCLIENTS error:",
                company_id,
                response.status_code,
                response.text,
            )
            return result

        data = response.json().get("data", [])

        if isinstance(data, list):
            clients = data

        elif isinstance(data, dict):
            clients = data.get("items", [])

        else:
            clients = []

        result["clients"] = clients

        return result

    except Exception as e:
        print("YCLIENTS request error:", company_id, e)

        return {
            "ok": False,
            "status": "error",
            "clients": [],
        }


def find_client_everywhere(phone):
    phone = normalize_phone(phone)

    found = []
    errors = {}

    for branch_name, branch in BRANCHES.items():
        result = search_client_in_branch(
            branch["company_id"],
            phone,
        )

        if not result["ok"]:
            errors[branch_name] = result["status"]
            continue

        for client in result["clients"]:
            client_phone = normalize_phone(
                str(client.get("phone", ""))
            )

            if client_phone == phone:
                found.append(
                    {
                        "branch": branch_name,
                        "client": client,
                    }
                )
                break

    return found, errors


# =========================================================
# ПРОВЕРКА СЕРВЕРА
# =========================================================

@app.route("/", methods=["GET"])
def home():
    return "Kapitan Bulk bot is running", 200


# =========================================================
# YCLIENTS REGISTRATION REDIRECT
# =========================================================

@app.route("/yclients/connect", methods=["GET"])
def yclients_connect():
    salon_id = request.args.get("salon_id")

    if not salon_id:
        return "YCLIENTS: salon_id не передан", 400

    print("YCLIENTS salon_id received:", salon_id)

    return (
        f"YCLIENTS подключение получено. salon_id={salon_id}",
        200,
    )


# =========================================================
# TELEGRAM WEBHOOK
# =========================================================

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


    # -----------------------------------------------------
    # ПОЛЬЗОВАТЕЛЬ ОТПРАВИЛ ТЕЛЕФОН
    # -----------------------------------------------------

    if contact:
        phone = contact.get("phone_number", "")

        send_message(
            chat_id,
            "Ищу вас в базе Капитана Булька… 🦭",
            main_keyboard(),
        )

        found, errors = find_client_everywhere(phone)

        if found:
            branches = "\n".join(
                f"• {item['branch']}"
                for item in found
            )

            send_message(
                chat_id,
                "Нашёл вас в YCLIENTS ✅\n\n"
                f"Вы найдены в филиалах:\n{branches}",
                main_keyboard(),
            )

            return "ok", 200

        if errors:
            error_text = "\n".join(
                f"{branch}: {status}"
                for branch, status in errors.items()
            )

            send_message(
                chat_id,
                "YCLIENTS пока не дал получить клиентскую базу.\n\n"
                "Коды ответа:\n"
                f"{error_text}\n\n"
                "Пришлите мне этот экран — по коду сразу поймём, "
                "что нужно поправить.",
                main_keyboard(),
            )

            return "ok", 200

        send_message(
            chat_id,
            "По этому номеру пока не нашёл клиента в YCLIENTS.",
            main_keyboard(),
        )

        return "ok", 200


    # -----------------------------------------------------
    # /START
    # -----------------------------------------------------

    if text == "/start":
        send_message(
            chat_id,
            "Привет! 🦭\n"
            "Я Капитан Бульк — ваш помощник 💙\n\n"
            "Здесь можно записаться на занятие, "
            "посмотреть свои записи и узнать информацию "
            "об абонементе.",
            main_keyboard(),
        )

        return "ok", 200


    # -----------------------------------------------------
    # ЗАПИСАТЬСЯ
    # -----------------------------------------------------

    if text == "🏊 Записаться":
        send_message(
            chat_id,
            "Выберите филиал 👇",
            branch_keyboard(),
        )

        return "ok", 200


    # -----------------------------------------------------
    # ВЫБОР ФИЛИАЛА
    # -----------------------------------------------------

    if text in BRANCHES:
        send_message(
            chat_id,
            f"Вы выбрали филиал «{text}» 💙",
            booking_button(text),
        )

        return "ok", 200


    # -----------------------------------------------------
    # МОИ ЗАПИСИ
    # -----------------------------------------------------

    if text == "📅 Мои записи":
        send_message(
            chat_id,
            "Чтобы найти вас в YCLIENTS, "
            "поделитесь номером телефона 👇",
            phone_keyboard(),
        )

        return "ok", 200


    # -----------------------------------------------------
    # МОЙ АБОНЕМЕНТ
    # -----------------------------------------------------

    if text == "🎟️ Мой абонемент":
        send_message(
            chat_id,
            "Чтобы найти ваш абонемент в YCLIENTS, "
            "поделитесь номером телефона 👇",
            phone_keyboard(),
        )

        return "ok", 200


    # -----------------------------------------------------
    # СВЯЗАТЬСЯ
    # -----------------------------------------------------

    if text == "💬 Связаться с нами":
        send_message(
            chat_id,
            "Здесь скоро появятся контакты администратора 💙",
            main_keyboard(),
        )

        return "ok", 200


    # -----------------------------------------------------
    # НАЗАД
    # -----------------------------------------------------

    if text == "← Назад":
        send_message(
            chat_id,
            "Выберите нужный раздел 👇",
            main_keyboard(),
        )

        return "ok", 200


    # -----------------------------------------------------
    # ЕСЛИ НЕ ПОНЯЛИ СООБЩЕНИЕ
    # -----------------------------------------------------

    send_message(
        chat_id,
        "Выберите нужный раздел 👇",
        main_keyboard(),
    )

    return "ok", 200


# =========================================================
# ЛОКАЛЬНЫЙ ЗАПУСК
# =========================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
    )
