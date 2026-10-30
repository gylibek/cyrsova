# src/reports.py
import functools
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

logger = logging.getLogger(__name__)
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


# ========== ДЕКОРАТОР ==========
def report_decorator(filename: Optional[str] = None) -> Callable:
    """
    Декоратор для функций-отчётов.
    Без параметра — сохраняет в reports/<имя_функции>_report.csv.
    С параметром — сохраняет в reports/<filename>.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if isinstance(result, pd.DataFrame):
                out_path = REPORTS_DIR / (
                    filename if filename else f"{func.__name__}_report.csv"
                )
                result.to_csv(out_path, index=False, encoding="utf-8-sig")
                logger.info("Отчёт сохранён: %s", out_path)
            return result

        return wrapper

    return decorator


# ========== ВСПОМОГАТЕЛЬНЫЕ ==========
def _parse_optional_date(date: Optional[str]) -> datetime:
    if date is None:
        return datetime.now()
    return datetime.strptime(date, "%Y-%m-%d")


def _filter_last_3_months(
    transactions: pd.DataFrame,
    date: Optional[str],
) -> pd.DataFrame:
    dt = _parse_optional_date(date)
    start = dt - timedelta(days=90)

    df = transactions.copy()
    df["Дата операции"] = pd.to_datetime(df["Дата операции"], errors="coerce")
    mask = (
        (df["Дата операции"] >= start)
        & (df["Дата операции"] <= dt)
        & (df["Сумма операции"] < 0)
        & (df["Статус"] == "OK")
    )
    filtered = df.loc[mask].copy()
    filtered["Сумма операции"] = filtered["Сумма операции"].abs()
    return filtered


# ========== 1. ТРАТЫ ПО КАТЕГОРИИ ==========
@report_decorator()
def spending_by_category(
    transactions: pd.DataFrame,
    category: str,
    date: Optional[str] = None,
) -> pd.DataFrame:
    """Траты по заданной категории за последние 3 месяца от date."""
    filtered = _filter_last_3_months(transactions, date)
    filtered = filtered[filtered["Категория"] == category]
    return filtered[["Дата операции", "Сумма операции", "Категория", "Описание"]]


# ========== 2. ТРАТЫ ПО ДНЯМ НЕДЕЛИ ==========
@report_decorator("spending_by_weekday.csv")
def spending_by_weekday(
    transactions: pd.DataFrame,
    date: Optional[str] = None,
) -> pd.DataFrame:
    """Средние траты по дням недели за последние 3 месяца."""
    filtered = _filter_last_3_months(transactions, date)
    filtered["weekday"] = filtered["Дата операции"].dt.day_name()

    return (
        filtered.groupby("weekday")["Сумма операции"]
        .mean()
        .round(2)
        .reset_index()
        .rename(columns={"Сумма операции": "average_spending"})
    )


# ========== 3. ТРАТЫ В РАБОЧИЙ/ВЫХОДНОЙ ДЕНЬ ==========
@report_decorator()
def spending_by_workday(
    transactions: pd.DataFrame,
    date: Optional[str] = None,
) -> pd.DataFrame:
    """Средние траты в рабочий и выходной день за последние 3 месяца."""
    filtered = _filter_last_3_months(transactions, date)

    filtered["day_type"] = filtered["Дата операции"].dt.weekday.apply(
        lambda x: "рабочий" if x < 5 else "выходной"
    )

    return (
        filtered.groupby("day_type")["Сумма операции"]
        .mean()
        .round(2)
        .reset_index()
        .rename(columns={"Сумма операции": "average_spending"})
    )
