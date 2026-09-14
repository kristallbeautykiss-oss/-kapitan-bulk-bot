import os
import re
import requests

from datetime import date, timedelta, datetime
from flask import Flask, request


app = Flask(__name__)


# =========================================================
# НАСТРОЙКИ
# =========================================================

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
        "address": "Нагатинская, 16",
    },

    "Беломорская": {
        "company_id": 647846,
        "booking_url": "https://n685581.yclients.ru",
        "address": "Беломорская, 9",
    },

    "Базовская": {
        "company_id": 594760,
        "booking_url": "https://n629339.yclients.ru",
        "address": "Базовская, 15А",
    },

    "Истринская": {
        "company_id": 689709,
        "booking_url": "https://n731690.yclients.ru",
        "address": "Истринская, 5",
    },
}


# Запоминает, какую кнопку нажал пользователь:
# "records" — Мои записи
# "subscription" — Мой абонемент
PENDING_ACTIONS = {}


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
            timeout=20,
        )
    except Exception as e:
        print("TELEGRAM SEND ERROR:", e)


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
                {"text": "← Назад"}
            ],
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
            [
                {"text": "← Назад"}
            ],
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


# =========================================================
# ТЕЛЕФОН
# =========================================================

def normalize_phone(phone):
    digits = re.sub(r"\D", "", phone or "")

    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]

    if len(digits) == 10:
        digits = "7" + digits

    return digits


# =========================================================
# YCLIENTS — АВТОРИЗАЦИЯ
# =========================================================

def yclients_user_headers():
    return {
        "Authorization": (
            f"Bearer {YCLIENTS_PARTNER_TOKEN}, "
            f"User {YCLIENTS_USER_TOKEN}"
        ),
        "Accept": "application/vnd.yclients.v2+json",
        "Content-Type": "application/json",
    }


def yclients_partner_headers():
    return {
        "Authorization": f"Bearer {YCLIENTS_PARTNER_TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


# =========================================================
# YCLIENTS — АКТИВАЦИЯ ИНТЕГРАЦИИ
# =========================================================

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


# =========================================================
# YCLIENTS — ПОИСК КЛИЕНТА
# =========================================================

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
            response.text[:700],
        )

        if response.status_code != 200:
            return {
                "ok": False,
                "status": response.status_code,
                "clients": [],
            }

        data = response.json()

        clients = data.get("data", [])

        if isinstance(clients, dict):
            clients = (
                clients.get("clients")
                or clients.get("items")
                or []
            )

        if not isinstance(clients, list):
            clients = []

        return {
            "ok": True,
            "status": 200,
            "clients": clients,
        }

    except Exception as e:
        print(
            "YCLIENTS CLIENT SEARCH ERROR:",
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

    normalized_phone = normalize_phone(phone)

    for branch_name, branch_data in BRANCHES.items():
        company_id = branch_data["company_id"]

        result = search_client_in_branch(
            company_id,
            normalized_phone,
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
                str(
                    client.get(
                        "phone",
                        ""
                    )
                )
            )

            if client_phone == normalized_phone:
                results.append(
                    {
                        "branch": branch_name,
                        "company_id": company_id,
                        "client": client,
                    }
                )

    return results, errors


# =========================================================
# YCLIENTS — ПОЛУЧЕНИЕ ЗАПИСЕЙ
# =========================================================

def get_client_records(company_id, client_id):
    url = (
        f"{YCLIENTS_API}"
        f"/records/{company_id}"
    )

    today = date.today()
    end_day = today + timedelta(days=365)

    params = {
        "page": 1,
        "count": 100,
        "client_id": client_id,
        "start_date": today.isoformat(),
        "end_date": end_day.isoformat(),
    }

    try:
        response = requests.get(
            url,
            headers=yclients_user_headers(),
            params=params,
            timeout=30,
        )

        print(
            "RECORD SEARCH:",
            company_id,
            client_id,
            response.status_code,
            response.text[:1500],
        )

        if response.status_code != 200:
            return {
                "ok": False,
                "status": response.status_code,
                "records": [],
            }

        data = response.json()

        records = data.get("data", [])

        if isinstance(records, dict):
            records = (
                records.get("records")
                or records.get("items")
                or []
            )

        if not isinstance(records, list):
            records = []

        return {
            "ok": True,
            "status": 200,
            "records": records,
        }

    except Exception as e:
        print(
            "YCLIENTS RECORD SEARCH ERROR:",
            company_id,
            client_id,
            e,
        )

        return {
            "ok": False,
            "status": "error",
            "records": [],
        }


# =========================================================
# ДАТА И ВРЕМЯ ЗАПИСИ
# =========================================================

def record_datetime(record):
    value = (
        record.get("datetime")
        or record.get("date")
        or ""
    )

    if not value:
        return None

    try:
        clean_value = str(value).replace(
            "Z",
            "+00:00"
        )

        return datetime.fromisoformat(
            clean_value
        )

    except Exception:
        return None


# =========================================================
# ДЛИТЕЛЬНОСТЬ ЗАПИСИ
# =========================================================

def format_duration(record):
    length = record.get("length")

    if not length:
        return "не указана"

    try:
        seconds = int(length)

        minutes = seconds // 60

        if minutes <= 0:
            return "не указана"

        if minutes < 60:
            return f"{minutes} мин"

        hours = minutes // 60
        remaining_minutes = minutes % 60

        if remaining_minutes == 0:
            return f"{hours} ч"

        return (
            f"{hours} ч "
            f"{remaining_minutes} мин"
        )

    except (
        TypeError,
        ValueError,
    ):
        return "не указана"


# =========================================================
# КАРТОЧКА ЗАПИСИ
# =========================================================

def format_record(record, branch_name):
    dt = record_datetime(record)

    if dt:
        date_text = dt.strftime(
            "%d.%m.%Y"
        )

        time_text = dt.strftime(
            "%H:%M"
        )

    else:
        raw_date = str(
            record.get(
                "date",
                ""
            )
        )

        date_text = (
            raw_date
            if raw_date
            else "дата не указана"
        )

        time_text = ""

    staff = record.get("staff") or {}

    if isinstance(staff, dict):
        staff_name = (
            staff.get("name")
            or staff.get("title")
            or "не указан"
        )
    else:
        staff_name = (
            str(staff)
            if staff
            else "не указан"
        )

    duration_text = format_duration(
        record
    )

    address = (
        BRANCHES
        .get(
            branch_name,
            {}
        )
        .get(
            "address",
            branch_name,
        )
    )

    if time_text:
        when = (
            f"{date_text} "
            f"в {time_text}"
        )
    else:
        when = date_text

    return (
        "📅 Ваша запись\n\n"
        f"🗓 {when}\n"
        "🏊 Индивидуальная тренировка\n"
        f"👤 Тренер: {staff_name}\n"
        f"⏱ Длительность: {duration_text}\n"
        f"📍 {address}"
    )


# =========================================================
# СОБИРАЕМ БУДУЩИЕ ЗАПИСИ
# =========================================================

def get_future_records_for_clients(
    client_results
):
    all_records = []
    errors = []

    for item in client_results:
        branch_name = item["branch"]
        company_id = item["company_id"]
        client = item["client"]

        client_id = client.get("id")

        if not client_id:
            continue

        result = get_client_records(
            company_id,
            client_id,
        )

        if not result["ok"]:
            errors.append(
                (
                    branch_name,
                    result["status"],
                )
            )
            continue

        for record in result["records"]:

            if record.get("deleted") is True:
                continue

            dt = record_datetime(record)

            if dt:
                try:
                    if dt.date() < date.today():
                        continue
                except Exception:
                    pass

            all_records.append(
                {
                    "branch": branch_name,
                    "record": record,
                    "datetime": dt,
                }
            )

    all_records.sort(
        key=lambda item: (
            item["datetime"] is None,
            item["datetime"]
            or datetime.max,
        )
    )

    return all_records, errors


# =========================================================
# ГЛАВНАЯ СТРАНИЦА
# =========================================================

@app.route(
    "/",
    methods=["GET"],
)
def home():
    return (
        "Kapitan Bulk bot is running",
        200,
    )


# =========================================================
# YCLIENTS — ПОДКЛЮЧЕНИЕ
# =========================================================

@app.route(
    "/yclients/connect",
    methods=["GET"],
)
def yclients_connect():
    salon_ids = []

    salon_id = request.args.get(
        "salon_id"
    )

    if salon_id:
        salon_ids.append(
            salon_id
        )

    salon_ids_array = request.args.getlist(
        "salon_ids[]"
    )

    if salon_ids_array:
        salon_ids.extend(
            salon_ids_array
        )

    if not salon_ids:
        print(
            "YCLIENTS CONNECT PARAMS:",
            dict(request.args),
        )

        return (
            "YCLIENTS не передал salon_id.",
            400,
        )

    activation_results = []

    for current_salon_id in salon_ids:

        try:
            response = (
                activate_yclients_branch(
                    current_salon_id
                )
            )

            activation_results.append(
                {
                    "salon_id":
                        current_salon_id,

                    "status":
                        response.status_code,

                    "body":
                        response.text[:500],
                }
            )

        except Exception as e:
            print(
                "YCLIENTS ACTIVATION ERROR:",
                current_salon_id,
                e,
            )

            activation_results.append(
                {
                    "salon_id":
                        current_salon_id,

                    "status":
                        "error",

                    "body":
                        str(e),
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

                <h2>
                    Готово! 🦭
                </h2>

                <p>
                    Капитан Бульк успешно
                    подключён к YCLIENTS.
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
        "YCLIENTS не удалось "
        "активировать интеграцию. "
        f"Коды: {statuses}",
        500,
    )


# =========================================================
# YCLIENTS — WEBHOOK
# =========================================================

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
            "YCLIENTS WEBHOOK ERROR:",
            e,
        )

        return "ok", 200


# =========================================================
# TELEGRAM WEBHOOK
# =========================================================

@app.route(
    "/telegram",
    methods=["POST"],
)
def telegram_webhook():

    update = (
        request.get_json(
            silent=True
        )
        or {}
    )

    message = update.get(
        "message"
    )

    if not message:
        return "ok", 200

    chat = message.get(
        "chat",
        {}
    )

    chat_id = chat.get(
        "id"
    )

    if not chat_id:
        return "ok", 200

    text = message.get(
        "text",
        ""
    )

    contact = message.get(
        "contact"
    )


    # =====================================================
    # ПОЛУЧИЛИ НОМЕР ТЕЛЕФОНА
    # =====================================================

    if contact:

        phone = normalize_phone(
            contact.get(
                "phone_number",
                ""
            )
        )

        action = PENDING_ACTIONS.get(
            chat_id,
            "records",
        )

        send_message(
            chat_id,
            "Ищу вас в базе "
            "Капитана Булька… 🦭",
        )

        clients, client_errors = (
            find_client_everywhere(
                phone
            )
        )

        if not clients:

            if client_errors:

                error_text = "\n".join(
                    f"{branch}: {status}"
                    for branch, status
                    in client_errors
                )

                send_message(
                    chat_id,
                    "Не удалось получить "
                    "данные из YCLIENTS.\n\n"
                    "Коды ответа:\n"
                    f"{error_text}",
                    main_keyboard(),
                )

            else:

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

            PENDING_ACTIONS.pop(
                chat_id,
                None,
            )

            return "ok", 200


        # =================================================
        # МОИ ЗАПИСИ
        # =================================================

        if action == "records":

            records, record_errors = (
                get_future_records_for_clients(
                    clients
                )
            )

            if records:

                send_message(
                    chat_id,
                    "Нашла ваши "
                    "ближайшие записи 💙",
                )

                for item in records[:10]:

                    send_message(
                        chat_id,
                        format_record(
                            item["record"],
                            item["branch"],
                        ),
                    )

                if len(records) > 10:

                    send_message(
                        chat_id,
                        "Показала первые "
                        "10 записей.",
                    )

                send_message(
                    chat_id,
                    "Что хотите сделать дальше?",
                    main_keyboard(),
                )

            elif record_errors:

                error_text = "\n".join(
                    f"{branch}: {status}"
                    for branch, status
                    in record_errors
                )

                send_message(
                    chat_id,
                    "Я нашла вас в базе 💙\n\n"
                    "Но YCLIENTS пока "
                    "не дал получить "
                    "ваши записи.\n\n"
                    "Коды ответа:\n"
                    f"{error_text}",
                    main_keyboard(),
                )

            else:

                send_message(
                    chat_id,
                    "Нашла вас в базе 💙\n\n"
                    "Будущих записей "
                    "пока нет.",
                    main_keyboard(),
                )

            PENDING_ACTIONS.pop(
                chat_id,
                None,
            )

            return "ok", 200


        # =================================================
        # МОЙ АБОНЕМЕНТ
        # =================================================

        if action == "subscription":

            send_message(
                chat_id,
                "Нашла вас в базе 💙\n\n"
                "Абонементы подключим "
                "следующим этапом.",
                main_keyboard(),
            )

            PENDING_ACTIONS.pop(
                chat_id,
                None,
            )

            return "ok", 200


    # =====================================================
    # START
    # =====================================================

    if text == "/start":

        PENDING_ACTIONS.pop(
            chat_id,
            None,
        )

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


    # =====================================================
    # ЗАПИСАТЬСЯ
    # =====================================================

    if text == "🏊 Записаться":

        PENDING_ACTIONS.pop(
            chat_id,
            None,
        )

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


    # =====================================================
    # МОИ ЗАПИСИ
    # =====================================================

    if text == "📅 Мои записи":

        PENDING_ACTIONS[
            chat_id
        ] = "records"

        send_message(
            chat_id,
            "Чтобы найти ваши записи, "
            "отправьте номер телефона, "
            "который указан в YCLIENTS.",
            phone_keyboard(),
        )

        return "ok", 200


    # =====================================================
    # МОЙ АБОНЕМЕНТ
    # =====================================================

    if text == "🎟️ Мой абонемент":

        PENDING_ACTIONS[
            chat_id
        ] = "subscription"

        send_message(
            chat_id,
            "Чтобы найти ваш абонемент, "
            "отправьте номер телефона, "
            "который указан в YCLIENTS.",
            phone_keyboard(),
        )

        return "ok", 200


    # =====================================================
    # СВЯЗАТЬСЯ
    # =====================================================

    if text == "💬 Связаться с нами":

        send_message(
            chat_id,
            "Напишите нам, "
            "и администратор "
            "поможет вам 💙",
            main_keyboard(),
        )

        return "ok", 200


    # =====================================================
    # НАЗАД
    # =====================================================

    if text == "← Назад":

        PENDING_ACTIONS.pop(
            chat_id,
            None,
        )

        send_message(
            chat_id,
            "Главное меню 🦭",
            main_keyboard(),
        )

        return "ok", 200


    # =====================================================
    # НЕИЗВЕСТНАЯ КОМАНДА
    # =====================================================

    send_message(
        chat_id,
        "Выберите нужный "
        "пункт в меню 👇",
        main_keyboard(),
    )

    return "ok", 200


# =========================================================
# ЗАПУСК
# =========================================================

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
