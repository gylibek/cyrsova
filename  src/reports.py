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
    Без параметра — сохраняет в файл по умолчанию.
    С параметром — сохраняет в указанный файл.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            # если результат — DataFrame, сохраняем в CSV
            if isinstance(result, pd.DataFrame):
                if filename:
                    out_path = REPORTS_DIR / filename
                else:
                    out_path = REPORTS_DIR / f"{func.__name__}_report.csv"
                result.to_csv(out_path, index=False, encoding="utf-8-sig")
                logger.info("Отчёт сохранён: %s", out_path)
            return result

        return wrapper

    return decorator


# ========== ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ==========
def _parse_optional_date(date: Optional[str]) -> datetime:
    if date is None:
        return datetime.now()
    return datetime.strptime(date, "%Y-%m-%d")


# ========== 1. ТРАТЫ ПО КАТЕГОРИИ ==========
@report_decorator()
def spending_by_category(
    transactions: pd.DataFrame,
    category: str,
    date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Траты по заданной категории за последние 3 месяца от date.
    Если date не передана — текущая дата.
    """
    dt = _parse_optional_date(date)
    start = dt - timedelta(days=90)

    df = transactions.copy()
    df["Дата операции"] = pd.to_datetime(df["Дата операции"], errors="coerce")
    mask = (
        (df["Дата операции"] >= start)
        & (df["Дата операции"] <= dt)
        & (df["Категория"] == category)
        & (df["Сумма операции"] < 0)
        & (df["Статус"] == "OK")
    )
    filtered = df.loc[mask].copy()
    filtered["Сумма операции"] = filtered["Сумма операции"].abs()
    return filtered[["Дата операции", "Сумма операции", "Категория", "Описание"]]


# ========== 2. ТРАТЫ ПО ДНЯМ НЕДЕЛИ ==========
@report_decorator("spending_by_weekday.csv")
def spending_by_weekday(
    transactions: pd.DataFrame,
    date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Средние траты по дням недели за последние 3 месяца.
    """
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
    filtered["weekday"] = filtered["Дата операции"].dt.day_name()

    # средние траты по дням недели
    result = (
        filtered.groupby("weekday")["Сумма операции"]
        .mean()
        .round(2)
        .reset_index()
        .rename(columns={"Сумма операции": "average_spending"})
    )
    return result


# ========== 3. ТРАТЫ В РАБОЧИЙ/ВЫХОДНОЙ ДЕНЬ ==========
@report_decorator()
def spending_by_workday(
    transactions: pd.DataFrame,
    date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Средние траты в рабочий и выходной день за последние 3 месяца.
    """
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

    # 0–4 — будни, 5–6 — выходные
    filtered["day_type"] = filtered["Дата операции"].dt.weekday.apply(
        lambda x: "рабочий" if x < 5 else "выходной"
    )

    result = (
        filtered.groupby("day_type")["Сумма операции"]
        .mean()
        .round(2)
        .reset_index()
        .rename(columns={"Сумма операции": "average_spending"})
    )
    return result
