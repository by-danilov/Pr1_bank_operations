import datetime
import logging
from typing import Any, Dict, List

# Настройка логирования для модуля services
logger = logging.getLogger(__name__)
# ИЗМЕНИТЕ ЭТУ СТРОКУ:
logger.setLevel(logging.WARNING)  # Измените на INFO или WARNING, чтобы видеть сообщения
# ниже уровня ERROR (например, WARNING, которые
# генерируются при пропуске транзакций)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(levelname)s\t%(name)s:%(filename)s:%(lineno)d %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def investment_bank(month: str, transactions: List[Dict[str, Any]], limit: int) -> float:
    """
    Рассчитывает сумму, которую удалось бы отложить в «Инвесткопилку»
    за указанный месяц на основе округления трат.

    Args:
        month (str): Месяц для расчета в формате 'YYYY-MM'.
        transactions (List[Dict[str, Any]]): Список словарей с информацией о транзакциях.
                                            Ожидаются поля 'Дата операции' (строка YYYY-MM-DD)
                                            и 'Сумма операции' (число).
        limit (int): Порог округления (10, 50 или 100).

    Returns:
        float: Общая сумма, отложенная в «Инвесткопилку».
    """
    if limit not in [10, 50, 100]:
        logger.error(f"Недопустимый порог округления: {limit}. Допустимые значения: 10, 50, 100.")
        return 0.0

    total_invested_amount = 0.0
    target_year, target_month = map(int, month.split("-"))

    for transaction in transactions:
        try:
            op_date_str = transaction.get("Дата операции")
            op_amount = transaction.get("Сумма операции")

            if not op_date_str or not isinstance(op_amount, (int, float)):
                logger.warning(f"Пропущена транзакция из-за отсутствия/некорректных данных: {transaction}")
                continue

            # Преобразование даты операции в объект datetime
            op_date = datetime.datetime.strptime(op_date_str, "%Y-%m-%d").date()

            # Проверка, что транзакция относится к указанному месяцу
            if op_date.year == target_year and op_date.month == target_month:
                # Нас интересуют только траты (отрицательные суммы)
                if op_amount < 0:
                    abs_amount = abs(op_amount)
                    # Рассчитываем сумму, которая была бы округлена
                    # Если сумма 1712, лимит 50: (1712 // 50) * 50 = 1700
                    # Следующий порог: 1700 + 50 = 1750
                    # Разница: 1750 - 1712 = 38

                    # Если сумма равна порогу округления (например, 50, 100),
                    # то округление до 50/100, разница 0
                    if abs_amount % limit == 0:
                        rounded_amount = abs_amount
                    else:
                        rounded_amount = (abs_amount // limit + 1) * limit

                    invested_amount = rounded_amount - abs_amount
                    total_invested_amount += invested_amount
                    logger.debug(
                        f"Транзакция: {op_amount}, Округлено до: {rounded_amount}, Инвесткопилка: {invested_amount}"
                    )

        except ValueError as ve:
            logger.error(f"Ошибка парсинга даты или суммы в транзакции {transaction}: {ve}")
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при обработке транзакции {transaction}: {e}")

    return round(total_invested_amount, 2)
