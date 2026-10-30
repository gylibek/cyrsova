# src/utils.py
"""
- загрузка пользовательских настроек из user_settings.json;
- чтение Excel-выгрузки Т-Банка (поддерживаются .xls и .xlsx);
- запросы к API курсов валют и цен на акции (с обработкой ошибок);
- приветствие по времени суток.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# ---------- пути ----------
BASE_DIR: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = BASE_DIR / "data"
SETTINGS_PATH: Path = BASE_DIR / "user_settings.json"


# ============================================================
# ПОЛЬЗОВАТЕЛЬСКИЕ НАСТРОЙКИ
# ============================================================
def load_user_settings(path: Path = SETTINGS_PATH) -> Dict[str, List[str]]:
    """
    Читает user_settings.json.

    Ожидаемый формат:
    {
      "user_currencies": ["USD", "EUR"],
      "user_stocks": ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"]
    }
    """
    if not Path(path).exists():
        logger.warning("Файл настроек не найден: %s. Используются значения по умолчанию.", path)
        return {"user_currencies": ["USD", "EUR"], "user_stocks": ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"]}

    try:
        with open(path, "r", encoding="utf-8") as f:
            settings = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Не удалось прочитать %s: %s", path, exc)
        return {"user_currencies": [], "user_stocks": []}

    settings.setdefault("user_currencies", [])
    settings.setdefault("user_stocks", [])
    return settings


# ============================================================
# ЧТЕНИЕ EXCEL С ТРАНЗАКЦИЯМИ
# ============================================================
def _find_operations_file() -> Path:
    """
    Ищет файл с операциями в data/ по базовому имени operations
    с любым поддерживаемым расширением (.xlsx, .xls).

    Raises:
        FileNotFoundError: если файл не найден.
    """
    for ext in (".xlsx", ".xls"):
        candidate = DATA_DIR / f"operations{ext}"
        if candidate.exists():
            logger.info("Найден файл операций: %s", candidate)
            return candidate
    raise FileNotFoundError(
        f"Не найден файл operations.xlsx или operations.xls в {DATA_DIR}. "
        f"Положите файл выгрузки Т-Банка в папку data/."
    )


def read_transactions_dataframe(file_path: str | Path | None = None) -> pd.DataFrame:
    """
    Читает Excel с транзакциями и возвращает DataFrame.

    Параметры:
        file_path: путь к файлу. Если не передан — файл ищется в data/
                   по имени operations.xlsx / operations.xls.

    Возвращает DataFrame с колонкой "Дата операции" в типе datetime
    и без строк с невалидной датой.
    """
    path = Path(file_path) if file_path else _find_operations_file()
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")

    df = pd.read_excel(path)

    if "Дата операции" not in df.columns:
        raise ValueError(
            f"В файле {path} отсутствует колонка «Дата операции». "
            f"Доступные колонки: {list(df.columns)}"
        )

    df["Дата операции"] = pd.to_datetime(
        df["Дата операции"], errors="coerce", dayfirst=True
    )
    df = df.dropna(subset=["Дата операции"]).reset_index(drop=True)
    return df


def read_transactions_from_excel(file_path: str | Path | None = None) -> List[Dict[str, Any]]:
    """
    Читает Excel с транзакциями и возвращает список словарей
    (удобно для сервисов и функций-представлений, работающих с list[dict]).

    Если file_path не передан — используется файл data/operations.xlsx|.xls.
    """
    return read_transactions_dataframe(file_path).to_dict(orient="records")


# ============================================================
# API ВАЛЮТ (ЦБ РФ, без ключа)
# ============================================================
CURRENCY_API_URL = "https://www.cbr-xml-daily.ru/daily_json.js"


def fetch_currency_rates(currencies: List[str]) -> List[Dict[str, Any]]:
    """
    Возвращает курсы валют к рублю из API ЦБ РФ.

    Формат ответа:
        [{"currency": "USD", "rate": 73.21}, ...]

    При ошибке сети/парсинга логирует предупреждение и возвращает
    пустой список — это допустимо по требованиям (ошибки API обработаны).
    """
    result: List[Dict[str, Any]] = []
    try:
        response = requests.get(CURRENCY_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        valute = data.get("Valute", {})
        for code in currencies:
            if code in valute:
                rate = float(valute[code]["Value"])
                if rate > 0:
                    result.append({"currency": code, "rate": round(rate, 2)})
            else:
                logger.warning("Валюта %s отсутствует в ответе API", code)
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.warning("Не удалось получить курсы валют: %s", exc)
    return result


# ============================================================
# API АКЦИЙ (Yahoo Finance, без ключа)
# ============================================================
STOCK_API_URL_TEMPLATE = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"


def fetch_stock_prices(tickers: List[str]) -> List[Dict[str, Any]]:
    """
    Возвращает цены акций с публичного endpoint Yahoo Finance.

    Формат ответа:
        [{"stock": "AAPL", "price": 150.12}, ...]

    Для каждого тикера ошибка обрабатывается независимо: если по одному
    тикеру API не ответил — остальные всё равно попадут в результат.
    """
    result: List[Dict[str, Any]] = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; BankAnalysis/1.0)"}
    for ticker in tickers:
        url = STOCK_API_URL_TEMPLATE.format(ticker=ticker)
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            price = float(data["chart"]["result"][0]["meta"]["regularMarketPrice"])
            if price > 0:
                result.append({"stock": ticker, "price": round(price, 2)})
            else:
                logger.warning("Получена некорректная цена для %s: %s", ticker, price)
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
            logger.warning("Не удалось получить цену %s: %s", ticker, exc)
    return result


# ============================================================
# ПРИВЕТСТВИЕ
# ============================================================
def get_greeting(dt: datetime) -> str:
    """
    Возвращает приветствие по времени суток:
        06:00–11:59 — «Доброе утро»
        12:00–17:59 — «Добрый день»
        18:00–22:59 — «Добрый вечер»
        23:00–05:59 — «Доброй ночи»
    """
    hour = dt.hour
    if 6 <= hour < 12:
        return "Доброе утро"
    if 12 <= hour < 18:
        return "Добрый день"
    if 18 <= hour < 23:
        return "Добрый вечер"
    return "Доброй ночи"
