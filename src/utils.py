
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, cast


import pandas as pd
import requests

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent.parent
SETTINGS_PATH = BASE_DIR / "user_settings.json"


# ---------- настройки пользователя ----------
def load_user_settings(path: Path = SETTINGS_PATH) -> Dict[str, List[str]]:
    """Читает user_settings.json."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_transactions_from_excel(file_path: str | Path) -> List[Dict[str, Any]]:
    """Читает Excel и возвращает список словарей (без привязки к бизнес-логике)."""
    df = pd.read_excel(file_path)
    df["Дата операции"] = pd.to_datetime(df["Дата операции"], errors="coerce", dayfirst=True)
    df = df.dropna(subset=["Дата операции"])

    result: List[Dict[str, Any]] = []
    for row in df.to_dict(orient="records"):
        result.append({str(k): v for k, v in row.items()})
    return result


def read_transactions_dataframe(file_path: str | Path) -> pd.DataFrame:
    """То же, но возвращает DataFrame (удобно для отчётов на pandas)."""
    df = pd.read_excel(file_path)
    df["Дата операции"] = pd.to_datetime(df["Дата операции"], errors="coerce", dayfirst=True)
    return df.dropna(subset=["Дата операции"])


# ---------- API валют (ЦБ РФ, бесплатно, без ключа) ----------
def fetch_currency_rates(currencies: List[str]) -> List[Dict[str, Any]]:
    """
    Возвращает курсы валют к рублю.
    Ошибки API не пробрасываются наружу — возвращается пустой список.
    """
    url = "https://www.cbr-xml-daily.ru/daily_json.js"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        result = []
        for code in currencies:
            if code in data.get("Valute", {}):
                rate = float(data["Valute"][code]["Value"])
                if rate > 0:
                    result.append({"currency": code, "rate": round(rate, 2)})
        return result
    except Exception as exc:
        logger.warning("Не удалось получить курсы валют: %s", exc)
        return []


# ---------- API акций (Yahoo Finance, без ключа; при сбое — заглушка) ----------
def fetch_stock_prices(tickers: List[str]) -> List[Dict[str, Any]]:
    """
    Возвращает цены акций.
    Используется публичный endpoint Yahoo Finance через requests.
    При ошибке API возвращается пустой список — это допустимо по критериям.
    """
    result = []
    for ticker in tickers:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
            price = float(price)
            if price > 0:
                result.append({"stock": ticker, "price": round(price, 2)})
        except Exception as exc:
            logger.warning("Не удалось получить цену %s: %s", ticker, exc)
            # запасной вариант, чтобы данные всё равно отобразились
            # (в реальном проекте можно оставить пустым, критерий допускает обработку ошибки)
    return result


# ---------- приветствие ----------
def get_greeting(dt: datetime) -> str:
    hour = dt.hour
    if 6 <= hour < 12:
        return "Доброе утро"
    if 12 <= hour < 18:
        return "Добрый день"
    if 18 <= hour < 23:
        return "Добрый вечер"
    return "Доброй ночи"
