import json
from datetime import datetime
from unittest.mock import mock_open, patch

import pandas as pd
import pytest

from src.utils import filter_by_date, get_greeting, load_user_settings
from src.views import read_transactions


# Фикстура для mock DataFrame
@pytest.fixture
def sample_dataframe():
    """
    Возвращает фиктивный DataFrame для тестирования.
    Колонки здесь должны быть строками, как их прочитал бы pandas.read_excel,
    прежде чем read_transactions их обработает.
    """
    data = {
        "Дата операции": ["2023-01-01 10:00:00", "2023-01-05 12:00:00", "2023-01-10 14:00:00"],
        "Дата платежа": ["2023-01-01", "2023-01-05", "2023-01-10"],
        "Номер карты": ["*1234", "*5678", "*1234"],
        "Статус": ["OK", "OK", "CANCELED"],
        "Сумма операции": [100.0, 200.0, 50.0],
        "Валюта операции": ["RUB", "USD", "RUB"],
        "Сумма платежа": [-100.0, -200.0, -50.0],
        "Валюта платежа": ["RUB", "USD", "RUB"],
        "Кешбэк": [1.0, 2.0, 0.5],
        "Категория": ["Еда", "Одежда", "Транспорт"],
        "MCC": [123, 456, 789],
        "Описание": ["Макдональдс", "H&M", "Автобус"],
        "Бонусы (включая кешбэк)": [1.0, 2.0, 0.5],
        "Округление на инвесткопилку": [0.0, 0.0, 0.0],
        "Сумма операции с округлением": [100.0, 200.0, 50.0],
    }
    # pandas.read_excel по умолчанию может читать даты как строки,
    # а затем функция read_transactions должна их преобразовать.
    # Поэтому для фикстуры, представляющей "сырые" данные из файла, лучше использовать строки.
    return pd.DataFrame(data)


# Тесты для read_transactions
@patch("pandas.read_excel")
def test_read_transactions_success(mock_read_excel, sample_dataframe):
    """Тестирует успешное чтение файла Excel."""
    mock_read_excel.return_value = sample_dataframe
    df = read_transactions("dummy_path.xlsx")
    assert not df.empty
    # После strip() колонка будет 'Номер карты'
    assert "Номер карты" in df.columns
    mock_read_excel.assert_called_once_with("dummy_path.xlsx")


@patch("pandas.read_excel", side_effect=FileNotFoundError)
def test_read_transactions_file_not_found(mock_read_excel):
    """Тестирует обработку отсутствующего файла Excel."""
    df = read_transactions("non_existent_path.xlsx")
    assert df.empty
    mock_read_excel.assert_called_once_with("non_existent_path.xlsx")


@patch("pandas.read_excel", side_effect=Exception("Permission denied"))
def test_read_transactions_general_error(mock_read_excel):
    """Тестирует обработку общих ошибок при чтении Excel."""
    df = read_transactions("error_path.xlsx")
    assert df.empty
    mock_read_excel.assert_called_once_with("error_path.xlsx")


def test_read_transactions_columns_stripped(sample_dataframe):
    """Тестирует, что пробелы в именах колонок обрезаются."""
    # Создаем DataFrame с пробелами в именах колонок,
    # который *как будто* вернул read_excel
    df_with_initial_spaces = sample_dataframe.copy()
    # Применяем пробелы к КОПИИ исходных колонок, чтобы не изменять фикстуру
    # Здесь sample_dataframe.columns - это список строк, как и ожидается.
    df_with_initial_spaces.columns = [f" {col} " for col in sample_dataframe.columns]

    with patch("pandas.read_excel", return_value=df_with_initial_spaces):
        df = read_transactions("dummy_path.xlsx")

        # Получаем ожидаемые (чистые) имена колонок из оригинальной фикстуры
        expected_clean_columns = sample_dataframe.columns.tolist()

        # Проверяем, что все колонки в результате присутствуют и не содержат пробелов
        # И что их имена точно соответствуют ожидаемым (чистым) именам
        assert len(df.columns) == len(expected_clean_columns)
        for i, col_name in enumerate(df.columns):
            assert isinstance(col_name, str)  # Убедимся, что это строка
            assert (
                col_name == expected_clean_columns[i]
            )  # Убедимся, что имя колонки точно совпадает с ожидаемым (без пробелов)
            assert not col_name.startswith(" ")  # Убедимся, что нет начальных пробелов
            assert not col_name.endswith(" ")  # Убедимся, что нет конечных пробелов


# Тесты для get_greeting
def test_get_greeting_morning():
    """Тестирует приветствие 'Доброе утро'."""
    assert get_greeting(datetime(2023, 1, 1, 8, 0, 0)) == "Доброе утро"
    assert get_greeting(datetime(2023, 1, 1, 5, 0, 0)) == "Доброе утро"
    assert get_greeting(datetime(2023, 1, 1, 11, 59, 59)) == "Доброе утро"


def test_get_greeting_day():
    """Тестирует приветствие 'Добрый день'."""
    assert get_greeting(datetime(2023, 1, 1, 12, 0, 0)) == "Добрый день"
    assert get_greeting(datetime(2023, 1, 1, 16, 59, 59)) == "Добрый день"


def test_get_greeting_evening():
    """Тестирует приветствие 'Добрый вечер'."""
    assert get_greeting(datetime(2023, 1, 1, 17, 0, 0)) == "Добрый вечер"
    assert get_greeting(datetime(2023, 1, 1, 21, 59, 59)) == "Добрый вечер"


def test_get_greeting_night():
    """Тестирует приветствие 'Доброй ночи'."""
    assert get_greeting(datetime(2023, 1, 1, 22, 0, 0)) == "Доброй ночи"
    assert get_greeting(datetime(2023, 1, 1, 4, 59, 59)) == "Доброй ночи"


# Тесты для load_user_settings
@patch("builtins.open", new_callable=mock_open, read_data='{"user_currencies": ["USD"], "user_stocks": ["AAPL"]}')
@patch("json.load")
def test_load_user_settings_success(mock_json_load, mock_file):
    """Тестирует успешную загрузку настроек пользователя."""
    mock_json_load.return_value = {"user_currencies": ["USD"], "user_stocks": ["AAPL"]}
    settings = load_user_settings("settings.json")
    assert settings == {"user_currencies": ["USD"], "user_stocks": ["AAPL"]}
    mock_file.assert_called_once_with("settings.json", "r", encoding="utf-8")
    mock_json_load.assert_called_once()


@patch("builtins.open", side_effect=FileNotFoundError)
def test_load_user_settings_file_not_found(mock_file):
    """Тестирует обработку отсутствующего файла настроек."""
    settings = load_user_settings("non_existent_settings.json")
    assert settings == {}
    mock_file.assert_called_once_with("non_existent_settings.json", "r", encoding="utf-8")


@patch("builtins.open", new_callable=mock_open, read_data='{"user_currencies": ["USD", }')  # Некорректный JSON
@patch("json.load", side_effect=json.JSONDecodeError("Expecting value", doc="json_string", pos=0))
def test_load_user_settings_json_decode_error(mock_json_load, mock_file):
    """Тестирует обработку некорректного JSON в файле настроек."""
    settings = load_user_settings("invalid_settings.json")
    assert settings == {}
    mock_file.assert_called_once_with("invalid_settings.json", "r", encoding="utf-8")
    mock_json_load.assert_called_once()


@patch("builtins.open", new_callable=mock_open)
@patch("json.load", side_effect=Exception("Unexpected error"))
def test_load_user_settings_general_error(mock_json_load, mock_file):
    """Тестирует обработку общей ошибки при загрузке настроек."""
    settings = load_user_settings("error_settings.json")
    assert settings == {}
    mock_file.assert_called_once_with("error_settings.json", "r", encoding="utf-8")
    mock_json_load.assert_called_once()


# Тесты для filter_by_date
def test_filter_by_date_success():
    """Тестирует успешную фильтрацию данных по дате."""
    data = [
        {"date": "2023-01-01 10:00:00", "value": 10},
        {"date": "2023-01-05 12:00:00", "value": 20},
        {"date": "2023-01-10 14:00:00", "value": 30},
    ]
    filtered = filter_by_date(data, "2023-01-06 00:00:00")
    assert len(filtered) == 2
    assert filtered[0]["value"] == 10
    assert filtered[1]["value"] == 20


def test_filter_by_date_no_match():
    """Тестирует фильтрацию, когда нет подходящих данных."""
    data = [
        {"date": "2023-01-10 14:00:00", "value": 30},
    ]
    filtered = filter_by_date(data, "2023-01-01 00:00:00")
    assert len(filtered) == 0


def test_filter_by_date_invalid_date_format_in_data():
    """Тестирует обработку некорректного формата даты в данных."""
    data = [
        {"date": "2023-01-01 10:00:00", "value": 10},
        {"date": "invalid-date", "value": 20},
    ]
    # Ожидаем, что некорректная дата будет проигнорирована, если в функции filter_by_date
    # обрабатывается исключение ValueError при парсинге item["date"]
    # (в текущей реализации utils.py filter_by_date, эта ошибка будет залогирована, а элемент пропущен)
    filtered = filter_by_date(data, "2023-01-05 00:00:00")
    assert len(filtered) == 1
    assert filtered[0]["value"] == 10


def test_filter_by_date_invalid_filter_date_format():
    """Тестирует обработку некорректного формата фильтрующей даты."""
    data = [
        {"date": "2023-01-01 10:00:00", "value": 10},
    ]
    filtered = filter_by_date(data, "invalid-filter-date")
    assert filtered == []  # Должен вернуть пустой список, так как filter_by_date обрабатывает ValueError


def test_filter_by_date_empty_data():
    """Тестирует фильтрацию пустого списка."""
    data = []
    filtered = filter_by_date(data, "2023-01-01 00:00:00")
    assert filtered == []


def test_filter_by_date_missing_date_key():
    """Тестирует обработку словарей без ключа 'date'."""
    data = [
        {"value": 10},  # Нет ключа 'date'
        {"date": "2023-01-01 10:00:00", "value": 20},
    ]
    filtered = filter_by_date(data, "2023-01-05 00:00:00")
    assert len(filtered) == 1
    assert filtered[0]["value"] == 20
