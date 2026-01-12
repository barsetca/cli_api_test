"""Модуль для работы с валютным калькулятором."""

from typing import Dict, Any, Optional
from datetime import datetime
from http_client import get
from storage import (
    read_from_file, 
    save_to_file, 
    is_file_today,
    get_file_data_date
)
from colorama import Fore, Style


FAVORITE_CURRENCIES = ["USD", "EUR", "GBP", "RUB", "CNY"]
CURRENCY_FILE = "currency_rate.json"


def get_currency_rates(base: str) -> Dict[str, Any]:
    """
    Получает курсы валют для базовой валюты с API.
    
    Args:
        base: Код базовой валюты (например, USD)
        
    Returns:
        Словарь с данными о курсах валют
        
    Raises:
        ValueError: Если базовая валюта не из списка FAVORITE_CURRENCIES
        requests.RequestException: При ошибке HTTP запроса
    """
    if base not in FAVORITE_CURRENCIES:
        raise ValueError(f"Валюта {base} не поддерживается. Доступные валюты: {', '.join(FAVORITE_CURRENCIES)}")
    
    url = f"https://open.er-api.com/v6/latest/{base}"
    
    try:
        response = get(url)
        
        if response.status_code != 200:
            raise ValueError(f"Ошибка API: получили статус код {response.status_code}")
        
        data = response.json()
        
        # Добавляем дату получения данных и базовую валюту
        result = {
            'base': base,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'rates': data.get('rates', {}),
            'timestamp': data.get('time_last_update_unix', 0)
        }
        
        return result
    except Exception as e:
        raise ValueError(f"Ошибка при получении курсов валют: {e}")


def get_cached_or_fresh_rates(base: str, force_update: bool = False) -> Dict[str, Any]:
    """
    Получает курсы валют из кэша (если актуальны) или делает новый запрос.
    
    Args:
        base: Код базовой валюты
        force_update: Принудительное обновление данных
        
    Returns:
        Словарь с данными о курсах валют
    """
    # Принудительное обновление
    if force_update:
        rates_data = get_currency_rates(base)
        save_to_file(rates_data, CURRENCY_FILE)
        return rates_data
    
    # Проверяем существование файла
    cached_data = read_from_file(CURRENCY_FILE)
    
    if cached_data is None:
        # Файла нет - делаем запрос
        rates_data = get_currency_rates(base)
        save_to_file(rates_data, CURRENCY_FILE)
        return rates_data
    
    # Проверяем дату данных в файле
    file_date = get_file_data_date(CURRENCY_FILE)
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Проверяем базовую валюту в кэше
    cached_base = cached_data.get('base')
    
    # Если дата совпадает и базовая валюта та же - используем кэш
    if file_date == today and cached_base == base and not force_update:
        return cached_data
    
    # Обновляем данные
    rates_data = get_currency_rates(base)
    save_to_file(rates_data, CURRENCY_FILE)
    return rates_data


def get_converted_data(amount: float, from_currency: str, to_currency: str) -> float:
    """
    Конвертирует сумму из одной валюты в другую.
    
    Args:
        amount: Сумма для конвертации
        from_currency: Код исходной валюты
        to_currency: Код целевой валюты
        
    Returns:
        Конвертированная сумма с точностью до 4 знаков после запятой
        
    Raises:
        ValueError: Если валюта не поддерживается или отсутствует курс
    """
    # Валидация валют
    if from_currency not in FAVORITE_CURRENCIES:
        raise ValueError(f"Исходная валюта {from_currency} не поддерживается. Доступные: {', '.join(FAVORITE_CURRENCIES)}")
    
    if to_currency not in FAVORITE_CURRENCIES:
        raise ValueError(f"Целевая валюта {to_currency} не поддерживается. Доступные: {', '.join(FAVORITE_CURRENCIES)}")
    
    if from_currency == to_currency:
        return round(amount, 4)
    
    # Получаем актуальные курсы
    rates_data = get_cached_or_fresh_rates(from_currency)
    rates = rates_data.get('rates', {})
    
    if to_currency not in rates:
        raise ValueError(f"Курс для валюты {to_currency} не найден")
    
    # Конвертируем
    rate = rates[to_currency]
    converted_amount = amount * rate
    
    return round(converted_amount, 4)


def get_available_currencies() -> list:
    """
    Возвращает список доступных валют.
    
    Returns:
        Список кодов доступных валют
    """
    return FAVORITE_CURRENCIES.copy()


def get_rates_for_base(base: str) -> Dict[str, float]:
    """
    Получает курсы всех избранных валют относительно базовой.
    
    Args:
        base: Код базовой валюты
        
    Returns:
        Словарь с курсами валют (только из FAVORITE_CURRENCIES)
    """
    rates_data = get_cached_or_fresh_rates(base)
    all_rates = rates_data.get('rates', {})
    
    # Фильтруем только избранные валюты
    favorite_rates = {
        currency: all_rates[currency] 
        for currency in FAVORITE_CURRENCIES 
        if currency != base and currency in all_rates
    }
    
    return favorite_rates


def validate_currency(currency: str) -> bool:
    """
    Проверяет, является ли код валюты валидным.
    
    Args:
        currency: Код валюты для проверки
        
    Returns:
        True, если валюта валидна, иначе False
    """
    return currency.upper() in FAVORITE_CURRENCIES


def print_currency_rates(base: str, rates: Dict[str, float]) -> None:
    """
    Выводит курсы валют в красиво отформатированном виде.
    
    Args:
        base: Базовая валюта
        rates: Словарь с курсами
    """
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.CYAN}{' '*25}КУРСЫ ВАЛЮТ")
    print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")
    print(f"{Fore.YELLOW}Базовая валюта: {Fore.GREEN}{base}{Style.RESET_ALL}\n")
    print(f"{Fore.MAGENTA}{'─'*70}{Style.RESET_ALL}")
    
    if not rates:
        print(f"{Fore.YELLOW}Курсы не найдены{Style.RESET_ALL}")
    else:
        for currency in sorted(rates.keys()):
            rate = rates[currency]
            print(f"{Fore.YELLOW}{currency:5} → {Fore.CYAN}{rate:>15.4f}{Style.RESET_ALL}")
    
    print(f"{Fore.MAGENTA}{'─'*70}{Style.RESET_ALL}\n")

