import datetime
import json
import os
import pandas as pd
from dotenv import load_dotenv
from src.reports import spending_by_weekday
from src.services import investment_bank
from src.views import main_page, read_transactions


def run_all_functionalities():
    """
    Основная функция для демонстрации работы всех реализованных функциональностей.
    """
    print("--- Запуск демонстрации функционала проекта ---")

    # 1. Загрузка переменных окружения из .env
    load_dotenv()
    print("Переменные окружения загружены.")

    # --- СТРОКИ ДЛЯ ПРОВЕРКИ ---
    # loaded_currency_key = os.getenv("CURRENCY_API_KEY")
    # loaded_alpha_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    # print(f"CURRENCY_API_KEY из .env: {'***' + loaded_currency_key[-4:] if loaded_currency_key else 'НЕ ЗАГРУЖЕН'}")
    # print(f"ALPHA_VANTAGE_API_KEY из .env: {'***' + loaded_alpha_key[-4:] if loaded_alpha_key else 'НЕ ЗАГРУЖЕН'}")
    # ----------------------------------------

    # 2. Загрузка транзакций
    transactions_path = os.path.join(os.path.dirname(__file__), "..", "data", "operations.xlsx")
    print(f"Попытка загрузить транзакции из: {transactions_path}")
    try:
        transactions_df = read_transactions(transactions_path)
        if transactions_df is not None and not transactions_df.empty:
            print(f"Загружено {len(transactions_df)} транзакций.")
        else:
            print("Транзакции не загружены или DataFrame пуст. Возможно, файл не существует или пуст.")
            transactions_df = pd.DataFrame()
    except Exception as e:
        print(f"Ошибка при загрузке транзакций: {e}")
        transactions_df = pd.DataFrame()

    # 3. Демонстрация главной страницы (views.py)
    print("\n--- Демонстрация главной страницы ---")
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    main_page_data_json = main_page(current_time)
    print("Данные для главной страницы (JSON):")
    try:
        main_page_data_dict = json.loads(main_page_data_json)
        print(json.dumps(main_page_data_dict, indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print(main_page_data_json)

    # 4. Демонстрация отчета "Траты по дням недели" (reports.py)
    print("\n--- Демонстрация отчета 'Траты по дням недели' ---")
    if not transactions_df.empty:
        # Используем дату, которая есть в вашем operations.xlsx, чтобы увидеть результат
        # Например, если данные за 2021-2022 год, используйте '2022-01-01'
        # weekday_spending_report = spending_by_weekday(transactions_df, current_time.split(" ")[0])
        # <--- ИЗМЕНЕНО: используйте подходящую дату, например:
        weekday_spending_report = spending_by_weekday(transactions_df, "2018-02-15")

        print("Отчет 'Траты по дням недели' сформирован. Подробности в консоли и в файле отчета.")
        print("Первые несколько строк отчета:")
        print(weekday_spending_report.head())
    else:
        print("Невозможно сформировать отчет: нет данных транзакций.")

    # 5. Демонстрация инвесткопилки (services.py)
    print("\n--- Демонстрация инвесткопилки ---")
    if not transactions_df.empty:
        # Для демонстрации выберем, например, январь 2022 года
        demo_month = "2022-01"
        demo_limit = 50  # Можно 10, 50 или 100

        # Преобразуем DataFrame в список словарей для investment_bank
        # Убедитесь, что 'Дата операции' отформатирована как 'YYYY-MM-DD'
        # И 'Сумма операции' корректна
        transactions_for_investbank = transactions_df[["Дата операции", "Сумма операции"]].copy()
        transactions_for_investbank["Дата операции"] = transactions_for_investbank["Дата операции"].dt.strftime(
            "%Y-%m-%d"
        )

        # Фильтруем транзакции для инвесткопилки по месяцу, если это необходимо для демонстрации
        # Однако investment_bank сам фильтрует по месяцу, так что можно передать все.
        # Просто убедитесь, что в файле operations.xlsx есть данные за demo_month

        invested_total = investment_bank(demo_month, transactions_for_investbank.to_dict("records"), demo_limit)
        print(f"Общая сумма, отложенная в инвесткопилку за {demo_month} (лимит {demo_limit}): {invested_total} руб.")
    else:
        print("Невозможно продемонстрировать инвесткопилку: нет данных транзакций.")

    print("\n--- Демонстрация завершена ---")


if __name__ == "__main__":
    run_all_functionalities()
