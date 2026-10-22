# src/main.py
import json
from pathlib import Path

from src.reports import spending_by_category, spending_by_weekday, spending_by_workday
from src.services import (
    cashback_categories,
    investment_bank,
    search_person_transfers,
    search_phone_numbers,
    simple_search,
)
from src.utils import read_transactions_dataframe, read_transactions_from_excel
from src.views import events_page_view, main_page_view

BASE_DIR = Path(__file__).resolve().parent.parent
EXCEL_PATH = BASE_DIR / "data" / "operations.xlsx"


def demo() -> None:
    # данные
    transactions_list = read_transactions_from_excel(EXCEL_PATH)
    transactions_df = read_transactions_dataframe(EXCEL_PATH)

    # главная страница
    print("=== ГЛАВНАЯ ===")
    print(json.dumps(
        main_page_view("2024-05-20 14:30:00", transactions_list),
        ensure_ascii=False,
        indent=2,
    ))

    # события
    print("\n=== СОБЫТИЯ (M) ===")
    print(json.dumps(
        events_page_view("2024-05-20 14:30:00", transactions_list, "M"),
        ensure_ascii=False,
        indent=2,
    ))

    # сервисы
    print("\n=== КЕШБЭК ПО КАТЕГОРИЯМ ===")
    print(cashback_categories(transactions_list, 2024, 5))

    print("\n=== ИНВЕСТКОПИЛКА ===")
    print(investment_bank("2024-05", transactions_list, 50))

    print("\n=== ПОИСК «МТС» ===")
    print(simple_search(transactions_list, "МТС"))

    print("\n=== ТЕЛЕФОНЫ ===")
    print(search_phone_numbers(transactions_list))

    print("\n=== ПЕРЕВОДЫ ФИЗЛИЦАМ ===")
    print(search_person_transfers(transactions_list))

    # отчёты
    print("\n=== ТРАТЫ ПО КАТЕГОРИИ «Супермаркеты» ===")
    print(spending_by_category(transactions_df, "Супермаркеты", "2024-05-20"))

    print("\n=== ТРАТЫ ПО ДНЯМ НЕДЕЛИ ===")
    print(spending_by_weekday(transactions_df, "2024-05-20"))

    print("\n=== ТРАТЫ В РАБОЧИЙ/ВЫХОДНОЙ ===")
    print(spending_by_workday(transactions_df, "2024-05-20"))


if __name__ == "__main__":
    demo()
