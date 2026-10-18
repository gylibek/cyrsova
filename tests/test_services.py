from datetime import datetime

from src.services import (
    investment_bank,
    search_person_transfers,
    search_phone_numbers,
    simple_search,
)


def _tx(date, amount, category, description):
    return {
        "Дата операции": date,
        "Сумма операции": amount,
        "Категория": category,
        "Описание": description,
        "Статус": "OK",
    }


def test_investment_bank():
    txs = [
        _tx(datetime(2024, 5, 1), -1712, "Супермаркеты", "Покупка"),
        _tx(datetime(2024, 5, 2), -1234, "Фастфуд", "Обед"),
    ]
    # 1712 -> 1750 (38), 1234 -> 1250 (16) => 54
    assert investment_bank("2024-05", txs, 50) == 54.0


def test_simple_search_case_insensitive():
    txs = [_tx(datetime(2024, 5, 1), -100, "Супермаркеты", "МТС оплата")]
    result = simple_search(txs, "мтс")
    assert "МТС" in result


def test_phone_numbers_different_formats():
    txs = [
        _tx(datetime(2024, 5, 1), -100, "Связь", "Я МТС +7 921 11-22-33"),
        _tx(datetime(2024, 5, 2), -200, "Связь", "Тинькофф Мобайл 89000000000"),
    ]
    result = search_phone_numbers(txs)
    assert "+7 921 11-22-33" in result
    assert "89000000000" in result


def test_person_transfers():
    txs = [
        _tx(datetime(2024, 5, 1), -500, "Переводы", "Валерий А."),
        _tx(datetime(2024, 5, 2), -300, "Переводы", "Оплата услуг"),
    ]
    result = search_person_transfers(txs)
    assert "Валерий А." in result
    assert "Оплата услуг" not in result
