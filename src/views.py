import datetime
import json
import logging
import os
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from dotenv import load_dotenv

# Импортируем get_greeting и load_user_settings из src.utils
from src.utils import get_greeting, load_user_settings

# Загружаем переменные окружения из .env
load_dotenv()

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)  # Уровень логирования можно изменить на INFO для отладки
handler = logging.StreamHandler()
formatter = logging.Formatter("%(levelname)s\t%(name)s:%(filename)s:%(lineno)d %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def read_transactions(file_path: str) -> pd.DataFrame:
    """
    Читает данные о финансовых операциях из Excel файла.
    """
    try:
        df = pd.read_excel(file_path)
        df.columns = [col.strip() if isinstance(col, str) else col for col in df.columns]
        return df
    except FileNotFoundError:
        logger.error(f"Файл не найден: {file_path}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Ошибка при чтении файла {file_path}: {e}")
        return pd.DataFrame()


def fetch_currency_rates(user_currencies: List[str]) -> List[Dict[str, Any]]:
    """
    Получает текущие курсы валют с помощью Free Currency API.
    Принимает список валют для запроса.
    Возвращает список словарей с валютой и курсом.
    """
    api_key = os.getenv("CURRENCY_API_KEY")
    if not api_key:
        logger.error("CURRENCY_API_KEY не установлен в .env")
        return []

    url = "https://api.currencyapi.com/v3/latest"
    # Запрашиваем курсы к рублю (RUB) для списка user_currencies
    params = {
        "apikey": api_key,
        "base_currency": "RUB",
        "currencies": ",".join(user_currencies) if user_currencies else "",
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Вызовет исключение для ошибок HTTP
        data = response.json()

        rates = []
        if "data" in data:
            for currency_code in user_currencies:
                if currency_code in data["data"]:
                    rates.append({"currency": currency_code, "rate": round(data["data"][currency_code]["value"], 2)})
                else:
                    logger.warning(f"Курс для валюты {currency_code} не найден в ответе API.")
                    rates.append({"currency": currency_code, "rate": None})
        return rates

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка запроса к API курсов валют: {e}")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при получении курсов валют: {e}")
    return []


def fetch_stock_prices(user_stocks: List[str]) -> List[Dict[str, Any]]:
    """
    Получает текущие цены акций S&P500 с помощью Alpha Vantage API.
    Принимает список символов акций для запроса.
    Возвращает список словарей с акцией и ценой.
    """
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        logger.error("ALPHA_VANTAGE_API_KEY не установлен в .env")
        return []

    stock_prices = []
    for stock_symbol in user_stocks:
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "GLOBAL_QUOTE",  # Функция для получения текущей котировки
            "symbol": stock_symbol,
            "apikey": api_key,
        }
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            # Alpha Vantage возвращает данные в "Global Quote" если успешно
            if "Global Quote" in data and len(data["Global Quote"]) > 0:
                # '05. price' - это цена закрытия
                price = float(data["Global Quote"].get("05. price", 0.0))
                stock_prices.append({"stock": stock_symbol, "price": round(price, 2)})
            elif "Error Message" in data:
                logger.warning(f"Ошибка API Alpha Vantage для акции {stock_symbol}: {data['Error Message']}")
                stock_prices.append({"stock": stock_symbol, "price": None})
            else:
                logger.warning(
                    f"Не удалось получить данные для акции {stock_symbol}. Неожиданный формат ответа: {data}"
                )
                stock_prices.append({"stock": stock_symbol, "price": None})

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка запроса к API акций для {stock_symbol}: {e}")
            stock_prices.append({"stock": stock_symbol, "price": None})
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при получении цен акции {stock_symbol}: {e}")
            stock_prices.append({"stock": stock_symbol, "price": None})
    return stock_prices


def main_page(date_time_str: str) -> str:  # <--- Меняем тип возвращаемого значения на str
    """
    Формирует данные для главной страницы на основе транзакций, курсов валют и цен акций
    и возвращает их в виде JSON-строки.
    """
    try:
        # Преобразуем входящую строку даты в datetime объект один раз в начале
        try:
            current_datetime = datetime.datetime.strptime(date_time_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            logger.error(f"Некорректный формат даты/времени: {date_time_str}")
            # Возвращаем JSON-строку даже в случае ошибки
            return json.dumps(
                {
                    "greeting": "Ошибка: Некорректная дата",
                    "cards": [],
                    "top_transactions": [],
                    "currency_rates": [],
                    "stock_prices": [],
                },
                indent=4,
                ensure_ascii=False,
            )

        # Теперь передавайте current_datetime в get_greeting
        greeting = get_greeting(current_datetime)

        user_settings = load_user_settings("settings.json")
        user_currencies = user_settings.get("user_currencies", [])
        user_stocks = user_settings.get("user_stocks", [])

        transactions_df = read_transactions("data/operations.xlsx")

        if not isinstance(transactions_df, pd.DataFrame):
            logger.error("read_transactions did not return a DataFrame.")
            return json.dumps(
                {  # <--- Возвращаем JSON-строку
                    "greeting": "Ошибка при загрузке данных",
                    "cards": [],
                    "top_transactions": [],
                    "currency_rates": [],
                    "stock_prices": [],
                },
                indent=4,
                ensure_ascii=False,
            )

        if transactions_df.empty:
            return json.dumps(
                {  # <--- Возвращаем JSON-строку
                    "greeting": greeting,
                    "cards": [],
                    "top_transactions": [],
                    "currency_rates": fetch_currency_rates(user_currencies),
                    "stock_prices": fetch_stock_prices(user_stocks),
                },
                indent=4,
                ensure_ascii=False,
            )

        # Преобразование колонок к правильным типам
        if "Дата операции" in transactions_df.columns:
            transactions_df["Дата операции"] = pd.to_datetime(
                transactions_df["Дата операции"], errors="coerce", dayfirst=True
            )
        else:
            transactions_df["Дата операции"] = pd.Series(pd.NaT, index=transactions_df.index)

        if "Дата платежа" in transactions_df.columns:
            transactions_df["Дата платежа"] = pd.to_datetime(
                transactions_df["Дата платежа"], errors="coerce", dayfirst=True
            )
        else:
            transactions_df["Дата платежа"] = pd.Series(pd.NaT, index=transactions_df.index)

        numeric_cols = [
            "Сумма операции",
            "Сумма платежа",
            "Кешбэк",
            "Бонусы (включая кешбэк)",
            "Округление на инвесткопилку",
            "Сумма операции с округлением",
            "MCC",
        ]
        for col in numeric_cols:
            if col in transactions_df.columns:
                transactions_df[col] = pd.to_numeric(
                    transactions_df[col].astype(str).str.replace(",", "."), errors="coerce"
                ).fillna(0.0)
            else:
                transactions_df[col] = pd.Series(0.0, index=transactions_df.index, dtype="float64")

        # Обработка "Номер карты"
        if "Номер карты" in transactions_df.columns:
            transactions_df["Номер карты"] = transactions_df["Номер карты"].astype(str)
            transactions_df["Последние 4 цифры карты"] = transactions_df["Номер карты"].apply(
                lambda x: f"**{str(x)[-4:]}" if pd.notna(x) and len(str(x)) >= 4 else None
            )
        else:
            transactions_df["Последние 4 цифры карты"] = pd.Series(
                [None] * len(transactions_df), index=transactions_df.index, dtype="object"
            )

        # === Фильтрация данных по дате ===
        start_of_month = current_datetime.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        transactions_df_filtered = transactions_df[
            (transactions_df["Дата операции"] >= start_of_month)
            & (transactions_df["Дата операции"] <= current_datetime)
        ].copy()

        # Если после фильтрации DataFrame стал пустым, возвращаем базовый ответ
        if transactions_df_filtered.empty:
            return json.dumps(
                {  # <--- Возвращаем JSON-строку
                    "greeting": greeting,
                    "cards": [],
                    "top_transactions": [],
                    "currency_rates": fetch_currency_rates(user_currencies),
                    "stock_prices": fetch_stock_prices(user_stocks),
                },
                indent=4,
                ensure_ascii=False,
            )

        # Фильтрация только трат (отрицательная сумма платежа)
        if "Сумма платежа" not in transactions_df_filtered.columns or not pd.api.types.is_numeric_dtype(
            transactions_df_filtered["Сумма платежа"]
        ):
            transactions_df_filtered["Сумма платежа"] = pd.Series(
                0.0, index=transactions_df_filtered.index, dtype="float64"
            )

        spending_transactions = transactions_df_filtered[transactions_df_filtered["Сумма платежа"] < 0].copy()

        # Группировка и подсчет для сводки по картам
        cards_summary = []
        if not spending_transactions.empty:
            if (
                "Последние 4 цифры карты" in spending_transactions.columns
                and spending_transactions["Последние 4 цифры карты"].notna().any()
            ):
                card_groups = spending_transactions.groupby("Последние 4 цифры карты", dropna=True)
                for card_digits, group in card_groups:
                    total_spent = abs(group["Сумма платежа"].sum())
                    total_cashback = group["Кешбэк"].sum()
                    cards_summary.append(
                        {
                            "last_digits": card_digits,
                            "total_spent": round(total_spent, 2),
                            "cashback": round(total_cashback, 2),
                        }
                    )

        # Топ-5 транзакций
        top_transactions_list = []
        if "Сумма платежа" in transactions_df_filtered.columns:
            transactions_df_filtered["Absolute_Payment_Amount"] = transactions_df_filtered["Сумма платежа"].abs()
            sorted_transactions = transactions_df_filtered.sort_values(
                by="Absolute_Payment_Amount", ascending=False
            ).head(5)

            for _, row in sorted_transactions.iterrows():
                top_transactions_list.append(
                    {
                        "date": row["Дата операции"].strftime("%d.%m.%Y") if pd.notna(row["Дата операции"]) else None,
                        "amount": float(row["Сумма платежа"]),
                        "currency": row["Валюта платежа"],
                        "description": row["Описание"],
                    }
                )

        # Получение курсов валют и цен акций (теперь вызываются с user_currencies/user_stocks)
        currency_rates_data = fetch_currency_rates(user_currencies)
        stock_prices_data = fetch_stock_prices(user_stocks)

        # Собираем финальный словарь
        final_response_data = {
            "greeting": greeting,
            "cards": cards_summary,
            "top_transactions": top_transactions_list,
            "currency_rates": currency_rates_data,
            "stock_prices": stock_prices_data,
        }
        # <--- Преобразуем словарь в JSON-строку перед возвратом
        return json.dumps(final_response_data, indent=4, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Произошла непредвиденная ошибка в main_page: {e}")
        # Возвращаем JSON-строку даже в случае ошибки
        return json.dumps(
            {
                "greeting": "Ошибка при загрузке данных",
                "cards": [],
                "top_transactions": [],
                "currency_rates": [],
                "stock_prices": [],
            },
            indent=4,
            ensure_ascii=False,
        )
