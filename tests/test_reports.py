import pandas as pd
import pytest
from unittest.mock import patch, mock_open, call
import datetime
import os
import logging
import json

# Импортируем тестируемые функции и декораторы
from src.reports import spending_by_weekday, log_and_save_report, logger as reports_logger


# Фикстура для создания примера DataFrame с транзакциями
@pytest.fixture
def sample_transactions_df():
    data = {
        'Дата операции': [
            '2024-03-01', '2024-03-02', '2024-03-03',  # Март
            '2024-03-04', '2024-03-05', '2024-04-01', '2024-04-02', '2024-04-03',  # Март, Апрель
            '2024-05-01', '2024-05-02', '2024-02-03', '2024-02-05',  # Май, Февраль (ранние даты)
            '2024-05-06', '2024-05-07'  # Май
        ],
        'Сумма операции': [
            -100.0, -200.0, -300.0,
            -150.0, -250.0, -350.0, -220.0, -75.0,
            -120.0, -50.0, -10.0, -50.0,
            -10.0, -20.0
        ],
        'Категория': [
            'Cat0', 'Cat1', 'Cat2',
            'Cat3', 'Cat4', 'Cat5', 'Cat6', 'Cat7',
            'Cat8', 'Cat9', 'Cat10', 'Cat11',
            'Cat12', 'Cat13'
        ]
    }
    df = pd.DataFrame(data)
    # Важно: преобразование даты должно соответствовать тому, как это делается в функции
    df['Дата операции'] = pd.to_datetime(df['Дата операции'], errors='coerce', dayfirst=True)
    return df


@pytest.fixture
def empty_transactions_df():
    return pd.DataFrame(columns=['Дата операции', 'Сумма операции', 'Категория'])


# Тесты для spending_by_weekday
@pytest.mark.parametrize(
    "test_date, expected_average_spending",
    [
        (
                "2024-05-10",  # Текущая дата, 3 месяца назад до 2024-02-10 (включительно)
                {  # Средние траты за 2024-02-10 до 2024-05-10
                    'Понедельник': 170.00,  # (150+350+10)/3 от 2024-03-04, 2024-04-01, 2024-05-06
                    'Вторник': 235.00,  # (250+220+20)/3 от 2024-03-05, 2024-04-02, 2024-05-07
                    'Среда': 97.50,  # (75+120)/2 от 2024-04-03, 2024-05-01
                    'Четверг': 50.00,  # 50 от 2024-05-02
                    'Пятница': 100.00,  # 100 от 2024-03-01
                    'Суббота': 200.00,  # 200 от 2024-03-02
                    'Воскресенье': 300.00  # 300 от 2024-03-03
                }
        ),
        (
                "2024-04-15",  # Текущая дата, 3 месяца назад до 2024-01-15 (включительно)
                {  # Средние траты за 2024-01-15 до 2024-04-15
                    'Понедельник': 250.00,  # (150+350)/2 от 2024-03-04, 2024-04-01
                    'Вторник': 235.00,  # (250+220)/2 от 2024-03-05, 2024-04-02
                    'Среда': 75.00,  # 75 от 2024-04-03
                    'Четверг': 0.00,  # Нет трат в этот период
                    'Пятница': 100.00,  # 100 от 2024-03-01
                    'Суббота': 200.00,  # 200 от 2024-03-02
                    'Воскресенье': 300.00  # 300 от 2024-03-03
                }
        ),
    ]
)
def test_spending_by_weekday_with_date(sample_transactions_df, test_date, expected_average_spending):
    """
    Тестирует функцию spending_by_weekday с заданной датой.
    """
    result_df = spending_by_weekday(sample_transactions_df, test_date)

    # Проверяем, что в результате есть все дни недели в правильном порядке
    ordered_weekdays = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    assert list(result_df['День недели']) == ordered_weekdays

    # Проверяем, что средние траты соответствуют ожиданиям
    result_dict = result_df.set_index('День недели')['Средние траты'].to_dict()

    # Сравниваем с ожидаемыми значениями, учитывая возможные отсутствующие дни
    for day in ordered_weekdays:  # Проверяем каждый день из ожидаемого порядка
        expected_avg = expected_average_spending.get(day, 0.00)  # Получаем ожидаемое или 0.00, если дня нет
        assert result_dict.get(day, 0.00) == pytest.approx(expected_avg, 0.01)


def test_spending_by_weekday_no_date(sample_transactions_df):
    """
    Тестирует функцию spending_by_weekday без указания даты (используется текущая).
    Мокнуть datetime.now() для воспроизводимости.
    """
    # Мокаем datetime.now() для воспроизводимости теста
    with patch('src.reports.datetime') as mock_dt:
        mock_dt.datetime.now.return_value = datetime.datetime(2024, 5, 10, 12, 0, 0)
        mock_dt.datetime.strptime = datetime.datetime.strptime  # Сохраняем оригинальный strptime
        mock_dt.timedelta = datetime.timedelta  # Сохраняем оригинальный timedelta
        mock_dt.date = datetime.date  # Сохраняем оригинальный date
        mock_dt.MINYEAR = datetime.MINYEAR
        mock_dt.MAXYEAR = datetime.MAXYEAR
        mock_dt.timezone = datetime.timezone  # Добавлено для совместимости с some pytz operations if used

        result_df = spending_by_weekday(sample_transactions_df)

        expected_average_spending = {
            'Понедельник': 170.00,
            'Вторник': 235.00,
            'Среда': 97.50,
            'Четверг': 50.00,
            'Пятница': 100.00,
            'Суббота': 200.00,
            'Воскресенье': 300.00
        }

        ordered_weekdays = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
        assert list(result_df['День недели']) == ordered_weekdays

        result_dict = result_df.set_index('День недели')['Средние траты'].to_dict()
        for day in ordered_weekdays:
            expected_avg = expected_average_spending.get(day, 0.00)
            assert result_dict.get(day, 0.00) == pytest.approx(expected_avg, 0.01)


def test_spending_by_weekday_empty_transactions(empty_transactions_df, caplog):
    """
    Тестирует функцию spending_by_weekday с пустым DataFrame.
    """
    caplog.set_level(logging.WARNING, logger='src.reports')
    result_df = spending_by_weekday(empty_transactions_df)

    # Ожидается, что result_df не будет пустым, а будет содержать 7 дней с нулями
    assert result_df.empty is False
    assert list(result_df['День недели']) == ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота',
                                              'Воскресенье']
    assert all(result_df['Средние траты'] == 0.00)
    assert "Пустой DataFrame транзакций передан в spending_by_weekday." in caplog.text


def test_spending_by_weekday_no_spending_in_period(sample_transactions_df, caplog):
    """
    Тестирует функцию spending_by_weekday, когда нет трат в заданном 3-месячном периоде.
    """
    # Используем дату, когда нет трат в прошлом, например, 2020 год
    caplog.set_level(logging.INFO, logger='src.reports')
    result_df = spending_by_weekday(sample_transactions_df, "2020-01-01")

    assert result_df.empty is False  # Должен вернуть DataFrame со всеми 7 днями и 0.00
    assert list(result_df['День недели']) == ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота',
                                              'Воскресенье']
    assert all(result_df['Средние траты'] == 0.00)
    assert "Нет транзакций за последние 3 месяца до 2020-01-01." in caplog.text


def test_spending_by_weekday_no_negative_amounts_in_period(sample_transactions_df, caplog):
    """
    Тестирует функцию spending_by_weekday, когда в периоде нет отрицательных сумм (трат).
    """
    # Создаем DataFrame, где все суммы положительные
    positive_transactions_df = sample_transactions_df.copy()
    positive_transactions_df['Сумма операции'] = abs(positive_transactions_df['Сумма операции'])

    caplog.set_level(logging.INFO, logger='src.reports')
    # Используем дату, где есть данные
    result_df = spending_by_weekday(positive_transactions_df, "2024-05-10")

    assert result_df.empty is False  # Должен вернуть DataFrame со всеми 7 днями и 0.00
    assert list(result_df['День недели']) == ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота',
                                              'Воскресенье']
    assert all(result_df['Средние траты'] == 0.00)
    assert "Нет трат за последние 3 месяца." in caplog.text


def test_spending_by_weekday_invalid_date_format(sample_transactions_df, caplog):
    """
    Тестирует обработку некорректного формата даты.
    """
    caplog.set_level(logging.ERROR, logger='src.reports')
    # Мокаем datetime.now() для воспроизводимости теста, так как он будет использован при ошибке формата даты
    with patch('src.reports.datetime') as mock_dt:
        mock_dt.datetime.now.return_value = datetime.datetime(2024, 5, 10, 12, 0, 0)
        mock_dt.datetime.strptime = datetime.datetime.strptime
        mock_dt.timedelta = datetime.timedelta
        mock_dt.date = datetime.date
        mock_dt.MINYEAR = datetime.MINYEAR
        mock_dt.MAXYEAR = datetime.MAXYEAR
        mock_dt.timezone = datetime.timezone

        result_df = spending_by_weekday(sample_transactions_df, "invalid-date")

        assert "Некорректный формат даты 'invalid-date'. Используется текущая дата." in caplog.text
        # Проверяем, что возвращен DataFrame с ожидаемым результатом для текущей даты
        ordered_weekdays = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
        assert list(result_df['День недели']) == ordered_weekdays
        expected_average_spending = {  # Эти значения соответствуют test_spending_by_weekday_no_date
            'Понедельник': 170.00,
            'Вторник': 235.00,
            'Среда': 97.50,
            'Четверг': 50.00,
            'Пятница': 100.00,
            'Суббота': 200.00,
            'Воскресенье': 300.00
        }
        result_dict = result_df.set_index('День недели')['Средние траты'].to_dict()
        for day in ordered_weekdays:
            expected_avg = expected_average_spending.get(day, 0.00)
            assert result_dict.get(day, 0.00) == pytest.approx(expected_avg, 0.01)


# Тесты для декоратора log_and_save_report
@pytest.fixture(autouse=True)
def cleanup_reports_dir():
    """Фикстура для очистки папки reports перед каждым тестом."""
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reports")
    if os.path.exists(reports_dir):
        for f in os.listdir(reports_dir):
            file_path = os.path.join(reports_dir, f)
            if os.path.isfile(file_path):  # Убедимся, что это файл, а не поддиректория
                os.remove(file_path)
    yield
    # Очистка после тестов
    if os.path.exists(reports_dir):
        for f in os.listdir(reports_dir):
            file_path = os.path.join(reports_dir, f)
            if os.path.isfile(file_path):
                os.remove(file_path)
        # Удаляем папку только если она пуста.
        # Это может быть проблематично, если другие тесты или процессы создают файлы.
        # Поэтому оставлю удаление файлов, но без удаления самой папки для большей надежности в CI/CD.
        # if not os.listdir(reports_dir):
        #     os.rmdir(reports_dir)


def test_log_and_save_report_default_filename(sample_transactions_df, caplog):
    """
    Тестирует декоратор без указания имени файла (используется имя по умолчанию).
    """
    # Мокаем datetime.datetime.now() для предсказуемого имени файла
    with patch('src.reports.datetime') as mock_dt, \
            patch('builtins.open', mock_open()) as mock_file:
        mock_dt.datetime.now.return_value = datetime.datetime(2024, 5, 10, 12, 30, 0)
        mock_dt.datetime.strftime = datetime.datetime.strftime  # Важно, чтобы strftime работал как оригинал

        @log_and_save_report()
        def dummy_report_function(df: pd.DataFrame) -> pd.DataFrame:
            return df.head(1)  # Возвращаем часть DataFrame для простоты

        caplog.set_level(logging.INFO, logger='src.reports')

        report_result = dummy_report_function(sample_transactions_df)

        expected_filename_base = "dummy_report_function_report_20240510_123000.json"

        # Проверяем, что open был вызван с путем, заканчивающимся на ожидаемое имя файла
        mock_file.assert_called_once()
        actual_call_args = mock_file.call_args

        # Проверяем путь к файлу
        assert actual_call_args[0][0].endswith(expected_filename_base)
        # Проверяем режим открытия
        assert actual_call_args[0][1] == "w"
        # Проверяем именованные аргументы
        assert actual_call_args[1] == {"encoding": "utf-8"}

        # Проверяем, что информация о сохранении попала в лог
        assert f"Отчет 'dummy_report_function' сохранен в файл:" in caplog.text
        assert expected_filename_base in caplog.text  # Проверяем, что имя файла есть в сообщении


def test_log_and_save_report_custom_filename(sample_transactions_df, caplog):
    """
    Тестирует декоратор с указанием пользовательского имени файла.
    """
    custom_filename = "my_custom_report.json"
    with patch('builtins.open', mock_open()) as mock_file:
        @log_and_save_report(file_path=custom_filename)
        def custom_report_function(df: pd.DataFrame) -> pd.DataFrame:
            return df.head(1)

        caplog.set_level(logging.INFO, logger='src.reports')

        report_result = custom_report_function(sample_transactions_df)

        # Проверяем, что open был вызван с путем, заканчивающимся на пользовательское имя файла
        mock_file.assert_called_once()
        actual_call_args = mock_file.call_args
        assert actual_call_args[0][0].endswith(custom_filename)
        assert actual_call_args[0][1] == "w"
        assert actual_call_args[1] == {"encoding": "utf-8"}

        assert f"Отчет 'custom_report_function' сохранен в файл:" in caplog.text
        assert custom_filename in caplog.text


def test_log_and_save_report_returns_original_result(sample_transactions_df):
    """
    Тестирует, что декоратор возвращает оригинальный результат функции.
    """

    @log_and_save_report()
    def identity_function(df: pd.DataFrame) -> pd.DataFrame:
        return df

    original_df = sample_transactions_df.copy()
    result_df = identity_function(original_df)

    pd.testing.assert_frame_equal(result_df, original_df)


def test_log_and_save_report_non_dataframe_result(caplog):
    """
    Тестирует сохранение не DataFrame результатов (например, dict или str).
    """

    @log_and_save_report(file_path="dict_report.json")
    def dict_report_function() -> dict:
        return {"data": "test_dict", "value": 123}

    @log_and_save_report(file_path="string_report.txt")
    def string_report_function() -> str:
        return "This is a string report."

    with patch('builtins.open', mock_open()) as mock_file:
        caplog.set_level(logging.INFO, logger='src.reports')

        dict_result = dict_report_function()
        string_result = string_report_function()

        # Проверяем, что mock_file был вызван дважды
        assert mock_file.call_count == 2

        # Проверяем первый вызов (для словаря)
        dict_call_args = mock_file.call_args_list[0]
        assert dict_call_args[0][0].endswith("dict_report.json")
        assert dict_call_args[0][1] == "w"
        assert dict_call_args[1] == {"encoding": "utf-8"}
        mock_file().write.assert_any_call(json.dumps({"data": "test_dict", "value": 123}, indent=4, ensure_ascii=False))

        # Проверяем второй вызов (для строки)
        string_call_args = mock_file.call_args_list[1]
        assert string_call_args[0][0].endswith("string_report.txt")
        assert string_call_args[0][1] == "w"
        assert string_call_args[1] == {"encoding": "utf-8"}
        mock_file().write.assert_any_call("This is a string report.")

        assert "Отчет 'dict_report_function' сохранен в файл:" in caplog.text
        assert "Отчет 'string_report_function' сохранен в файл:" in caplog.text


def test_log_and_save_report_error_logging(sample_transactions_df, caplog):
    """
    Тестирует логирование ошибок при сохранении отчета.
    """
    with patch('builtins.open', side_effect=IOError("Permission denied")), \
            patch('src.reports.datetime') as mock_dt:
        mock_dt.datetime.now.return_value = datetime.datetime(2024, 5, 10, 12, 30, 0)
        mock_dt.datetime.strftime = datetime.datetime.strftime

        @log_and_save_report()
        def failing_report_function(df: pd.DataFrame) -> pd.DataFrame:
            return df.head(1)

        caplog.set_level(logging.ERROR, logger='src.reports')

        report_result = failing_report_function(sample_transactions_df)

        expected_filename_base = "failing_report_function_report_20240510_123000.json"

        # Проверяем, что в логе присутствует сообщение об ошибке с базовым именем файла
        assert f"Ошибка при сохранении отчета 'failing_report_function' в файл" in caplog.text
        assert expected_filename_base in caplog.text
        assert "Permission denied" in caplog.text
