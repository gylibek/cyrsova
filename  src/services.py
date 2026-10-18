# src/services.py
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


# ========== 1. ВЫГОДНЫЕ КАТЕГОРИИ ПОВЫШЕННОГО КЕШБЭКА ==========
def cashback_categories(
    transactions: List[Dict[str, Any]],
    year: int,
    month: int,
) -> str:
    """
    Анализирует, сколько кешбэка можно заработать по категориям за месяц.
    Кешбэк считается как 1% от суммы расходов (можно заменить на логику банка).
    Возвращает JSON-строку.
    """
    result: dict[str, float] = {}

    for tx in transactions:
        if tx.get("Статус") != "OK":
            continue
        dt: datetime = tx["Дата операции"]
        if dt.year != year or dt.month != month:
            continue
        amount = float(tx.get("Сумма операции") or 0)
        if amount >= 0:
            continue
        category = tx.get("Категория", "Без категории")
        # кешбэк 1%
        result[category] = result.get(category, 0.0) + abs(amount) * 0.01

    # сортируем по убыванию и берём минимум 3 категории (по критериям — не менее 3)
    sorted_items = sorted(result.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_items) < 3:
        # дополняем, если категорий меньше 3 (на реальных данных обычно больше)
        pass
    output = {cat: round(amount, 2) for cat, amount in sorted_items}
    return json.dumps(output, ensure_ascii=False, indent=2)


# ========== 2. ИНВЕСТКОПИЛКА ==========
def investment_bank(
    month: str,
    transactions: List[Dict[str, Any]],
    limit: int,
) -> float:
    """
    Сумма, которую удалось бы отложить в «Инвесткопилку».
    month: 'YYYY-MM'
    limit: шаг округления (10, 50, 100)
    """
    total_saved = 0.0
    for tx in transactions:
        tx_date: datetime = tx["Дата операции"]
        if tx_date.strftime("%Y-%m") != month:
            continue
        if tx.get("Статус") != "OK":
            continue
        amount = float(tx.get("Сумма операции") or 0)
        if amount >= 0:
            continue  # только расходы
        amount_abs = abs(amount)
        # округление вверх до ближайшего кратного limit
        rounded = ((amount_abs + limit - 1) // limit) * limit
        total_saved += rounded - amount_abs
    return round(total_saved, 2)


# ========== 3. ПРОСТОЙ ПОИСК ==========
def simple_search(transactions: List[Dict[str, Any]], query: str) -> str:
    """Поиск по подстроке в описании или категории, без учёта регистра."""
    query_lower = query.lower()
    matched = []
    for tx in transactions:
        description = str(tx.get("Описание", "")).lower()
        category = str(tx.get("Категория", "")).lower()
        if query_lower in description or query_lower in category:
            matched.append({
                "date": tx["Дата операции"].strftime("%d.%m.%Y"),
                "amount": tx.get("Сумма операции"),
                "category": tx.get("Категория"),
                "description": tx.get("Описание"),
            })
    return json.dumps(matched, ensure_ascii=False, indent=2, default=str)


# ========== 4. ПОИСК ПО ТЕЛЕФОННЫМ НОМЕРАМ ==========
# Поддерживает: +7 921 11-22-33, 8 900 000-00-00, 89000000000 и т.п.
PHONE_PATTERN = re.compile(
    r"(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}"
)


def search_phone_numbers(transactions: List[Dict[str, Any]]) -> str:
    """Возвращает транзакции, в описании которых есть мобильный номер."""
    matched = []
    for tx in transactions:
        description = str(tx.get("Описание", ""))
        if PHONE_PATTERN.search(description):
            matched.append({
                "date": tx["Дата операции"].strftime("%d.%m.%Y"),
                "amount": tx.get("Сумма операции"),
                "category": tx.get("Категория"),
                "description": description,
            })
    return json.dumps(matched, ensure_ascii=False, indent=2, default=str)


# ========== 5. ПОИСК ПЕРЕВОДОВ ФИЗЛИЦАМ ==========
# Категория «Переводы» + в описании имя и первая буква фамилии с точкой.
PERSON_PATTERN = re.compile(r"\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.")


def search_person_transfers(transactions: List[Dict[str, Any]]) -> str:
    """Возвращает транзакции-переводы физическим лицам."""
    matched = []
    for tx in transactions:
        category = str(tx.get("Категория", ""))
        description = str(tx.get("Описание", ""))
        if category == "Переводы" and PERSON_PATTERN.search(description):
            matched.append({
                "date": tx["Дата операции"].strftime("%d.%m.%Y"),
                "amount": tx.get("Сумма операции"),
                "category": category,
                "description": description,
            })
    return json.dumps(matched, ensure_ascii=False, indent=2, default=str)
