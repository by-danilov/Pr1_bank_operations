import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
import datetime
import requests
import json  # <--- Добавляем импорт json

# Предполагаем, что main_page находится в src.views
from src.views import main_page, fetch_currency_rates, fetch_stock_prices
from src.utils import get_greeting, load_user_settings # ИМПОРТ ИЗ UTILS


@pytest.fixture
def mock_transactions_df():
    data = {
        "Дата операции": ["2020-01-01 10:00:00", "2020-01-02 11:00:00", "2020-01-03 12:00:00", "2020-01-04 13:00:00", "2020-01-05 14:00:00", "2020-01-06 15:00:00", "2020-01-07 16:00:00"],
        "Дата платежа": ["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04", "2020-01-05", "2020-01-06", "2020-01-07"],
        "Номер карты": ["*7197", "*5091", "*7197", "*7197", "*7197", "*5091", "*7197"],
        "Статус": ["OK", "OK", "OK", "OK", "OK", "OK", "OK"],
        "Сумма операции": [-160.89, -564.00, -20000.00, -383.00, -829.00, 453.00, -1198.23],
        "Валюта операции": ["RUB", "RUB", "RUB", "RUB", "RUB", "RUB", "RUB"],
        "Сумма платежа": [-160.89, -564.00, -20000.00, -383.00, -829.00, 453.00, -1198.23],
        "Валюта платежа": ["RUB", "RUB", "RUB", "RUB", "RUB", "RUB", "RUB"],
        "Кешбэк": [3.00, 5.00, 0.00, 7.00, 0.00, 0.00, 0.00],
        "Категория": ["Фастфуд", "Супермаркеты", "Переводы", "Дом", "Супермаркеты", "Кешбэк", "Переводы"],
        "MCC": [5814, 5411, 4829, 5200, 5411, 0, 4829],
        "Описание": ["Колхоз", "Ozon.ru", "Константин Л.", "МаксидоМ", "Лента", "Кешбэк", "Перевод"],
        "Бонусы (включая кешбэк)": [3.00, 5.00, 0.00, 7.00, 0.00, 0.00, 0.00],
        "Округление на инвесткопилку": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "Сумма операции с округлением": [160.89, 564.00, 20000.00, 383.00, 829.00, 453.00, 1198.23]
    }
    df = pd.DataFrame(data)
    for col in ["Сумма операции", "Сумма платежа", "Кешбэк", "MCC",
                "Бонусы (включая кешбэк)", "Округление на инвесткопилку", "Сумма операции с округлением"]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    for col in ["Дата операции", "Дата платежа"]:
        df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=False)
    df["Номер карты"] = df["Номер карты"].astype(str)
    return df


# === НОВЫЕ ТЕСТЫ ДЛЯ API ФУНКЦИЙ ===
@patch("src.views.requests.get")
@patch("src.views.os.getenv")
def test_fetch_currency_rates_success(mock_getenv, mock_requests_get):
    """
    Тестирует успешное получение курсов валют.
    """
    mock_getenv.return_value = "fake_api_key"
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": {
            "USD": {"value": 91.23},
            "EUR": {"value": 101.45},
            "GBP": {"value": 115.67} # Лишняя валюта, не запрашивали
        }
    }
    mock_requests_get.return_value = mock_response

    user_currencies = ["USD", "EUR"]
    rates = fetch_currency_rates(user_currencies)

    assert len(rates) == 2
    assert {"currency": "USD", "rate": 91.23} in rates
    assert {"currency": "EUR", "rate": 101.45} in rates
    mock_requests_get.assert_called_once_with(
        "https://api.currencyapi.com/v3/latest",
        params={"apikey": "fake_api_key", "base_currency": "RUB", "currencies": "USD,EUR"}
    )

@patch("src.views.requests.get", side_effect=requests.exceptions.RequestException("API error"))
@patch("src.views.os.getenv")
def test_fetch_currency_rates_api_error(mock_getenv, mock_requests_get):
    """
    Тестирует обработку ошибок API при получении курсов валют.
    """
    mock_getenv.return_value = "fake_api_key"
    user_currencies = ["USD"]
    rates = fetch_currency_rates(user_currencies)
    assert rates == []

@patch("src.views.os.getenv")
def test_fetch_currency_rates_no_api_key(mock_getenv):
    """
    Тестирует случай, когда нет API ключа для валют.
    """
    mock_getenv.return_value = None
    rates = fetch_currency_rates(["USD"])
    assert rates == []

@patch("src.views.requests.get")
@patch("src.views.os.getenv")
def test_fetch_stock_prices_success(mock_getenv, mock_requests_get):
    """
    Тестирует успешное получение цен акций.
    """
    mock_getenv.return_value = "fake_api_key"
    mock_response_aapl = MagicMock()
    mock_response_aapl.json.return_value = {"Global Quote": {"05. price": "170.50"}}
    mock_response_googl = MagicMock()
    mock_response_googl.json.return_value = {"Global Quote": {"05. price": "1800.75"}}

    mock_requests_get.side_effect = [mock_response_aapl, mock_response_googl]

    user_stocks = ["AAPL", "GOOGL"]
    prices = fetch_stock_prices(user_stocks)

    assert len(prices) == 2
    assert {"stock": "AAPL", "price": 170.50} in prices
    assert {"stock": "GOOGL", "price": 1800.75} in prices
    assert mock_requests_get.call_count == 2

@patch("src.views.requests.get", side_effect=requests.exceptions.RequestException("API error"))
@patch("src.views.os.getenv")
def test_fetch_stock_prices_api_error(mock_getenv, mock_requests_get):
    """
    Тестирует обработку ошибок API при получении цен акций.
    """
    mock_getenv.return_value = "fake_api_key"
    user_stocks = ["AAPL"]
    prices = fetch_stock_prices(user_stocks)
    assert prices == [{"stock": "AAPL", "price": None}] # Должен вернуть None для акции

@patch("src.views.os.getenv")
def test_fetch_stock_prices_no_api_key(mock_getenv):
    """
    Тестирует случай, когда нет API ключа для акций.
    """
    mock_getenv.return_value = None
    prices = fetch_stock_prices(["AAPL"])
    assert prices == []

# === ТЕСТЫ ДЛЯ main_page ===
# Изменен порядок патчей, чтобы сначала мокать src.utils, затем src.views
@patch("src.utils.get_greeting")
@patch("src.utils.load_user_settings")
@patch("src.views.read_transactions")
@patch("src.views.fetch_currency_rates")
@patch("src.views.fetch_stock_prices")
def test_main_page_success(
    mock_fetch_stock_prices,
    mock_fetch_currency_rates,
    mock_read_transactions,
    mock_load_user_settings,
    mock_get_greeting,
    mock_transactions_df,
):
    """
    Тестирует успешное формирование ответа main_page.
    """
    mock_get_greeting.return_value = "Добрый день"
    mock_load_user_settings.return_value = {
        "user_currencies": ["USD", "EUR"],
        "user_stocks": ["AAPL", "GOOGL"],
    }
    mock_read_transactions.return_value = mock_transactions_df

    mock_fetch_currency_rates.return_value = [
        {"currency": "USD", "rate": 90.00},
        {"currency": "EUR", "rate": 100.00},
    ]
    mock_fetch_stock_prices.return_value = [
        {"stock": "AAPL", "price": 150.00},
        {"stock": "GOOGL", "price": 2800.00},
    ]

    date_time_str = "2020-01-05 16:00:00"
    response_json = main_page(date_time_str) # <--- Получаем JSON-строку
    response = json.loads(response_json) # <--- Преобразуем в словарь

    # Проверки
    assert response["greeting"] == "Добрый день"
    assert len(response["cards"]) > 0

    card_7197 = next((card for card in response["cards"] if card["last_digits"] == "**7197"), None)
    assert card_7197 is not None
    assert card_7197["total_spent"] == round(abs(-160.89) + abs(-20000.00) + abs(-383.00) + abs(-829.00), 2)
    assert card_7197["cashback"] == round(3.00 + 7.00, 2)

    card_5091 = next((card for card in response["cards"] if card["last_digits"] == "**5091"), None)
    assert card_5091 is not None
    assert card_5091["total_spent"] == round(abs(-564.00), 2)
    assert card_5091["cashback"] == round(5.00, 2)

    assert len(response["top_transactions"]) == 5
    assert response["top_transactions"][0]["amount"] == -20000.00
    assert response["top_transactions"][1]["amount"] == -829.00
    assert response["top_transactions"][2]["amount"] == -564.00
    assert response["top_transactions"][3]["amount"] == -383.00
    assert response["top_transactions"][4]["amount"] == -160.89

    assert len(response["currency_rates"]) == 2
    assert response["currency_rates"][0]["currency"] == "USD"
    assert response["currency_rates"][0]["rate"] == 90.00
    assert response["currency_rates"][1]["currency"] == "EUR"
    assert response["currency_rates"][1]["rate"] == 100.00

    assert len(response["stock_prices"]) == 2
    assert response["stock_prices"][0]["stock"] == "AAPL"
    assert response["stock_prices"][0]["price"] == 150.00
    assert response["stock_prices"][1]["stock"] == "GOOGL"
    assert response["stock_prices"][1]["price"] == 2800.00


# Создаем функцию, которая будет возвращать пустой DataFrame с нужными колонками и типами
def create_empty_mock_df():
    empty_df_columns = {
        "Дата операции": 'datetime64[ns]',
        "Дата платежа": 'datetime64[ns]',
        "Номер карты": 'str',
        "Статус": 'str',
        "Сумма операции": 'float64',
        "Валюта операции": 'str',
        "Валюта платежа": 'str',
        "Сумма платежа": 'float64',
        "Кешбэк": 'float64',
        "Категория": 'str',
        "MCC": 'float64',
        "Описание": 'str',
        "Бонусы (включая кешбэк)": 'float64',
        "Округление на инвесткопилку": 'float64',
        "Сумма операции с округлением": 'float64'
    }
    return pd.DataFrame({col: pd.Series(dtype=dtype) for col, dtype in empty_df_columns.items()})


# Изменение порядка патчей и аргументов
@patch("src.utils.get_greeting")
@patch("src.utils.load_user_settings")
@patch("src.views.read_transactions")
@patch("src.views.fetch_currency_rates")
@patch("src.views.fetch_stock_prices")
def test_main_page_empty_transactions(
    mock_fetch_stock_prices,
    mock_fetch_currency_rates,
    mock_read_transactions,
    mock_load_user_settings,
    mock_get_greeting
):
    """
    Тестирует main_page, когда нет транзакций.
    """
    mock_get_greeting.return_value = "Добрый день"
    mock_load_user_settings.return_value = {
        "user_currencies": [],
        "user_stocks": [],
    }

    mock_read_transactions.return_value = create_empty_mock_df()
    mock_fetch_currency_rates.return_value = []
    mock_fetch_stock_prices.return_value = []


    date_time_str = "2021-12-31 16:00:00"
    response_json = main_page(date_time_str) # <--- Получаем JSON-строку
    response = json.loads(response_json) # <--- Преобразуем в словарь

    assert response["greeting"] == "Добрый день"
    assert response["cards"] == []
    assert response["top_transactions"] == []
    assert response["currency_rates"] == []
    assert response["stock_prices"] == []


@patch("src.views.read_transactions", side_effect=Exception("Database error"))
@patch("src.utils.get_greeting")
@patch("src.utils.load_user_settings")
@patch("src.views.fetch_currency_rates")
@patch("src.views.fetch_stock_prices")
def test_main_page_general_exception(
    mock_fetch_stock_prices,
    mock_fetch_currency_rates,
    mock_load_user_settings,
    mock_get_greeting,
    mock_read_transactions
):
    """
    Тестирует обработку общей ошибки внутри main_page.
    """
    mock_get_greeting.return_value = "Добрый день"
    mock_load_user_settings.return_value = {}
    mock_fetch_currency_rates.return_value = []
    mock_fetch_stock_prices.return_value = []

    date_time_str = "2021-12-31 16:00:00"
    response_json = main_page(date_time_str) # <--- Получаем JSON-строку
    response = json.loads(response_json) # <--- Преобразуем в словарь

    assert response["greeting"] == "Ошибка при загрузке данных"


# Новый тест для некорректного формата даты
@patch("src.views.read_transactions")
@patch("src.utils.load_user_settings")
@patch("src.utils.get_greeting")
@patch("src.views.fetch_currency_rates")
@patch("src.views.fetch_stock_prices")
def test_main_page_invalid_date_format(
    mock_fetch_stock_prices,
    mock_fetch_currency_rates,
    mock_get_greeting,
    mock_load_user_settings,
    mock_read_transactions
):
    """
    Тестирует main_page с некорректным форматом даты,
    что должно привести к раннему выходу с ошибкой.
    """
    mock_get_greeting.return_value = "Добрый день"
    mock_load_user_settings.return_value = {}
    mock_read_transactions.return_value = create_empty_mock_df()
    mock_fetch_currency_rates.return_value = []
    mock_fetch_stock_prices.return_value = []

    date_time_str = "invalid-date"
    response_json = main_page(date_time_str) # <--- Получаем JSON-строку
    response = json.loads(response_json) # <--- Преобразуем в словарь

    assert response["greeting"] == "Ошибка: Некорректная дата"
    assert response["cards"] == []
    assert response["top_transactions"] == []
    assert response["currency_rates"] == []
    assert response["stock_prices"] == []
    mock_get_greeting.assert_not_called()
