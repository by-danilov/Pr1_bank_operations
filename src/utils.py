import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)  # Уровень логирования можно изменить на INFO для отладки
handler = logging.StreamHandler()
formatter = logging.Formatter("%(levelname)s\t%(name)s:%(filename)s:%(lineno)d %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def get_greeting(current_datetime: datetime) -> str:
    """
    Возвращает приветствие в зависимости от времени суток.
    """
    hour = current_datetime.hour
    if 5 <= hour < 12:
        return "Доброе утро"
    elif 12 <= hour < 17:
        return "Добрый день"
    elif 17 <= hour < 22:
        return "Добрый вечер"
    else:
        return "Доброй ночи"


def load_user_settings(file_path: str) -> Dict[str, Any]:
    """
    Загружает пользовательские настройки из JSON-файла.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
        return settings
    except FileNotFoundError:
        logger.error(f"Файл настроек не найден: {file_path}")
        return {}
    except json.JSONDecodeError:
        logger.error(f"Ошибка декодирования JSON в файле настроек: {file_path}")
        return {}
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при загрузке настроек: {e}")
        return {}


def filter_by_date(data: list[dict], date_str: str) -> list[dict]:
    """
    Фильтрует список словарей по дате.
    Дата должна быть в формате "YYYY-MM-DD HH:MM:SS".
    """
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        filtered_data = []
        for item in data:
            if "date" in item:
                try:
                    item_date = datetime.strptime(item["date"], "%Y-%m-%d %H:%M:%S")
                    if item_date <= target_date:
                        filtered_data.append(item)
                except ValueError:
                    logger.warning(f"Некорректный формат даты в данных: {item.get('date')}")
            else:
                logger.warning(f"Элемент данных не содержит ключ 'date': {item}")
        return filtered_data
    except ValueError as e:
        logger.error(f"Ошибка формата даты при фильтрации (date_str): {e}")
        return []
    except TypeError as e:
        logger.error(f"Ошибка типа данных при фильтрации по дате: {e}")
        return []
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при фильтрации по дате: {e}")
        return []
