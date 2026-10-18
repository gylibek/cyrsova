from datetime import datetime

from src.views import events_page_view, main_page_view


def _make_tx(date, amount, category, description, card="1234", status="OK"):
    return {
        "Дата операции": date,
        "Сумма операции": amount,
        "Категория": category,
        "Описание": description,
        "Номер карты": card,
        "Статус": status,
        "Сумма платежа": amount,
    }


def test_greeting_intervals():
    tx = []
    assert main_page_view("2024-05-20 07:00:00", tx)["greeting"] == "Доброе утро"
    assert main_page_view("2024-05-20 13:00:00", tx)["greeting"] == "Добрый день"
    assert main_page_view("2024-05-20 19:00:00", tx)["greeting"] == "Добрый вечер"
    assert main_page_view("2024-05-20 02:00:00", tx)["greeting"] == "Доброй ночи"


def test_main_page_cards_and_top():
    txs = [
        _make_tx(datetime(2024, 5, 1), -1500, "Супермаркеты", "Пятёрочка", card="1111"),
        _make_tx(datetime(2024, 5, 10), -500, "Фастфуд", "Вкусно и точка", card="1111"),
        _make_tx(datetime(2024, 5, 15), 10000, "Пополнение", "Зарплата", card="1111"),
        _make_tx(datetime(2024, 5, 5), -2000, "Топливо", "АЗС", card="2222"),
    ]
    result = main_page_view("2024-05-20 14:00:00", txs)
    assert len(result["cards"]) == 2
    assert result["cards"][0]["last_digits"] == "1111"
    assert result["cards"][0]["total_spent"] == 2000.0
    assert result["cards"][0]["cashback"] == 20.0
    # топ-5 содержит только расходные OK-транзакции
    assert len(result["top_transactions"]) <= 5


def test_events_top7_and_rest():
    txs = [
        _make_tx(datetime(2024, 5, i), -100 * i, f"Категория_{i}", f"Описание_{i}")
        for i in range(1, 10)
    ]
    txs.append(_make_tx(datetime(2024, 5, 15), -500, "Наличные", "Снятие"))
    txs.append(_make_tx(datetime(2024, 5, 16), -200, "Переводы", "Перевод другу"))
    result = events_page_view("2024-05-20 14:00:00", txs, "M")
    assert len(result["expenses"]["main"]) == 8  # 7 категорий + Остальное
    assert any(item["category"] == "Остальное" for item in result["expenses"]["main"])
    assert len(result["expenses"]["transfers_and_cash"]) == 2
