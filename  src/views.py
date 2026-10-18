# src/views.py
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .utils import (
    fetch_currency_rates,
    fetch_stock_prices,
    get_greeting,
    load_user_settings,
)

logger = logging.getLogger(__name__)


def _parse_datetime(dt_str: str) -> datetime:
    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")


def _period_start_of_month(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _period_for_events(dt: datetime, interval: Optional[str] = None) -> tuple[datetime, datetime]:
    """Возвращает (start, end) для страницы «События»."""
    if interval == "W":
        start = dt - timedelta(days=dt.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    elif interval == "Y":
        start = dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif interval == "ALL":
        return datetime.min, dt
    else:  # M по умолчанию
        start = _period_start_of_month(dt)
    return start, dt


# ========== ГЛАВНАЯ СТРАНИЦА ==========
def main_page_view(dt_str: str, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Главная страница.
    dt_str: 'YYYY-MM-DD HH:MM:SS'
    transactions: список словарей из Excel
    """
    dt = _parse_datetime(dt_str)
    start = _period_start_of_month(dt)

    # фильтруем транзакции за период
    period_tx = [
        tx for tx in transactions
        if start <= tx["Дата операции"] <= dt
    ]

    # приветствие
    greeting = get_greeting(dt)

    # по картам
    cards_map: dict[str, dict[str, float]] = defaultdict(lambda: {"expenses": 0.0, "cashback": 0.0})
    for tx in period_tx:
        if tx.get("Статус") != "OK":
            continue
        amount = float(tx.get("Сумма операции") or 0)
        if amount >= 0:
            continue  # только расходы
        card = str(tx.get("Номер карты", "")).strip()
        if not card:
            continue
        cards_map[card]["expenses"] += abs(amount)
        # кешбэк 1 ₽ на каждые 100 ₽
        cards_map[card]["cashback"] += abs(amount) / 100

    cards = [
        {
            "last_digits": card[-4:],
            "total_spent": round(info["expenses"], 2),
            "cashback": round(info["cashback"], 2),
        }
        for card, info in cards_map.items()
    ]

    # топ-5 транзакций по сумме платежа
    top_transactions = sorted(
        [tx for tx in period_tx if tx.get("Статус") == "OK"],
        key=lambda x: abs(float(x.get("Сумма платежа") or 0)),
        reverse=True,
    )[:5]

    top_5 = [
        {
            "date": tx["Дата операции"].strftime("%d.%m.%Y"),
            "amount": float(tx.get("Сумма платежа") or 0),
            "category": tx.get("Категория", ""),
            "description": tx.get("Описание", ""),
        }
        for tx in top_transactions
    ]

    # валюты и акции
    settings = load_user_settings()
    currency_rates = fetch_currency_rates(settings.get("user_currencies", []))
    stock_prices = fetch_stock_prices(settings.get("user_stocks", []))

    return {
        "greeting": greeting,
        "cards": cards,
        "top_transactions": top_5,
        "currency_rates": currency_rates,
        "stock_prices": stock_prices,
    }


# ========== СТРАНИЦА «СОБЫТИЯ» ==========
def events_page_view(
    dt_str: str,
    transactions: List[Dict[str, Any]],
    interval: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Страница «События».
    interval: 'W', 'M', 'Y', 'ALL' или None (M по умолчанию).
    """
    dt = _parse_datetime(dt_str)
    start, end = _period_for_events(dt, interval)

    period_tx = [
        tx for tx in transactions
        if start <= tx["Дата операции"] <= end and tx.get("Статус") == "OK"
    ]

    # ---------- РАСХОДЫ ----------
    expenses_total = 0.0
    expenses_by_category: dict[str, float] = defaultdict(float)
    transfers_cash: dict[str, float] = defaultdict(float)

    for tx in period_tx:
        amount = float(tx.get("Сумма операции") or 0)
        if amount >= 0:
            continue
        amount_abs = abs(amount)
        category = tx.get("Категория", "Без категории")
        if category in ("Наличные", "Переводы"):
            transfers_cash[category] += amount_abs
        else:
            expenses_by_category[category] += amount_abs
        expenses_total += amount_abs

    # топ-7 категорий + «Остальное»
    sorted_expenses = sorted(expenses_by_category.items(), key=lambda x: x[1], reverse=True)
    main_expenses = sorted_expenses[:7]
    rest_amount = sum(v for _, v in sorted_expenses[7:])
    if rest_amount > 0:
        main_expenses.append(("Остальное", rest_amount))

    expenses_main = [
        {"category": cat, "amount": round(amount)}
        for cat, amount in main_expenses
    ]
    transfers_and_cash = [
        {"category": cat, "amount": round(amount)}
        for cat, amount in sorted(transfers_cash.items(), key=lambda x: x[1], reverse=True)
    ]

    # ---------- ПОСТУПЛЕНИЯ ----------
    income_total = 0.0
    income_by_category: dict[str, float] = defaultdict(float)
    for tx in period_tx:
        amount = float(tx.get("Сумма операции") or 0)
        if amount <= 0:
            continue
        income_total += amount
        income_by_category[tx.get("Категория", "Без категории")] += amount

    income_main = [
        {"category": cat, "amount": round(amount)}
        for cat, amount in sorted(income_by_category.items(), key=lambda x: x[1], reverse=True)
    ]

    # ---------- ВАЛЮТЫ И АКЦИИ ----------
    settings = load_user_settings()
    currency_rates = fetch_currency_rates(settings.get("user_currencies", []))
    stock_prices = fetch_stock_prices(settings.get("user_stocks", []))

    return {
        "expenses": {
            "total_amount": round(expenses_total),
            "main": expenses_main,
            "transfers_and_cash": transfers_and_cash,
        },
        "income": {
            "total_amount": round(income_total),
            "main": income_main,
        },
        "currency_rates": currency_rates,
        "stock_prices": stock_prices,
    }
