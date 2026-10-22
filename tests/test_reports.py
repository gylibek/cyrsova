import pandas as pd
import pytest
from src.reports import (spending_by_category, spending_by_weekday,
                         spending_by_workday)


@pytest.fixture
def df():
    return pd.DataFrame(
        [
            {
                "Дата операции": pd.Timestamp("2024-05-01"),
                "Сумма операции": -1000,
                "Категория": "Супермаркеты",
                "Описание": "Покупка",
                "Статус": "OK",
            },
            {
                "Дата операции": pd.Timestamp("2024-05-04"),  # суббота
                "Сумма операции": -2000,
                "Категория": "Развлечения",
                "Описание": "Кино",
                "Статус": "OK",
            },
            {
                "Дата операции": pd.Timestamp("2024-02-01"),
                "Сумма операции": -500,
                "Категория": "Супермаркеты",
                "Описание": "Старая",
                "Статус": "OK",
            },
        ]
    )


def test_spending_by_category(df):
    result = spending_by_category(df, "Супермаркеты", "2024-05-20")
    assert len(result) == 1
    assert result.iloc[0]["Сумма операции"] == 1000


def test_spending_by_weekday(df):
    result = spending_by_weekday(df, "2024-05-20")
    assert not result.empty
    assert "weekday" in result.columns
