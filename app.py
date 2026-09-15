import os
import re
import requests

from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
from flask import Flask, request


app = Flask(__name__)


# =========================================================
# НАСТРОЙКИ
# =========================================================

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"].strip()

YCLIENTS_USER_TOKEN = os.environ["YCLIENTS_USER_TOKEN"].strip()
YCLIENTS_PARTNER_TOKEN = os.environ["YCLIENTS_PARTNER_TOKEN"].strip()

SUPABASE_URL = os.environ["SUPABASE_URL"].strip()
SUPABASE_SECRET_KEY = os.environ["SUPABASE_SECRET_KEY"].strip()

# Добавим в Render следующим шагом.
# Пока код запустится и без него,
# но автоматическая проверка напоминаний будет выключена.
REMINDER_SECRET = os.environ.get(
    "REMINDER_SECRET",
    "",
).strip()


TELEGRAM_API = (
    f"https://api.telegram.org/bot{BOT_TOKEN}"
)

YCLIENTS_API = (
    "https://api.yclients.ru/api/v1"
)

YCLIENTS_MARKETPLACE_API = (
    "https://api.yclients.ru"
)

APPLICATION_ID = 51162

YCLIENTS_WEBHOOK_URL = (
    "https://kapitan-bulk-bot.onrender.com/"
    "yclients/webhook"
)

MOSCOW_TZ = ZoneInfo(
    "Europe/Moscow"
)


# =========================================================
# ФИЛИАЛЫ
# =========================================================

BRANCHES = {
    "Нагатинская": {
        "company_id": 558795,
        "booking_url":
            "https://n591306.yclients.ru",
        "address":
            "Нагатинская, 16",
        "admin":
            "@Bulk_nagatinskaya",
    },

    "Беломорская": {
        "company_id": 647846,
        "booking_url":
            "https://n685581.yclients.ru",
        "address":
            "Беломорская, 9",
        "admin":
            "@Bulk_levoberezhny",
    },

    "Базовская": {
        "company_id": 594760,
        "booking_url":
            "https://n629339.yclients.ru",
        "address":
            "Базовская, 15А",
        "admin":
            "@Bulk_hovrino",
    },

    "Истринская": {
        "company_id": 689709,
        "booking_url":
            "https://n731690.yclients.ru",
        "address":
            "Истринская, 5",
        "admin":
            "@Bulk_molodezhnaia",
    },
}


# =========================================================
# ВРЕМЕННОЕ СОСТОЯНИЕ
# =========================================================

PENDING_ACTIONS = {}


# =========================================================
# TELEGRAM
# =========================================================

def send_message(
    chat_id,
    text,
    reply_markup=None,
):
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
            timeout=30,
        )

        print(
            "TELEGRAM SEND:",
            response.status_code,
            response.text[:500],
        )

        return response

    except Exception as e:
        print(
            "TELEGRAM SEND ERROR:",
            e,
        )

        return None


def answer_callback(
    callback_query_id,
    text=None,
    show_alert=False,
):
    payload = {
        "callback_query_id":
            callback_query_id,
        "show_alert":
            show_alert,
    }

    if text:
        payload["text"] = text

    try:
        requests.post(
            f"{TELEGRAM_API}/answerCallbackQuery",
            json=payload,
            timeout=20,
        )

    except Exception as e:
        print(
            "ANSWER CALLBACK ERROR:",
            e,
        )


def edit_message_buttons(
    chat_id,
    message_id,
    reply_markup=None,
):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "reply_markup":
            reply_markup
            or {"inline_keyboard": []},
    }

    try:
        requests.post(
            f"{TELEGRAM_API}/editMessageReplyMarkup",
            json=payload,
            timeout=20,
        )

    except Exception as e:
        print(
            "EDIT BUTTONS ERROR:",
            e,
        )


# =========================================================
# КЛАВИАТУРЫ
# =========================================================

def main_keyboard():
    return {
        "keyboard": [
            [
                {
                    "text":
                        "🏊 Записаться"
                },
                {
                    "text":
                        "🎟️ Мой абонемент"
                },
            ],
            [
                {
                    "text":
                        "📅 Мои записи"
                },
                {
                    "text":
                        "⚙️ Мои данные"
                },
            ],
            [
                {
                    "text":
                        "💬 Связаться с нами"
                },
            ],
        ],
        "resize_keyboard": True,
    }


def branch_keyboard():
    return {
        "keyboard": [
            [
                {
                    "text":
                        "Нагатинская"
                },
                {
                    "text":
                        "Беломорская"
                },
            ],
            [
                {
                    "text":
                        "Базовская"
                },
                {
                    "text":
                        "Истринская"
                },
            ],
            [
                {
                    "text":
                        "← Назад"
                },
            ],
        ],
        "resize_keyboard": True,
    }


def phone_keyboard():
    return {
        "keyboard": [
            [
                {
                    "text":
                        "📱 Отправить мой номер",
                    "request_contact":
                        True,
                }
            ],
            [
                {
                    "text":
                        "← Назад"
                }
            ],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }


def user_data_keyboard():
    return {
        "keyboard": [
            [
                {
                    "text":
                        "📱 Изменить номер"
                },
            ],
            [
                {
                    "text":
                        "← Назад"
                },
            ],
        ],
        "resize_keyboard": True,
    }


def booking_button(url):
    return {
        "inline_keyboard": [
            [
                {
                    "text":
                        "Записаться онлайн",
                    "url":
                        url,
                }
            ]
        ]
    }


def reminder_buttons(
    company_id,
    record_id,
    already_confirmed=False,
):
    buttons = []

    if not already_confirmed:
        buttons.append(
            [
                {
                    "text":
                        "✅ Подтвердить запись",
                    "callback_data":
                        f"confirm:{company_id}:{record_id}",
                }
            ]
        )

    buttons.append(
        [
            {
                "text":
                    "❌ Отменить занятие",
                "callback_data":
                    f"cancel:{company_id}:{record_id}",
            }
        ]
    )

    return {
        "inline_keyboard":
            buttons
    }


def confirm_cancel_buttons(
    company_id,
    record_id,
):
    return {
        "inline_keyboard": [
            [
                {
                    "text":
                        "Да, отменить",
                    "callback_data":
                        f"cancel_yes:{company_id}:{record_id}",
                }
            ],
            [
                {
                    "text":
                        "Нет, оставить запись",
                    "callback_data":
                        f"cancel_no:{company_id}:{record_id}",
                }
            ],
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

    if (
        len(digits) == 11
        and digits.startswith("8")
    ):
        digits = (
            "7"
            + digits[1:]
        )

    if len(digits) == 10:
        digits = (
            "7"
            + digits
        )

    return digits


def masked_phone(phone):
    phone = normalize_phone(
        phone
    )

    if len(phone) >= 2:
        return (
            "+7 ••• ••• •• "
            f"{phone[-2:]}"
        )

    return "номер сохранён"


# =========================================================
# SUPABASE
# =========================================================

def supabase_base_url():
    url = (
        SUPABASE_URL
        .strip()
        .rstrip("/")
    )

    if url.endswith(
        "/rest/v1"
    ):
        return url

    return (
        f"{url}/rest/v1"
    )


def supabase_headers(
    prefer=None,
):
    headers = {
        "apikey":
            SUPABASE_SECRET_KEY.strip(),

        "Content-Type":
            "application/json",
    }

    if prefer:
        headers[
            "Prefer"
        ] = prefer

    return headers


# =========================================================
# SUPABASE — TELEGRAM USERS
# =========================================================

def get_saved_user(chat_id):
    url = (
        f"{supabase_base_url()}"
        "/telegram_users"
    )

    params = {
        "chat_id":
            f"eq.{chat_id}",

        "select":
            "chat_id,phone,name,created_at",

        "limit":
            1,
    }

    try:
        response = requests.get(
            url,
            headers=
                supabase_headers(),
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

        if (
            isinstance(data, list)
            and data
        ):
            return data[0]

        return None

    except Exception as e:
        print(
            "SUPABASE GET USER ERROR:",
            e,
        )

        return None


def get_all_saved_users():
    url = (
        f"{supabase_base_url()}"
        "/telegram_users"
    )

    params = {
        "select":
            "chat_id,phone,name",
    }

    try:
        response = requests.get(
            url,
            headers=
                supabase_headers(),
            params=params,
            timeout=30,
        )

        print(
            "SUPABASE ALL USERS:",
            response.status_code,
        )

        if response.status_code != 200:
            return []

        data = response.json()

        if isinstance(
            data,
            list,
        ):
            return data

        return []

    except Exception as e:
        print(
            "SUPABASE ALL USERS ERROR:",
            e,
        )

        return []


def save_user(
    chat_id,
    phone,
    name=None,
):
    url = (
        f"{supabase_base_url()}"
        "/telegram_users"
    )

    payload = {
        "chat_id":
            int(chat_id),

        "phone":
            normalize_phone(
                phone
            ),

        "name":
            name or None,
    }

    try:
        response = requests.post(
            url,

            headers=
                supabase_headers(
                    "resolution=merge-duplicates,"
                    "return=representation"
                ),

            params={
                "on_conflict":
                    "chat_id"
            },

            json=payload,
            timeout=20,
        )

        print(
            "SUPABASE SAVE USER:",
            response.status_code,
            response.text[:700],
        )

        return (
            response.status_code
            in (
                200,
                201,
            )
        )

    except Exception as e:
        print(
            "SUPABASE SAVE USER ERROR:",
            e,
        )

        return False


# =========================================================
# SUPABASE — REMINDERS
# =========================================================

def get_reminder_row(
    company_id,
    record_id,
):
    url = (
        f"{supabase_base_url()}"
        "/appointment_reminders"
    )

    params = {
        "company_id":
            f"eq.{company_id}",

        "record_id":
            f"eq.{record_id}",

        "select":
            "*",

        "limit":
            1,
    }

    try:
        response = requests.get(
            url,
            headers=
                supabase_headers(),
            params=params,
            timeout=20,
        )

        if response.status_code != 200:
            print(
                "GET REMINDER ERROR:",
                response.status_code,
                response.text[:500],
            )
            return None

        data = response.json()

        if (
            isinstance(data, list)
            and data
        ):
            return data[0]

        return None

    except Exception as e:
        print(
            "GET REMINDER EXCEPTION:",
            e,
        )

        return None


def create_reminder_row(
    company_id,
    record_id,
    chat_id,
    record_datetime_value,
    reminder_sent=True,
    confirmed=False,
):
    url = (
        f"{supabase_base_url()}"
        "/appointment_reminders"
    )

    # В созданной нами таблице id не автоинкрементный.
    # Поэтому используем ID самой записи YCLIENTS.
    payload = {
        "id":
            int(record_id),

        "record_id":
            int(record_id),

        "company_id":
            int(company_id),

        "chat_id":
            int(chat_id),

        "record_datetime":
            record_datetime_value,

        "reminder_sent":
            bool(reminder_sent),

        "confirmed":
            bool(confirmed),

        "cancelled":
            False,
    }

    try:
        response = requests.post(
            url,
            headers=
                supabase_headers(
                    "return=representation"
                ),
            json=payload,
            timeout=20,
        )

        print(
            "CREATE REMINDER:",
            response.status_code,
            response.text[:700],
        )

        return (
            response.status_code
            in (
                200,
                201,
            )
        )

    except Exception as e:
        print(
            "CREATE REMINDER ERROR:",
            e,
        )

        return False


def update_reminder_row(
    company_id,
    record_id,
    fields,
):
    url = (
        f"{supabase_base_url()}"
        "/appointment_reminders"
    )

    params = {
        "company_id":
            f"eq.{company_id}",

        "record_id":
            f"eq.{record_id}",
    }

    try:
        response = requests.patch(
            url,
            headers=
                supabase_headers(
                    "return=representation"
                ),
            params=params,
            json=fields,
            timeout=20,
        )

        print(
            "UPDATE REMINDER:",
            response.status_code,
            response.text[:500],
        )

        return (
            response.status_code
            in (
                200,
                204,
            )
        )

    except Exception as e:
        print(
            "UPDATE REMINDER ERROR:",
            e,
        )

        return False


# =========================================================
# YCLIENTS HEADERS
# =========================================================

def yclients_user_headers():
    return {
        "Authorization": (
            f"Bearer "
            f"{YCLIENTS_PARTNER_TOKEN}, "
            f"User "
            f"{YCLIENTS_USER_TOKEN}"
        ),

        "Accept":
            "application/vnd.yclients.v2+json",

        "Content-Type":
            "application/json",
    }


def yclients_partner_headers():
    return {
        "Authorization":
            f"Bearer "
            f"{YCLIENTS_PARTNER_TOKEN}",

        "Accept":
            "application/json",

        "Content-Type":
            "application/json",
    }


# =========================================================
# YCLIENTS — ПОИСК КЛИЕНТА
# =========================================================

def search_client_in_branch(
    company_id,
    phone,
):
    url = (
        f"{YCLIENTS_API}"
        f"/company/"
        f"{company_id}"
        f"/clients/search"
    )

    payload = {
        "page":
            1,

        "page_size":
            10,

        "fields": [
            "id",
            "name",
            "phone",
        ],

        "operation":
            "AND",

        "filters": [
            {
                "type":
                    "quick_search",

                "state": {
                    "value":
                        phone
                },
            }
        ],
    }

    try:
        response = requests.post(
            url,
            headers=
                yclients_user_headers(),
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
                "ok":
                    False,

                "status":
                    response.status_code,

                "clients":
                    [],
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
                clients.get(
                    "clients"
                )
                or clients.get(
                    "items"
                )
                or []
            )

        if not isinstance(
            clients,
            list,
        ):
            clients = []

        return {
            "ok":
                True,

            "status":
                200,

            "clients":
                clients,
        }

    except Exception as e:
        print(
            "CLIENT SEARCH ERROR:",
            company_id,
            e,
        )

        return {
            "ok":
                False,

            "status":
                "error",

            "clients":
                [],
        }


def find_client_everywhere(
    phone,
):
    results = []
    errors = []

    phone = normalize_phone(
        phone
    )

    for (
        branch_name,
        branch,
    ) in BRANCHES.items():

        company_id = (
            branch[
                "company_id"
            ]
        )

        result = (
            search_client_in_branch(
                company_id,
                phone,
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

        for client in result[
            "clients"
        ]:
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

            if client_phone == phone:
                results.append(
                    {
                        "branch":
                            branch_name,

                        "company_id":
                            company_id,

                        "client":
                            client,
                    }
                )

    return (
        results,
        errors,
    )


def get_client_name(
    clients,
):
    for item in clients:
        name = (
            item.get(
                "client",
                {},
            )
            .get(
                "name"
            )
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
        f"/records/"
        f"{company_id}"
    )

    today = (
        datetime
        .now(
            MOSCOW_TZ
        )
        .date()
    )

    end_day = (
        today
        + timedelta(
            days=365
        )
    )

    params = {
        "page":
            1,

        "count":
            100,

        "client_id":
            client_id,

        "start_date":
            today.isoformat(),

        "end_date":
            end_day.isoformat(),
    }

    try:
        response = requests.get(
            url,
            headers=
                yclients_user_headers(),
            params=params,
            timeout=30,
        )

        print(
            "RECORD SEARCH:",
            company_id,
            client_id,
            response.status_code,
            response.text[:1000],
        )

        if response.status_code != 200:
            return {
                "ok":
                    False,

                "status":
                    response.status_code,

                "records":
                    [],
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
                records.get(
                    "records"
                )
                or records.get(
                    "items"
                )
                or []
            )

        if not isinstance(
            records,
            list,
        ):
            records = []

        return {
            "ok":
                True,

            "status":
                200,

            "records":
                records,
        }

    except Exception as e:
        print(
            "RECORD SEARCH ERROR:",
            e,
        )

        return {
            "ok":
                False,

            "status":
                "error",

            "records":
                [],
        }


def get_record(
    company_id,
    record_id,
):
    url = (
        f"{YCLIENTS_API}"
        f"/record/"
        f"{company_id}/"
        f"{record_id}"
    )

    try:
        response = requests.get(
            url,
            headers=
                yclients_user_headers(),
            timeout=30,
        )

        print(
            "GET RECORD:",
            response.status_code,
            response.text[:800],
        )

        if response.status_code != 200:
            return None

        data = response.json()

        record = data.get(
            "data"
        )

        if isinstance(
            record,
            dict,
        ):
            return record

        return None

    except Exception as e:
        print(
            "GET RECORD ERROR:",
            e,
        )

        return None


def confirm_yclients_record(
    company_id,
    record_id,
):
    url = (
        f"{YCLIENTS_API}"
        f"/record/"
        f"{company_id}/"
        f"{record_id}"
    )

    try:
        response = requests.put(
            url,
            headers=
                yclients_user_headers(),

            json={
                "confirmed":
                    1
            },

            timeout=30,
        )

        print(
            "CONFIRM RECORD:",
            company_id,
            record_id,
            response.status_code,
            response.text[:800],
        )

        return (
            response.status_code
            in (
                200,
                201,
            )
        )

    except Exception as e:
        print(
            "CONFIRM RECORD ERROR:",
            e,
        )

        return False


def delete_yclients_record(
    company_id,
    record_id,
):
    url = (
        f"{YCLIENTS_API}"
        f"/record/"
        f"{company_id}/"
        f"{record_id}"
    )

    try:
        response = requests.delete(
            url,
            headers=
                yclients_user_headers(),
            timeout=30,
        )

        print(
            "DELETE RECORD:",
            company_id,
            record_id,
            response.status_code,
            response.text[:800],
        )

        return (
            response.status_code
            in (
                200,
                204,
            )
        )

    except Exception as e:
        print(
            "DELETE RECORD ERROR:",
            e,
        )

        return False


# =========================================================
# ДАТА И ВРЕМЯ
# =========================================================

def record_datetime(
    record,
):
    value = (
        record.get(
            "datetime"
        )
        or record.get(
            "date"
        )
        or ""
    )

    if not value:
        return None

    try:
        value = (
            str(value)
            .replace(
                "Z",
                "+00:00",
            )
        )

        dt = (
            datetime
            .fromisoformat(
                value
            )
        )

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=
                    MOSCOW_TZ
            )

        return dt.astimezone(
            MOSCOW_TZ
        )

    except Exception as e:
        print(
            "DATETIME PARSE ERROR:",
            value,
            e,
        )

        return None


def hours_until_record(
    record,
):
    dt = record_datetime(
        record
    )

    if not dt:
        return None

    now = datetime.now(
        MOSCOW_TZ
    )

    seconds = (
        dt - now
    ).total_seconds()

    return (
        seconds / 3600
    )


def format_duration(
    record,
):
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

    hours, mins = divmod(
        minutes,
        60,
    )

    if hours and mins:
        return (
            f"{hours} ч "
            f"{mins} мин"
        )

    if hours:
        return (
            f"{hours} ч"
        )

    return (
        f"{mins} мин"
    )


# =========================================================
# ФИЛИАЛ ПО COMPANY ID
# =========================================================

def branch_name_by_company_id(
    company_id,
):
    company_id = int(
        company_id
    )

    for (
        name,
        branch,
    ) in BRANCHES.items():

        if (
            int(
                branch[
                    "company_id"
                ]
            )
            == company_id
        ):
            return name

    return None


# =========================================================
# КАРТОЧКА ЗАПИСИ
# =========================================================

def get_staff_name(
    record,
):
    staff = (
        record.get(
            "staff"
        )
        or {}
    )

    if isinstance(
        staff,
        dict,
    ):
        return (
            staff.get(
                "name"
            )
            or staff.get(
                "title"
            )
            or "не указан"
        )

    if staff:
        return str(
            staff
        )

    return "не указан"


def format_record(
    record,
    branch_name,
):
    dt = record_datetime(
        record
    )

    if dt:
        when = (
            dt.strftime(
                "%d.%m.%Y в %H:%M"
            )
        )

    else:
        when = (
            "дата не указана"
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

    return (
        "📅 Ваша запись\n\n"
        f"🗓 {when}\n"
        "🏊 Индивидуальная тренировка\n"
        f"👤 Тренер: "
        f"{get_staff_name(record)}\n"
        f"⏱ Длительность: "
        f"{format_duration(record)}\n"
        f"📍 {address}"
    )


def format_reminder(
    record,
    branch_name,
):
    dt = record_datetime(
        record
    )

    if dt:
        when = (
            dt.strftime(
                "%d.%m.%Y в %H:%M"
            )
        )

    else:
        when = (
            "время не указано"
        )

    branch = BRANCHES.get(
        branch_name,
        {},
    )

    address = branch.get(
        "address",
        branch_name,
    )

    return (
        "🦭 Напоминание от "
        "Капитана Булька!\n\n"
        "Ждём вас на занятии 💙\n\n"
        f"🗓 {when}\n"
        "🏊 Индивидуальная тренировка\n"
        f"👤 Тренер: "
        f"{get_staff_name(record)}\n"
        f"⏱ Длительность: "
        f"{format_duration(record)}\n"
        f"📍 {address}\n\n"
        "Пожалуйста, подтвердите запись."
    )


# =========================================================
# БУДУЩИЕ ЗАПИСИ
# =========================================================

def get_future_records_for_clients(
    clients,
):
    all_records = []
    errors = []

    now = datetime.now(
        MOSCOW_TZ
    )

    for item in clients:
        branch_name = item[
            "branch"
        ]

        company_id = item[
            "company_id"
        ]

        client_id = (
            item[
                "client"
            ]
            .get(
                "id"
            )
        )

        if not client_id:
            continue

        result = get_client_records(
            company_id,
            client_id,
        )

        if not result[
            "ok"
        ]:
            errors.append(
                (
                    branch_name,
                    result[
                        "status"
                    ],
                )
            )
            continue

        for record in result[
            "records"
        ]:

            if record.get(
                "deleted"
            ):
                continue

            dt = record_datetime(
                record
            )

            if (
                dt
                and dt < now
            ):
                continue

            all_records.append(
                {
                    "branch":
                        branch_name,

                    "company_id":
                        company_id,

                    "record":
                        record,
                }
            )

    all_records.sort(
        key=lambda item:
            (
                record_datetime(
                    item[
                        "record"
                    ]
                )
                or datetime.max.replace(
                    tzinfo=
                        MOSCOW_TZ
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
        send_message(
            chat_id,
            "Не нашла ваши записи "
            "в клиентской базе.\n\n"
            "Если вы меняли номер, "
            "откройте «⚙️ Мои данные».",
            main_keyboard(),
        )

        return

    records, errors = (
        get_future_records_for_clients(
            clients
        )
    )

    if not records:
        send_message(
            chat_id,
            "Будущих записей "
            "пока нет 💙",
            main_keyboard(),
        )

        return

    send_message(
        chat_id,
        "Нашла ваши "
        "ближайшие записи 💙",
    )

    for item in records[:10]:
        send_message(
            chat_id,
            format_record(
                item[
                    "record"
                ],
                item[
                    "branch"
                ],
            ),
        )

    send_message(
        chat_id,
        "Что хотите сделать дальше?",
        main_keyboard(),
    )


# =========================================================
# НАПОМИНАНИЯ
# =========================================================

def scan_and_send_reminders():
    users = get_all_saved_users()

    sent = 0
    checked = 0

    for user in users:
        chat_id = user.get(
            "chat_id"
        )

        phone = user.get(
            "phone"
        )

        if (
            not chat_id
            or not phone
        ):
            continue

        clients, errors = (
            find_client_everywhere(
                phone
            )
        )

        if not clients:
            continue

        records, errors = (
            get_future_records_for_clients(
                clients
            )
        )

        for item in records:
            checked += 1

            record = item[
                "record"
            ]

            company_id = item[
                "company_id"
            ]

            branch_name = item[
                "branch"
            ]

            record_id = record.get(
                "id"
            )

            if not record_id:
                continue

            hours_left = (
                hours_until_record(
                    record
                )
            )

            if hours_left is None:
                continue

            # Напоминание отправляется
            # в последние 24 часа до занятия.
            # Если сервис временно "спал",
            # напоминание не потеряется.
            if not (
                0
                < hours_left
                <= 24
            ):
                continue

            existing = (
                get_reminder_row(
                    company_id,
                    record_id,
                )
            )

            if (
                existing
                and existing.get(
                    "reminder_sent"
                )
            ):
                continue

            # Кнопку подтверждения показываем, пока клиент
            # не подтвердил запись именно через нашего бота.
            # Поле confirmed в YCLIENTS не используем для скрытия
            # кнопки: запись там может быть подтверждена заранее.
            already_confirmed = (
                bool(
                    existing.get(
                        "confirmed"
                    )
                )
                if existing
                else False
            )

            response = send_message(
                chat_id,
                format_reminder(
                    record,
                    branch_name,
                ),
                reminder_buttons(
                    company_id,
                    record_id,
                    already_confirmed=
                        already_confirmed,
                ),
            )

            if (
                response
                and response.status_code
                == 200
            ):
                dt = record_datetime(
                    record
                )

                dt_value = (
                    dt.isoformat()
                    if dt
                    else None
                )

                if existing:
                    update_reminder_row(
                        company_id,
                        record_id,
                        {
                            "chat_id":
                                int(chat_id),

                            "record_datetime":
                                dt_value,

                            "reminder_sent":
                                True,

                            "confirmed":
                                already_confirmed,
                        },
                    )

                else:
                    create_reminder_row(
                        company_id,
                        record_id,
                        chat_id,
                        dt_value,
                        reminder_sent=True,
                        confirmed=
                            already_confirmed,
                    )

                sent += 1

    return {
        "users":
            len(users),

        "records_checked":
            checked,

        "sent":
            sent,
    }


# =========================================================
# ПРАВИЛО 23 ЧАСА
# =========================================================

def can_cancel_record(
    record,
):
    hours_left = (
        hours_until_record(
            record
        )
    )

    if hours_left is None:
        return False

    return (
        hours_left >= 23
    )


def admin_for_company(
    company_id,
):
    branch_name = (
        branch_name_by_company_id(
            company_id
        )
    )

    if not branch_name:
        return (
            "администратору филиала"
        )

    return (
        BRANCHES[
            branch_name
        ][
            "admin"
        ]
    )


# =========================================================
# HOME
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
# ENDPOINT ДЛЯ ЗАПУСКА НАПОМИНАНИЙ
# =========================================================

@app.route(
    "/tasks/send-reminders",
    methods=[
        "GET",
        "POST",
    ],
)
def send_reminders_task():
    if not REMINDER_SECRET:
        return (
            "REMINDER_SECRET is not configured",
            503,
        )

    supplied_key = (
        request.headers.get(
            "X-Reminder-Secret"
        )
        or request.args.get(
            "key"
        )
        or ""
    )

    if supplied_key != REMINDER_SECRET:
        return (
            "Unauthorized",
            401,
        )

    result = (
        scan_and_send_reminders()
    )

    return (
        result,
        200,
    )


# =========================================================
# YCLIENTS WEBHOOK
# =========================================================

@app.route(
    "/yclients/webhook",
    methods=["POST"],
)
def yclients_webhook():
    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    print(
        "YCLIENTS WEBHOOK:",
        data,
    )

    return (
        "ok",
        200,
    )


# =========================================================
# YCLIENTS CONNECT
# =========================================================

def activate_yclients_branch(
    salon_id,
):
    url = (
        f"{YCLIENTS_MARKETPLACE_API}"
        "/marketplace/partner/callback"
    )

    payload = {
        "salon_id":
            int(salon_id),

        "application_id":
            APPLICATION_ID,

        "webhook_urls": [
            YCLIENTS_WEBHOOK_URL
        ],
    }

    return requests.post(
        url,
        headers=
            yclients_partner_headers(),
        json=payload,
        timeout=30,
    )


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

    salon_ids.extend(
        request.args.getlist(
            "salon_ids[]"
        )
    )

    if not salon_ids:
        return (
            "YCLIENTS не передал salon_id",
            400,
        )

    results = []

    for salon_id in salon_ids:
        try:
            response = (
                activate_yclients_branch(
                    salon_id
                )
            )

            results.append(
                (
                    salon_id,
                    response.status_code,
                )
            )

        except Exception as e:
            results.append(
                (
                    salon_id,
                    str(e),
                )
            )

    success = all(
        status in (
            200,
            201,
        )
        for (
            salon,
            status,
        )
        in results
    )

    if success:
        return (
            "Капитан Бульк успешно подключён",
            200,
        )

    return (
        str(results),
        500,
    )


# =========================================================
# CALLBACK-КНОПКИ TELEGRAM
# =========================================================

def handle_callback_query(
    callback,
):
    callback_id = callback.get(
        "id"
    )

    data = callback.get(
        "data",
        "",
    )

    message = callback.get(
        "message",
        {},
    )

    chat_id = (
        message
        .get(
            "chat",
            {},
        )
        .get(
            "id"
        )
    )

    message_id = message.get(
        "message_id"
    )

    if not (
        callback_id
        and chat_id
    ):
        return

    parts = data.split(
        ":"
    )

    if len(parts) != 3:
        answer_callback(
            callback_id
        )
        return

    action = parts[0]

    try:
        company_id = int(
            parts[1]
        )

        record_id = int(
            parts[2]
        )

    except ValueError:
        answer_callback(
            callback_id
        )
        return


    # =====================================================
    # ПОДТВЕРДИТЬ
    # =====================================================

    if action == "confirm":
        answer_callback(
            callback_id,
            "Подтверждаю запись…",
        )

        success = (
            confirm_yclients_record(
                company_id,
                record_id,
            )
        )

        if success:
            update_reminder_row(
                company_id,
                record_id,
                {
                    "confirmed":
                        True,
                },
            )

            edit_message_buttons(
                chat_id,
                message_id,
                {
                    "inline_keyboard": [
                        [
                            {
                                "text":
                                    "❌ Отменить занятие",
                                "callback_data":
                                    (
                                        f"cancel:"
                                        f"{company_id}:"
                                        f"{record_id}"
                                    ),
                            }
                        ]
                    ]
                },
            )

            send_message(
                chat_id,
                "✅ Запись подтверждена!\n\n"
                "Спасибо 💙 "
                "Будем ждать вас "
                "на тренировке 🦭",
            )

        else:
            send_message(
                chat_id,
                "Не получилось подтвердить "
                "запись автоматически.\n\n"
                "Попробуйте ещё раз "
                "или свяжитесь с "
                "администратором.",
            )

        return


    # =====================================================
    # НАЖАЛ ОТМЕНИТЬ
    # =====================================================

    if action == "cancel":
        answer_callback(
            callback_id
        )

        record = get_record(
            company_id,
            record_id,
        )

        if not record:
            send_message(
                chat_id,
                "Не удалось получить "
                "данные записи.\n\n"
                "Пожалуйста, свяжитесь "
                "с администратором.",
            )
            return

        if not can_cancel_record(
            record
        ):
            admin = (
                admin_for_company(
                    company_id
                )
            )

            send_message(
                chat_id,
                "❌ Самостоятельная отмена "
                "уже недоступна.\n\n"
                "Отменить занятие через бота "
                "можно не позднее чем "
                "за 23 часа до начала.\n\n"
                "Сейчас, пожалуйста, "
                "напишите администратору "
                "вашего филиала:\n"
                f"👉 {admin}",
            )

            return

        send_message(
            chat_id,
            "Вы точно хотите "
            "отменить занятие?\n\n"
            "После отмены запись "
            "освободится.",
            confirm_cancel_buttons(
                company_id,
                record_id,
            ),
        )

        return


    # =====================================================
    # НЕТ, ОСТАВИТЬ
    # =====================================================

    if action == "cancel_no":
        answer_callback(
            callback_id,
            "Запись оставлена 💙",
        )

        edit_message_buttons(
            chat_id,
            message_id,
        )

        send_message(
            chat_id,
            "Хорошо 💙 "
            "Запись остаётся в силе. "
            "Ждём вас на тренировке 🦭",
        )

        return


    # =====================================================
    # ДА, ОТМЕНИТЬ
    # =====================================================

    if action == "cancel_yes":
        answer_callback(
            callback_id,
            "Проверяю возможность отмены…",
        )

        # Повторно проверяем время,
        # потому что клиент мог нажать
        # кнопку значительно позже.
        record = get_record(
            company_id,
            record_id,
        )

        if not record:
            send_message(
                chat_id,
                "Не удалось получить "
                "актуальную запись.\n\n"
                "Пожалуйста, свяжитесь "
                "с администратором.",
            )
            return

        if not can_cancel_record(
            record
        ):
            admin = (
                admin_for_company(
                    company_id
                )
            )

            edit_message_buttons(
                chat_id,
                message_id,
            )

            send_message(
                chat_id,
                "За время подтверждения "
                "до занятия осталось "
                "меньше 23 часов.\n\n"
                "Самостоятельная отмена "
                "уже недоступна.\n\n"
                "Напишите администратору:\n"
                f"👉 {admin}",
            )

            return

        success = (
            delete_yclients_record(
                company_id,
                record_id,
            )
        )

        if success:
            update_reminder_row(
                company_id,
                record_id,
                {
                    "cancelled":
                        True,
                },
            )

            edit_message_buttons(
                chat_id,
                message_id,
            )

            send_message(
                chat_id,
                "✅ Занятие отменено.\n\n"
                "Будем ждать вас "
                "в другой раз 💙🦭",
                main_keyboard(),
            )

        else:
            admin = (
                admin_for_company(
                    company_id
                )
            )

            send_message(
                chat_id,
                "Не получилось отменить "
                "запись автоматически.\n\n"
                "Пожалуйста, напишите "
                "администратору:\n"
                f"👉 {admin}",
            )

        return


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

    # INLINE BUTTONS
    callback = update.get(
        "callback_query"
    )

    if callback:
        handle_callback_query(
            callback
        )

        return (
            "ok",
            200,
        )


    message = update.get(
        "message"
    )

    if not message:
        return (
            "ok",
            200,
        )

    chat_id = (
        message
        .get(
            "chat",
            {},
        )
        .get(
            "id"
        )
    )

    if not chat_id:
        return (
            "ok",
            200,
        )

    text = message.get(
        "text",
        "",
    )

    contact = message.get(
        "contact"
    )

    sender_id = (
        message
        .get(
            "from",
            {},
        )
        .get(
            "id"
        )
    )


    # =====================================================
    # КОНТАКТ
    # =====================================================

    if contact:
        contact_user_id = (
            contact.get(
                "user_id"
            )
        )

        # Не разрешаем привязать
        # чужой Telegram-контакт.
        if (
            contact_user_id
            and sender_id
            and contact_user_id
            != sender_id
        ):
            send_message(
                chat_id,
                "Пожалуйста, отправьте "
                "именно свой номер "
                "кнопкой ниже.",
                phone_keyboard(),
            )

            return (
                "ok",
                200,
            )

        phone = normalize_phone(
            contact.get(
                "phone_number",
                "",
            )
        )

        action = (
            PENDING_ACTIONS
            .get(
                chat_id,
                "records",
            )
        )

        send_message(
            chat_id,
            "Проверяю номер "
            "в базе Капитана Булька… 🦭",
        )

        clients, errors = (
            find_client_everywhere(
                phone
            )
        )

        if not clients:
            send_message(
                chat_id,
                "Не нашла этот номер "
                "в нашей базе.\n\n"
                "Проверьте, пожалуйста, "
                "что это тот номер, "
                "который указан в YCLIENTS.",
                main_keyboard(),
            )

            PENDING_ACTIONS.pop(
                chat_id,
                None,
            )

            return (
                "ok",
                200,
            )

        name = get_client_name(
            clients
        )

        saved = save_user(
            chat_id,
            phone,
            name,
        )

        if not saved:
            send_message(
                chat_id,
                "Я нашла вас в базе, "
                "но пока не смогла "
                "сохранить номер.\n\n"
                "Попробуйте чуть позже.",
                main_keyboard(),
            )

            return (
                "ok",
                200,
            )

        PENDING_ACTIONS.pop(
            chat_id,
            None,
        )

        if action == "change_phone":
            send_message(
                chat_id,
                "✅ Новый номер сохранён 💙",
                main_keyboard(),
            )

            return (
                "ok",
                200,
            )

        if action == "subscription":
            send_message(
                chat_id,
                "Номер сохранён 💙\n\n"
                "Абонемент подключим "
                "следующим этапом.",
                main_keyboard(),
            )

            return (
                "ok",
                200,
            )

        show_records(
            chat_id,
            phone,
        )

        return (
            "ok",
            200,
        )


    # =====================================================
    # START
    # =====================================================

    if text == "/start":
        PENDING_ACTIONS.pop(
            chat_id,
            None,
        )

        saved_user = get_saved_user(
            chat_id
        )

        if saved_user:
            name = (
                saved_user.get(
                    "name"
                )
            )

            greeting = (
                f"С возвращением"
                f"{', ' + name if name else ''}! "
                "🦭💙\n\n"
                "Я уже помню ваш номер — "
                "повторно отправлять "
                "его не нужно."
            )

        else:
            greeting = (
                "Привет! 🦭\n"
                "Я Капитан Бульк — "
                "ваш помощник 💙\n\n"
                "Здесь можно записаться "
                "на занятие, посмотреть "
                "записи и управлять ими."
            )

        send_message(
            chat_id,
            greeting,
            main_keyboard(),
        )

        return (
            "ok",
            200,
        )


    # =====================================================
    # ЗАПИСАТЬСЯ
    # =====================================================

    if text == "🏊 Записаться":
        send_message(
            chat_id,
            "Выберите филиал:",
            branch_keyboard(),
        )

        return (
            "ok",
            200,
        )


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

        return (
            "ok",
            200,
        )


    # =====================================================
    # МОИ ЗАПИСИ
    # =====================================================

    if text == "📅 Мои записи":
        saved_user = get_saved_user(
            chat_id
        )

        if (
            saved_user
            and saved_user.get(
                "phone"
            )
        ):
            show_records(
                chat_id,
                saved_user[
                    "phone"
                ],
            )

        else:
            PENDING_ACTIONS[
                chat_id
            ] = "records"

            send_message(
                chat_id,
                "Чтобы найти ваши записи, "
                "один раз отправьте "
                "свой номер телефона.",
                phone_keyboard(),
            )

        return (
            "ok",
            200,
        )


    # =====================================================
    # АБОНЕМЕНТ
    # =====================================================

    if text == "🎟️ Мой абонемент":
        saved_user = get_saved_user(
            chat_id
        )

        if saved_user:
            send_message(
                chat_id,
                "Я уже помню ваш номер 💙\n\n"
                "Сам абонемент подключим "
                "следующим этапом.",
                main_keyboard(),
            )

        else:
            PENDING_ACTIONS[
                chat_id
            ] = "subscription"

            send_message(
                chat_id,
                "Отправьте номер телефона, "
                "который указан в YCLIENTS.",
                phone_keyboard(),
            )

        return (
            "ok",
            200,
        )


    # =====================================================
    # МОИ ДАННЫЕ
    # =====================================================

    if text == "⚙️ Мои данные":
        saved_user = get_saved_user(
            chat_id
        )

        if not saved_user:
            PENDING_ACTIONS[
                chat_id
            ] = "change_phone"

            send_message(
                chat_id,
                "Отправьте номер телефона, "
                "который указан в YCLIENTS.",
                phone_keyboard(),
            )

            return (
                "ok",
                200,
            )

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
            f"{masked_phone(phone)}",
            user_data_keyboard(),
        )

        return (
            "ok",
            200,
        )


    if text == "📱 Изменить номер":
        PENDING_ACTIONS[
            chat_id
        ] = "change_phone"

        send_message(
            chat_id,
            "Отправьте новый номер "
            "кнопкой ниже.",
            phone_keyboard(),
        )

        return (
            "ok",
            200,
        )


    # =====================================================
    # СВЯЗАТЬСЯ
    # =====================================================

    if text == "💬 Связаться с нами":
        send_message(
            chat_id,
            "Выберите нужный филиал "
            "и напишите администратору:\n\n"
            "📍 Нагатинская — "
            "@Bulk_nagatinskaya\n"
            "📍 Беломорская — "
            "@Bulk_levoberezhny\n"
            "📍 Базовская — "
            "@Bulk_hovrino\n"
            "📍 Истринская — "
            "@Bulk_molodezhnaia",
            main_keyboard(),
        )

        return (
            "ok",
            200,
        )


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

        return (
            "ok",
            200,
        )


    send_message(
        chat_id,
        "Выберите нужный "
        "пункт в меню 👇",
        main_keyboard(),
    )

    return (
        "ok",
        200,
    )


# =========================================================
# START APP
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
