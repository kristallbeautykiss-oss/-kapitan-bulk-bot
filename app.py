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
YCLIENTS_PARTNER_TOKEN = os.environ["YCLIENTS_PARTNER_TOKEN"]

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

YCLIENTS_API = "https://api.yclients.ru/api/v1"
YCLIENTS_MARKETPLACE_API = "https://api.yclients.ru"

APPLICATION_ID = 51162

YCLIENTS_WEBHOOK_URL = (
    "https://kapitan-bulk-bot.onrender.com/yclients/webhook"
)

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


# =========================
# TELEGRAM
# =========================

def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json=payload,
        timeout=20,
    )


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
            [{"text": "← Назад"}],
        ],
        "resize_keyboard": True,
    }


def phone_keyboard():
    return {
        "keyboard": [
            [
                {
                    "text": "📱 Отправить мой номер",
                    "request_contact": True,
                }
            ],
            [{"text": "← Назад"}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }


def booking_button(url):
    return {
        "inline_keyboard": [
            [
                {
                    "text": "Записаться онлайн",
                    "url": url,
                }
            ]
        ]
    }


# =========================
# ТЕЛЕФОН
# =========================

def normalize_phone(phone):
    digits = re.sub(r"\D", "", phone or "")

    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]

    if len(digits) == 10:
        digits = "7" + digits

    return digits


# =========================
# YCLIENTS — АВТОРИЗАЦИЯ
# =========================

def yclients_user_headers():
    return {
        "Authorization": f"Bearer {YCLIENTS_USER_TOKEN}",
        "Accept": "application/vnd.yclients.v2+json",
        "Content-Type": "application/json",
    }


def yclients_partner_headers():
    return {
        "Authorization": f"Bearer {YCLIENTS_PARTNER_TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


# =========================
# YCLIENTS — АКТИВАЦИЯ
# =========================

def activate_yclients_branch(salon_id):
    url = (
        f"{YCLIENTS_MARKETPLACE_API}"
        f"/marketplace/partner/callback"
    )

    payload = {
        "salon_id": int(salon_id),
        "application_id": APPLICATION_ID,
        "webhook_urls": [
            YCLIENTS_WEBHOOK_URL
        ],
    }

    response = requests.post(
        url,
        headers=yclients_partner_headers(),
        json=payload,
        timeout=30,
    )

    print(
        "YCLIENTS ACTIVATION:",
        salon_id,
        response.status_code,
        response.text[:1000],
    )

    return response


# =========================
# YCLIENTS — ПОИСК КЛИЕНТА
# =========================

def search_client_in_branch(company_id, phone):
    url = (
        f"{YCLIENTS_API}"
        f"/company/{company_id}/clients/search"
    )

    payload = {
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
            headers=yclients_user_headers(),
            json=payload,
            timeout=30,
        )

        print(
            "CLIENT SEARCH:",
            company_id,
            response.status_code,
            response.text[:500],
        )

        if response.status_code != 200:
            return {
                "ok": False,
                "status": response.status_code,
                "clients": [],
            }

        data = response.json()

        clients = data.get("data", [])

        return {
            "ok": True,
            "status": 200,
            "clients": clients,
        }

    except Exception as e:
        print(
            "YCLIENTS client search error:",
            company_id,
            e,
        )

        return {
            "ok": False,
            "status": "error",
            "clients": [],
        }


def find_client_everywhere(phone):
    results = []
    errors = []

    normalized = normalize_phone(phone)

    for branch_name, branch_data in BRANCHES.items():
        company_id = branch_data["company_id"]

        result = search_client_in_branch(
            company_id,
            normalized,
        )

        if not result["ok"]:
            errors.append(
                (
                    branch_name,
                    result["status"],
                )
            )
            continue

        for client in result["clients"]:
            client_phone = normalize_phone(
                str(client.get("phone", ""))
            )

            if client_phone == normalized:
                results.append(
                    {
                        "branch": branch_name,
                        "client": client,
                    }
                )

    return results, errors


# =========================
# ГЛАВНАЯ
# =========================

@app.route("/", methods=["GET"])
def home():
    return "Kapitan Bulk bot is running", 200


# =========================
# YCLIENTS — ПОДКЛЮЧЕНИЕ
# =========================

@app.route("/yclients/connect", methods=["GET"])
def yclients_connect():
    salon_ids = []

    salon_id = request.args.get("salon_id")

    if salon_id:
        salon_ids.append(salon_id)

    salon_ids_array = request.args.getlist(
        "salon_ids[]"
    )

    if salon_ids_array:
        salon_ids.extend(salon_ids_array)

    if not salon_ids:
        print(
            "YCLIENTS CONNECT PARAMS:",
            dict(request.args),
        )

        return (
            "YCLIENTS не передал salon_id. "
            "Попробуйте подключить приложение заново.",
            400,
        )

    activation_results = []

    for current_salon_id in salon_ids:
        try:
            response = activate_yclients_branch(
                current_salon_id
            )

            activation_results.append(
                {
                    "salon_id": current_salon_id,
                    "status": response.status_code,
                    "body": response.text[:500],
                }
            )

        except Exception as e:
            print(
                "YCLIENTS activation error:",
                current_salon_id,
                e,
            )

            activation_results.append(
                {
                    "salon_id": current_salon_id,
                    "status": "error",
                    "body": str(e),
                }
            )

    success = all(
        item["status"] in (
            200,
            201,
        )
        for item in activation_results
    )

    if success:
        return (
            """
            <html>
            <head>
                <meta charset="utf-8">
                <title>Капитан Бульк!</title>
            </head>
            <body style="
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
            ">
                <h2>Готово! 🦭</h2>
                <p>
                    Капитан Бульк успешно подключён
                    к YCLIENTS.
                </p>
                <p>
                    Эту страницу можно закрыть.
                </p>
            </body>
            </html>
            """,
            200,
        )

    print(
        "YCLIENTS ACTIVATION RESULTS:",
        activation_results,
    )

    statuses = ", ".join(
        f'{item["salon_id"]}: '
        f'{item["status"]}'
        for item in activation_results
    )

    return (
        "YCLIENTS не удалось активировать "
        f"интеграцию. Коды: {statuses}",
        500,
    )


# =========================
# YCLIENTS — WEBHOOK
# =========================

@app.route(
    "/yclients/webhook",
    methods=["POST"],
)
def yclients_webhook():
    try:
        data = request.get_json(
            silent=True
        )

        print(
            "YCLIENTS WEBHOOK RECEIVED"
        )

        print(data)

        return "ok", 200

    except Exception as e:
        print(
            "YCLIENTS webhook error:",
            e,
        )

        return "ok", 200


# =========================
# TELEGRAM WEBHOOK
# =========================

@app.route(
    "/telegram",
    methods=["POST"],
)
def telegram_webhook():
    update = request.get_json(
        silent=True
    ) or {}

    message = update.get("message")

    if not message:
        return "ok", 200

    chat = message.get("chat", {})
    chat_id = chat.get("id")

    if not chat_id:
        return "ok", 200

    text = message.get(
        "text",
        ""
    )

    contact = message.get("contact")

    # ---------- CONTACT ----------

    if contact:
        phone = normalize_phone(
            contact.get(
                "phone_number",
                "",
            )
        )

        send_message(
            chat_id,
            "Ищу вас в базе "
            "Капитана Булька… 🦭",
        )

        results, errors = (
            find_client_everywhere(
                phone
            )
        )

        if results:
            branches = ", ".join(
                item["branch"]
                for item in results
            )

            names = [
                item["client"].get(
                    "name"
                )
                for item in results
                if item["client"].get(
                    "name"
                )
            ]

            name = (
                names[0]
                if names
                else "клиент"
            )

            send_message(
                chat_id,
                f"Нашла 💙\n\n"
                f"{name}, вы есть "
                f"в нашей базе.\n"
                f"Филиал: {branches}",
                main_keyboard(),
            )

            return "ok", 200

        if errors:
            error_text = "\n".join(
                f"{branch}: {status}"
                for branch, status
                in errors
            )

            send_message(
                chat_id,
                "YCLIENTS пока не дал "
                "получить клиентскую базу.\n\n"
                "Коды ответа:\n"
                f"{error_text}",
                main_keyboard(),
            )

            return "ok", 200

        send_message(
            chat_id,
            "Не нашла этот номер "
            "в клиентской базе.\n\n"
            "Проверьте, что в Telegram "
            "указан тот же номер, "
            "который вы оставляли "
            "при записи.",
            main_keyboard(),
        )

        return "ok", 200

    # ---------- START ----------

    if text == "/start":
        send_message(
            chat_id,
            "Привет! 🦭\n"
            "Я Капитан Бульк — "
            "ваш помощник 💙\n\n"
            "Здесь можно записаться "
            "на занятие, посмотреть "
            "свои записи и узнать "
            "информацию об абонементе.",
            main_keyboard(),
        )

        return "ok", 200

    # ---------- BOOKING ----------

    if text == "🏊 Записаться":
        send_message(
            chat_id,
            "Выберите филиал:",
            branch_keyboard(),
        )

        return "ok", 200

    if text in BRANCHES:
        branch = BRANCHES[text]

        send_message(
            chat_id,
            f"Вы выбрали филиал "
            f"«{text}» 💙",
            booking_button(
                branch["booking_url"]
            ),
        )

        return "ok", 200

    # ---------- MY RECORDS ----------

    if text == "📅 Мои записи":
        send_message(
            chat_id,
            "Чтобы найти ваши записи, "
            "отправьте номер телефона, "
            "который указан в YCLIENTS.",
            phone_keyboard(),
        )

        return "ok", 200

    # ---------- SUBSCRIPTION ----------

    if text == "🎟️ Мой абонемент":
        send_message(
            chat_id,
            "Чтобы найти ваш абонемент, "
            "отправьте номер телефона, "
            "который указан в YCLIENTS.",
            phone_keyboard(),
        )

        return "ok", 200

    # ---------- CONTACT US ----------

    if text == "💬 Связаться с нами":
        send_message(
            chat_id,
            "Напишите нам, и "
            "администратор поможет вам 💙",
            main_keyboard(),
        )

        return "ok", 200

    # ---------- BACK ----------

    if text == "← Назад":
        send_message(
            chat_id,
            "Главное меню 🦭",
            main_keyboard(),
        )

        return "ok", 200

    send_message(
        chat_id,
        "Выберите нужный пункт "
        "в меню 👇",
        main_keyboard(),
    )

    return "ok", 200


# =========================
# ЗАПУСК
# =========================

if __name__ == "__main__":
    port = int(
        os.environ.get(
            "PORT",
            10000,
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
    )
