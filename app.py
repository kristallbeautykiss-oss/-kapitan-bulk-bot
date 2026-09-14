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

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SECRET_KEY = os.environ["SUPABASE_SECRET_KEY"]


TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

YCLIENTS_API = "https://api.yclients.ru/api/v1"
YCLIENTS_MARKETPLACE_API = "https://api.yclients.ru"

APPLICATION_ID = 51162

YCLIENTS_WEBHOOK_URL = (
    "https://kapitan-bulk-bot.onrender.com/yclients/webhook"
)


# =========================================================
# ФИЛИАЛЫ
# =========================================================

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


# =========================================================
# ВРЕМЕННОЕ СОСТОЯНИЕ ДИАЛОГА
# =========================================================

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
        response = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json=payload,
            timeout=20,
        )

        print(
            "TELEGRAM SEND:",
            response.status_code,
            response.text[:500],
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
                {"text": "⚙️ Мои данные"},
            ],
            [
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
                    "text": "📱 Отправить мой номер",
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


def user_data_keyboard():
    return {
        "keyboard": [
            [
                {"text": "📱 Изменить номер"},
            ],
            [
                {"text": "← Назад"},
            ],
        ],
        "resize_keyboard": True,
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
    digits = re.sub(
        r"\D",
        "",
        phone or "",
    )

    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]

    if len(digits) == 10:
        digits = "7" + digits

    return digits


def masked_phone(phone):
    phone = normalize_phone(phone)

    if len(phone) >= 4:
        return f"+7 ••• ••• •• {phone[-2:]}"

    return "номер сохранён"


# =========================================================
# SUPABASE
# =========================================================

def supabase_base_url():
    url = SUPABASE_URL.rstrip("/")

    if url.endswith("/rest/v1"):
        return url

    return f"{url}/rest/v1"


def supabase_headers(prefer=None):
    headers = {
        "apikey": SUPABASE_SECRET_KEY,
        "Content-Type": "application/json",
    }

    if prefer:
        headers["Prefer"] = prefer

    return headers


def get_saved_user(chat_id):
    url = (
        f"{supabase_base_url()}"
        f"/telegram_users"
    )

    params = {
        "chat_id": f"eq.{chat_id}",
        "select": "chat_id,phone,name,created_at",
        "limit": 1,
    }

    try:
        response = requests.get(
            url,
            headers=supabase_headers(),
            params=params,
            timeout=20,
        )

        print(
            "SUPABASE GET USER:",
            response.status_code,
            response.text[:500],
        )

        if response.status_code != 200:
            return None

        data = response.json()

        if not isinstance(data, list):
            return None

        if not data:
            return None

        return data[0]

    except Exception as e:
        print(
            "SUPABASE GET USER ERROR:",
            e,
        )

        return None


def save_user(chat_id, phone, name=None):
    url = (
        f"{supabase_base_url()}"
        f"/telegram_users"
    )

    payload = {
        "chat_id": int(chat_id),
        "phone": normalize_phone(phone),
        "name": name or None,
    }

    try:
        response = requests.post(
            url,
            headers=supabase_headers(
                "resolution=merge-duplicates,return=representation"
            ),
            params={
                "on_conflict": "chat_id",
            },
            json=payload,
            timeout=20,
        )

        print(
            "SUPABASE SAVE USER:",
            response.status_code,
            response.text[:700],
        )

        return response.status_code in (
            200,
            201,
        )

    except Exception as e:
        print(
            "SUPABASE SAVE USER ERROR:",
            e,
        )

        return False


# =========================================================
# YCLIENTS — ЗАГОЛОВКИ
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
        "Authorization": (
            f"Bearer {YCLIENTS_PARTNER_TOKEN}"
        ),
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


# =========================================================
# YCLIENTS — АКТИВАЦИЯ
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

        clients = data.get(
            "data",
            [],
        )

        if isinstance(
            clients,
            dict,
        ):
            clients = (
                clients.get("clients")
                or clients.get("items")
                or []
            )

        if not isinstance(
            clients,
            list,
        ):
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

    normalized_phone = normalize_phone(
        phone
    )

    for (
        branch_name,
        branch_data,
    ) in BRANCHES.items():

        company_id = (
            branch_data[
                "company_id"
            ]
        )

        result = (
            search_client_in_branch(
                company_id,
                normalized_phone,
            )
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

            client_phone = (
                normalize_phone(
                    str(
                        client.get(
                            "phone",
                            "",
                        )
                    )
                )
            )

            if (
                client_phone
                == normalized_phone
            ):
                results.append(
                    {
                        "branch": branch_name,
                        "company_id": company_id,
                        "client": client,
                    }
                )

    return results, errors


def get_client_name(client_results):
    for item in client_results:
        client = item.get(
            "client",
            {},
        )

        name = client.get(
            "name"
        )

        if name:
            return name

    return None


# =========================================================
# YCLIENTS — ЗАПИСИ
# =========================================================

def get_client_records(
    company_id,
    client_id,
):
    url = (
        f"{YCLIENTS_API}"
        f"/records/{company_id}"
    )

    today = date.today()

    end_day = (
        today
        + timedelta(
            days=365
        )
    )

    params = {
        "page": 1,
        "count": 100,
        "client_id": client_id,
        "start_date": (
            today.isoformat()
        ),
        "end_date": (
            end_day.isoformat()
        ),
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

        records = data.get(
            "data",
            [],
        )

        if isinstance(
            records,
            dict,
        ):
            records = (
                records.get("records")
                or records.get("items")
                or []
            )

        if not isinstance(
            records,
            list,
        ):
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
# ДАТА ЗАПИСИ
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
        clean_value = (
            str(value)
            .replace(
                "Z",
                "+00:00",
            )
        )

        return (
            datetime.fromisoformat(
                clean_value
            )
        )

    except Exception:
        return None


def record_sort_value(record):
    dt = record_datetime(
        record
    )

    if not dt:
        return float("inf")

    try:
        return dt.timestamp()

    except Exception:
        return float("inf")


# =========================================================
# ДЛИТЕЛЬНОСТЬ
# =========================================================

def format_duration(record):
    seconds = record.get(
        "length"
    )

    if seconds in (
        None,
        "",
        0,
        "0",
    ):
        seconds = record.get(
            "seance_length"
        )

    try:
        seconds = int(
            seconds
        )

    except (
        TypeError,
        ValueError,
    ):
        return "не указана"

    if seconds <= 0:
        return "не указана"

    minutes = round(
        seconds / 60
    )

    hours, minutes_left = (
        divmod(
            minutes,
            60,
        )
    )

    if (
        hours
        and minutes_left
    ):
        return (
            f"{hours} ч "
            f"{minutes_left} мин"
        )

    if hours:
        return f"{hours} ч"

    return f"{minutes_left} мин"


# =========================================================
# КАРТОЧКА ЗАПИСИ
# =========================================================

def format_record(
    record,
    branch_name,
):
    dt = record_datetime(
        record
    )

    if dt:
        date_text = (
            dt.strftime(
                "%d.%m.%Y"
            )
        )

        time_text = (
            dt.strftime(
                "%H:%M"
            )
        )

    else:
        date_text = (
            str(
                record.get(
                    "date",
                    "",
                )
            )
            or "дата не указана"
        )

        time_text = ""

    staff = (
        record.get("staff")
        or {}
    )

    if isinstance(
        staff,
        dict,
    ):
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

    duration_text = (
        format_duration(
            record
        )
    )

    address = (
        BRANCHES
        .get(
            branch_name,
            {},
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
    client_results,
):
    all_records = []
    errors = []

    for item in client_results:

        branch_name = (
            item["branch"]
        )

        company_id = (
            item["company_id"]
        )

        client = (
            item["client"]
        )

        client_id = (
            client.get("id")
        )

        if not client_id:
            continue

        result = (
            get_client_records(
                company_id,
                client_id,
            )
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

            if record.get(
                "deleted"
            ) is True:
                continue

            dt = record_datetime(
                record
            )

            if dt:
                try:
                    if (
                        dt.date()
                        < date.today()
                    ):
                        continue

                except Exception:
                    pass

            all_records.append(
                {
                    "branch": branch_name,
                    "record": record,
                }
            )

    all_records.sort(
        key=lambda item: (
            record_sort_value(
                item["record"]
            )
        )
    )

    return (
        all_records,
        errors,
    )


# =========================================================
# ПОКАЗАТЬ ЗАПИСИ
# =========================================================

def show_records(
    chat_id,
    phone,
):
    send_message(
        chat_id,
        "Ищу ваши записи "
        "у Капитана Булька… 🦭",
    )

    clients, client_errors = (
        find_client_everywhere(
            phone
        )
    )

    if not clients:

        if client_errors:

            error_text = "\n".join(
                (
                    f"{branch}: "
                    f"{status}"
                )
                for (
                    branch,
                    status,
                )
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
                "Если номер изменился, "
                "откройте «⚙️ Мои данные» "
                "и привяжите новый.",
                main_keyboard(),
            )

        return

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
            "Что хотите "
            "сделать дальше?",
            main_keyboard(),
        )

        return

    if record_errors:

        error_text = "\n".join(
            (
                f"{branch}: "
                f"{status}"
            )
            for (
                branch,
                status,
            )
            in record_errors
        )

        send_message(
            chat_id,
            "Я нашла вас "
            "в базе 💙\n\n"
            "Но YCLIENTS пока "
            "не дал получить "
            "ваши записи.\n\n"
            "Коды ответа:\n"
            f"{error_text}",
            main_keyboard(),
        )

        return

    send_message(
        chat_id,
        "Нашла вас в базе 💙\n\n"
        "Будущих записей "
        "пока нет.",
        main_keyboard(),
    )


# =========================================================
# СТАРТОВАЯ СТРАНИЦА
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
# YCLIENTS CONNECT
# =========================================================

@app.route(
    "/yclients/connect",
    methods=["GET"],
)
def yclients_connect():

    salon_ids = []

    salon_id = (
        request.args.get(
            "salon_id"
        )
    )

    if salon_id:
        salon_ids.append(
            salon_id
        )

    salon_ids_array = (
        request.args.getlist(
            "salon_ids[]"
        )
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
        for item
        in activation_results
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
        (
            f'{item["salon_id"]}: '
            f'{item["status"]}'
        )
        for item
        in activation_results
    )

    return (
        "YCLIENTS не удалось "
        "активировать интеграцию. "
        f"Коды: {statuses}",
        500,
    )


# =========================================================
# YCLIENTS WEBHOOK
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
        "",
    )

    contact = message.get(
        "contact"
    )


    # =====================================================
    # ПОЛУЧИЛИ НОМЕР
    # =====================================================

    if contact:

        phone = normalize_phone(
            contact.get(
                "phone_number",
                "",
            )
        )

        action = (
            PENDING_ACTIONS.get(
                chat_id,
                "records",
            )
        )

        send_message(
            chat_id,
            "Проверяю номер "
            "в базе Капитана Булька… 🦭",
        )

        clients, client_errors = (
            find_client_everywhere(
                phone
            )
        )

        if not clients:

            if client_errors:

                error_text = "\n".join(
                    (
                        f"{branch}: "
                        f"{status}"
                    )
                    for (
                        branch,
                        status,
                    )
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
                    "в нашей клиентской базе.\n\n"
                    "Проверьте, что отправлен "
                    "тот же номер, который "
                    "указывали при записи.",
                    main_keyboard(),
                )

            PENDING_ACTIONS.pop(
                chat_id,
                None,
            )

            return "ok", 200


        client_name = (
            get_client_name(
                clients
            )
        )

        saved = save_user(
            chat_id,
            phone,
            client_name,
        )

        if not saved:

            send_message(
                chat_id,
                "Я нашла вас в базе, "
                "но пока не смогла "
                "сохранить номер.\n\n"
                "Попробуйте ещё раз "
                "чуть позже.",
                main_keyboard(),
            )

            PENDING_ACTIONS.pop(
                chat_id,
                None,
            )

            return "ok", 200


        # =================================================
        # СМЕНА НОМЕРА
        # =================================================

        if action == "change_phone":

            if client_name:
                greeting = (
                    f"{client_name}, "
                    "новый номер сохранён 💙"
                )

            else:
                greeting = (
                    "Новый номер "
                    "сохранён 💙"
                )

            send_message(
                chat_id,
                greeting,
                main_keyboard(),
            )

            PENDING_ACTIONS.pop(
                chat_id,
                None,
            )

            return "ok", 200


        # =================================================
        # ЗАПИСИ
        # =================================================

        if action == "records":

            PENDING_ACTIONS.pop(
                chat_id,
                None,
            )

            show_records(
                chat_id,
                phone,
            )

            return "ok", 200


        # =================================================
        # АБОНЕМЕНТ
        # =================================================

        if action == "subscription":

            PENDING_ACTIONS.pop(
                chat_id,
                None,
            )

            send_message(
                chat_id,
                "Нашла вас в базе 💙\n\n"
                "Номер сохранён — "
                "больше отправлять "
                "его каждый раз "
                "не понадобится.\n\n"
                "Информацию по абонементу "
                "подключим следующим этапом.",
                main_keyboard(),
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

        saved_user = (
            get_saved_user(
                chat_id
            )
        )

        if saved_user:

            name = (
                saved_user.get(
                    "name"
                )
            )

            if name:
                hello = (
                    f"С возвращением, "
                    f"{name}! 🦭💙"
                )

            else:
                hello = (
                    "С возвращением! 🦭💙"
                )

            send_message(
                chat_id,
                hello
                + "\n\n"
                + "Я уже помню ваш номер, "
                + "поэтому повторно "
                + "отправлять его не нужно.",
                main_keyboard(),
            )

        else:

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

        branch = BRANCHES[
            text
        ]

        send_message(
            chat_id,
            f"Вы выбрали филиал "
            f"«{text}» 💙",
            booking_button(
                branch[
                    "booking_url"
                ]
            ),
        )

        return "ok", 200


    # =====================================================
    # МОИ ЗАПИСИ
    # =====================================================

    if text == "📅 Мои записи":

        saved_user = (
            get_saved_user(
                chat_id
            )
        )

        if saved_user:

            phone = saved_user.get(
                "phone"
            )

            if phone:
                show_records(
                    chat_id,
                    phone,
                )

                return "ok", 200


        PENDING_ACTIONS[
            chat_id
        ] = "records"

        send_message(
            chat_id,
            "Чтобы найти ваши записи, "
            "один раз отправьте номер "
            "телефона, который указан "
            "в YCLIENTS.\n\n"
            "Я запомню его, и дальше "
            "повторно отправлять "
            "номер не понадобится 💙",
            phone_keyboard(),
        )

        return "ok", 200


    # =====================================================
    # МОЙ АБОНЕМЕНТ
    # =====================================================

    if text == "🎟️ Мой абонемент":

        saved_user = (
            get_saved_user(
                chat_id
            )
        )

        if saved_user:

            send_message(
                chat_id,
                "Я уже помню ваш номер 💙\n\n"
                "Информацию по абонементу "
                "подключим следующим этапом.",
                main_keyboard(),
            )

            return "ok", 200


        PENDING_ACTIONS[
            chat_id
        ] = "subscription"

        send_message(
            chat_id,
            "Чтобы найти ваш абонемент, "
            "один раз отправьте номер "
            "телефона, который указан "
            "в YCLIENTS.",
            phone_keyboard(),
        )

        return "ok", 200


    # =====================================================
    # МОИ ДАННЫЕ
    # =====================================================

    if text == "⚙️ Мои данные":

        saved_user = (
            get_saved_user(
                chat_id
            )
        )

        if not saved_user:

            PENDING_ACTIONS[
                chat_id
            ] = "change_phone"

            send_message(
                chat_id,
                "У вас пока нет "
                "сохранённого номера.\n\n"
                "Отправьте номер телефона, "
                "который указан в YCLIENTS.",
                phone_keyboard(),
            )

            return "ok", 200


        name = (
            saved_user.get(
                "name"
            )
            or "не указано"
        )

        phone = (
            saved_user.get(
                "phone"
            )
        )

        send_message(
            chat_id,
            "⚙️ Мои данные\n\n"
            f"👤 Имя: {name}\n"
            f"📱 Телефон: "
            f"{masked_phone(phone)}\n\n"
            "Если номер изменился, "
            "его можно перепривязать.",
            user_data_keyboard(),
        )

        return "ok", 200


    # =====================================================
    # ИЗМЕНИТЬ НОМЕР
    # =====================================================

    if text == "📱 Изменить номер":

        PENDING_ACTIONS[
            chat_id
        ] = "change_phone"

        send_message(
            chat_id,
            "Отправьте новый номер "
            "телефона кнопкой ниже.\n\n"
            "Он должен совпадать с номером "
            "в вашей карточке YCLIENTS.",
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
