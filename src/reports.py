import datetime
import json
import logging
import os
from functools import wraps
from typing import Any, Callable, Optional

import pandas as pd

# Настройка логирования для модуля reports
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Установим INFO для разработки
# Удалим существующие обработчики, чтобы избежать дублирования, если их несколько
# (это предотвращает многократный вывод одних и тех же сообщений)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(levelname)s\t%(name)s:%(filename)s:%(lineno)d %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def log_and_save_report(file_path: Optional[str] = None) -> Callable[..., Callable[..., Any]]:
    """
    Декоратор для функций-отчетов, который записывает результат в файл.

    Args:
        file_path (Optional[str]): Путь к файлу для сохранения отчета.
                                    Если None, используется имя по умолчанию.

    Returns:
        Callable: Декорирующая функция.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = func(*args, **kwargs)  # Выполняем оригинальную функцию отчета

            # Определяем путь к папке reports относительно текущего файла (reports.py)
            reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reports")

            # Убеждаемся, что папка reports существует. Если нет, создаем ее.
            os.makedirs(reports_dir, exist_ok=True)

            # Формируем имя файла по умолчанию.
            default_file_name_base = f"{func.__name__}_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            default_file_name_full_path = os.path.join(reports_dir, default_file_name_base)

            # Если file_path был передан в декоратор, используем его.
            # Если это относительный путь, преобразуем его в полный путь относительно reports_dir.
            # Иначе используем автоматически сгенерированный полный путь.
            output_file: str
            if file_path:
                if os.path.isabs(file_path):
                    output_file = file_path
                else:
                    output_file = os.path.join(reports_dir, file_path)
            else:
                output_file = default_file_name_full_path

            try:
                if isinstance(result, pd.DataFrame):
                    result_to_save = result.to_json(orient="records", indent=4, force_ascii=False)
                elif isinstance(result, (dict, list)):
                    result_to_save = json.dumps(result, indent=4, ensure_ascii=False)
                else:
                    result_to_save = str(result)

                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(result_to_save)
                logger.info(f"Отчет '{func.__name__}' сохранен в файл: {output_file}")
            except Exception as e:
                logger.error(f"Ошибка при сохранении отчета '{func.__name__}' в файл {output_file}: {e}")

            return result  # Всегда возвращаем оригинальный результат функции

        return wrapper

    # Этот блок позволяет декоратору работать как с аргументами, так и без них.
    # Если log_and_save_report вызывается без скобок (@log_and_save_report),
    # то file_path будет сама декорируемая функция.
    if callable(file_path):
        # Если file_path - это функция, значит декоратор был вызван без аргументов
        return decorator(file_path)
    else:
        # Если file_path - это не функция, значит декоратор был вызван с аргументами
        return decorator


@log_and_save_report()
def spending_by_weekday(transactions: pd.DataFrame, date: Optional[str] = None) -> pd.DataFrame:
    """
    Рассчитывает средние траты в каждый из дней недели за последние три месяца
    от переданной даты.

    Args:
        transactions (pd.DataFrame): DataFrame с транзакциями, содержащий колонки
                                     'Дата операции' и 'Сумма операции'.
        date (Optional[str]): Дата в формате 'YYYY-MM-DD' для отсчета трех месяцев.
                              Если None, используется текущая дата.

    Returns:
        pd.DataFrame: DataFrame со средними тратами по дням недели.
                      Столбцы: 'День недели', 'Средние траты'.
    """
    # Создаем DataFrame со всеми днями недели и значениями по умолчанию
    # Это гарантирует, что все дни недели присутствуют в результате, даже если по ним нет трат
    weekday_map = {
        0: "Понедельник",
        1: "Вторник",
        2: "Среда",
        3: "Четверг",
        4: "Пятница",
        5: "Суббота",
        6: "Воскресенье",
    }
    all_weekdays_df_template = pd.DataFrame(
        {
            "День недели_num": list(weekday_map.keys()),  # Числовой день недели
            "День недели": list(weekday_map.values()),  # Название дня недели
        }
    )

    if transactions.empty:
        logger.warning("Пустой DataFrame транзакций передан в spending_by_weekday.")
        # Возвращаем DataFrame со всеми днями недели, но с нулевыми тратами
        return all_weekdays_df_template.drop(columns=["День недели_num"]).assign(**{"Средние траты": 0.00})

    # Преобразование 'Дата операции' в datetime
    transactions["Дата операции"] = pd.to_datetime(transactions["Дата операции"], errors="coerce", dayfirst=True)
    transactions.dropna(subset=["Дата операции"], inplace=True)

    current_date_dt: datetime.datetime
    if date:
        try:
            current_date_dt = pd.to_datetime(date).to_pydatetime()
        except ValueError:
            logger.error(f"Некорректный формат даты '{date}'. Используется текущая дата.")
            current_date_dt = datetime.datetime.now()
    else:
        current_date_dt = datetime.datetime.now()

    # Убедимся, что current_date является pandas Timestamp для удобства сравнения
    current_date = pd.to_datetime(current_date_dt)

    # Определяем начало периода (3 месяца назад от текущей даты)
    three_months_ago = current_date - pd.DateOffset(months=3)

    # Фильтруем транзакции за последние три месяца
    filtered_transactions = transactions[
        (transactions["Дата операции"] >= three_months_ago) & (transactions["Дата операции"] <= current_date)
    ].copy()

    if filtered_transactions.empty:
        logger.info(f"Нет транзакций за последние 3 месяца до {current_date.strftime('%Y-%m-%d')}.")
        # Возвращаем DataFrame со всеми днями недели, но с нулевыми тратами
        return all_weekdays_df_template.drop(columns=["День недели_num"]).assign(**{"Средние траты": 0.00})

    # Извлекаем день недели (0=понедельник, 6=воскресенье)
    filtered_transactions["День недели"] = filtered_transactions["Дата операции"].dt.dayofweek

    # Фильтруем только траты (отрицательные суммы)
    spending_transactions = filtered_transactions[filtered_transactions["Сумма операции"] < 0].copy()

    if spending_transactions.empty:
        logger.info("Нет трат за последние 3 месяца.")
        # Если нет трат, возвращаем DataFrame со всеми днями недели и нулевыми тратами
        return all_weekdays_df_template.drop(columns=["День недели_num"]).assign(**{"Средние траты": 0.00})

    # Группируем по числовому дню недели и считаем среднее значение (используя abs() для положительных трат)
    daily_avg_spending_raw = (
        spending_transactions.groupby("День недели")["Сумма операции"].apply(lambda x: abs(x).mean()).reset_index()
    )
    daily_avg_spending_raw.rename(columns={"Сумма операции": "Средние траты"}, inplace=True)

    # Объединяем с DataFrame всех дней недели, чтобы гарантировать наличие всех дней.
    # Используем числовой день недели для объединения.
    # Сначала daily_avg_spending_raw['День недели'] нужно преобразовать в названия
    daily_avg_spending_raw["День недели_name"] = daily_avg_spending_raw["День недели"].map(weekday_map)

    # Объединяем с all_weekdays_df_template по названию дня недели
    daily_avg_spending = pd.merge(
        all_weekdays_df_template,
        daily_avg_spending_raw[["День недели_name", "Средние траты"]],
        left_on="День недели",
        right_on="День недели_name",
        how="left",
    )
    # Удаляем вспомогательный столбец
    daily_avg_spending.drop(columns=["День недели_num", "День недели_name"], inplace=True)

    # Заполняем NaN (для дней без трат) нулями
    daily_avg_spending["Средние траты"] = daily_avg_spending["Средние траты"].fillna(0.00)

    # Упорядочиваем по дням недели (используя категориальный тип для сохранения порядка)
    ordered_weekdays = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    daily_avg_spending["День недели"] = pd.Categorical(
        daily_avg_spending["День недели"], categories=ordered_weekdays, ordered=True
    )
    daily_avg_spending = daily_avg_spending.sort_values("День недели").reset_index(drop=True)

    # Округляем средние траты до двух знаков после запятой
    daily_avg_spending["Средние траты"] = daily_avg_spending["Средние траты"].round(2)

    logger.info("Отчет 'Траты по дням недели' успешно сформирован.")

    return daily_avg_spending
