"""CLI приложение для тестирования API запросов."""

import json
import sys
from pathlib import Path
from colorama import init, Fore, Style
from http_client import get, post
from country_formatter import format_country_info
from currency import (
    get_converted_data,
    get_available_currencies,
    get_rates_for_base,
    validate_currency,
    print_currency_rates,
    get_cached_or_fresh_rates
)
from weather_app import (
    get_weather_by_city,
    get_weather_by_coordinates,
    get_cached_weather_by_city,
    get_cached_weather_by_coordinates
)
import requests

# Инициализация colorama для Windows совместимости
init(autoreset=True)


def print_json_pretty(data, status_code: int = 200):
    """
    Выводит JSON данные с красивым форматированием и цветами.
    
    Args:
        data: Словарь или список с данными для вывода
        status_code: HTTP статус код
    """
    # Цвет для статуса
    if 200 <= status_code < 300:
        status_color = Fore.GREEN
    elif 300 <= status_code < 400:
        status_color = Fore.YELLOW
    else:
        status_color = Fore.RED
    
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}Статус: {status_color}{status_code} {Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    # Форматированный JSON
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    
    # Раскраска JSON
    lines = json_str.split('\n')
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            print(f"{Fore.YELLOW}{key}:{Style.RESET_ALL}{value}")
        else:
            print(line)
    
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")


def get_request():
    """Выполняет GET запрос к указанному URL."""
    url = input(f"{Fore.GREEN}Введите URL для GET запроса: {Style.RESET_ALL}")
    if not url:
        print(f"{Fore.RED}URL не может быть пустым!{Style.RESET_ALL}")
        return
    
    try:
        response = get(url)
        try:
            data = response.json()
        except ValueError:
            print(f"{Fore.YELLOW}Ответ не является JSON. Текст ответа:{Style.RESET_ALL}")
            print(response.text)
            return
        print_json_pretty(data, response.status_code)
    except Exception as e:
        print(f"{Fore.RED}Ошибка: {e}{Style.RESET_ALL}")


def post_request():
    """Выполняет POST запрос к указанному URL."""
    url = input(f"{Fore.GREEN}Введите URL для POST запроса: {Style.RESET_ALL}")
    if not url:
        print(f"{Fore.RED}URL не может быть пустым!{Style.RESET_ALL}")
        return
    
    print(f"{Fore.YELLOW}Введите JSON данные (или нажмите Enter для пустого тела):{Style.RESET_ALL}")
    json_input = input()
    
    json_data = None
    if json_input:
        try:
            json_data = json.loads(json_input)
        except json.JSONDecodeError:
            print(f"{Fore.RED}Неверный формат JSON!{Style.RESET_ALL}")
            return
    
    try:
        response = post(url, json=json_data)
        try:
            data = response.json()
        except ValueError:
            print(f"{Fore.YELLOW}Ответ не является JSON. Текст ответа:{Style.RESET_ALL}")
            print(response.text)
            return
        print_json_pretty(data, response.status_code)
    except Exception as e:
        print(f"{Fore.RED}Ошибка: {e}{Style.RESET_ALL}")


def get_country_info():
    """Получает информацию о стране с restcountries.com."""
    country = input(f"{Fore.GREEN}Введите название страны: {Style.RESET_ALL}")
    if not country:
        print(f"{Fore.RED}Название страны не может быть пустым!{Style.RESET_ALL}")
        return
    
    url = f"https://restcountries.com/v3.1/name/{country}"
    
    try:
        response = get(url)
        try:
            data = response.json()
        except ValueError:
            print(f"{Fore.YELLOW}Ответ не является JSON. Текст ответа:{Style.RESET_ALL}")
            print(response.text)
            return
        
        # Используем специальный форматтер для страны
        format_country_info(data)
    except Exception as e:
        print(f"{Fore.RED}Ошибка: {e}{Style.RESET_ALL}")


def get_random_dog():
    """Получает ссылку на случайное изображение собаки."""
    url = "https://dog.ceo/api/breeds/image/random"
    
    try:
        response = get(url)
        try:
            data = response.json()
        except ValueError:
            print(f"{Fore.YELLOW}Ответ не является JSON. Текст ответа:{Style.RESET_ALL}")
            print(response.text)
            return
        print_json_pretty(data, response.status_code)
        
        # Дополнительно выводим ссылку на изображение
        if isinstance(data, dict) and 'message' in data:
            print(f"\n{Fore.MAGENTA}Ссылка на изображение: {Fore.CYAN}{data['message']}{Style.RESET_ALL}\n")
    except Exception as e:
        print(f"{Fore.RED}Ошибка: {e}{Style.RESET_ALL}")


def convert_currency():
    """Конвертирует валюту."""
    try:
        amount_str = input(f"{Fore.GREEN}Введите сумму: {Style.RESET_ALL}").strip()
        if not amount_str:
            print(f"{Fore.RED}Сумма не может быть пустой!{Style.RESET_ALL}")
            return
        
        try:
            amount = float(amount_str)
        except ValueError:
            print(f"{Fore.RED}Некорректное значение суммы!{Style.RESET_ALL}")
            return
        
        from_currency = input(f"{Fore.GREEN}Введите код исходной валюты (например, USD): {Style.RESET_ALL}").strip().upper()
        if not from_currency:
            print(f"{Fore.RED}Код валюты не может быть пустым!{Style.RESET_ALL}")
            return
        
        if not validate_currency(from_currency):
            print(f"{Fore.RED}Валюта {from_currency} не поддерживается!{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Доступные валюты: {', '.join(get_available_currencies())}{Style.RESET_ALL}")
            return
        
        to_currency = input(f"{Fore.GREEN}Введите код целевой валюты (например, RUB): {Style.RESET_ALL}").strip().upper()
        if not to_currency:
            print(f"{Fore.RED}Код валюты не может быть пустым!{Style.RESET_ALL}")
            return
        
        if not validate_currency(to_currency):
            print(f"{Fore.RED}Валюта {to_currency} не поддерживается!{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Доступные валюты: {', '.join(get_available_currencies())}{Style.RESET_ALL}")
            return
        
        result = get_converted_data(amount, from_currency, to_currency)
        
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.CYAN}{' '*20}РЕЗУЛЬТАТ КОНВЕРТАЦИИ")
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")
        print(f"{Fore.YELLOW}{amount:.2f} {from_currency} = {Fore.GREEN}{result:.4f} {to_currency}{Style.RESET_ALL}\n")
        
    except ValueError as e:
        print(f"{Fore.RED}Ошибка: {e}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Неожиданная ошибка: {e}{Style.RESET_ALL}")


def show_available_currencies():
    """Показывает список доступных валют."""
    currencies = get_available_currencies()
    
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.CYAN}{' '*25}ДОСТУПНЫЕ ВАЛЮТЫ")
    print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")
    
    for i, currency_code in enumerate(currencies, 1):
        print(f"{Fore.YELLOW}{i}.{Style.RESET_ALL} {Fore.GREEN}{currency_code}{Style.RESET_ALL}")
    
    print()


def show_currency_rates():
    """Показывает курсы валют относительно выбранной базовой валюты."""
    base = input(f"{Fore.GREEN}Введите код базовой валюты (например, USD): {Style.RESET_ALL}").strip().upper()
    
    if not base:
        print(f"{Fore.RED}Код валюты не может быть пустым!{Style.RESET_ALL}")
        return
    
    if not validate_currency(base):
        print(f"{Fore.RED}Валюта {base} не поддерживается!{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Доступные валюты: {', '.join(get_available_currencies())}{Style.RESET_ALL}")
        return
    
    try:
        rates = get_rates_for_base(base)
        print_currency_rates(base, rates)
    except ValueError as e:
        print(f"{Fore.RED}Ошибка: {e}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Неожиданная ошибка: {e}{Style.RESET_ALL}")


def update_currency_rates():
    """Обновляет курсы валют через API."""
    base = input(f"{Fore.GREEN}Введите код базовой валюты для обновления (например, USD): {Style.RESET_ALL}").strip().upper()
    
    if not base:
        print(f"{Fore.RED}Код валюты не может быть пустым!{Style.RESET_ALL}")
        return
    
    if not validate_currency(base):
        print(f"{Fore.RED}Валюта {base} не поддерживается!{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Доступные валюты: {', '.join(get_available_currencies())}{Style.RESET_ALL}")
        return
    
    try:
        print(f"{Fore.YELLOW}Обновление курсов валют...{Style.RESET_ALL}")
        rates_data = get_cached_or_fresh_rates(base, force_update=True)
        rates = rates_data.get('rates', {})
        
        print(f"{Fore.GREEN}Курсы успешно обновлены!{Style.RESET_ALL}\n")
        print_json_pretty(rates_data, 200)
        
    except ValueError as e:
        print(f"{Fore.RED}Ошибка: {e}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Неожиданная ошибка: {e}{Style.RESET_ALL}")


def show_currency_menu():
    """Отображает меню валютного калькулятора."""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}       ВАЛЮТНЫЙ КАЛЬКУЛЯТОР")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}1{Style.RESET_ALL} - Конвертировать валюту")
    print(f"{Fore.YELLOW}2{Style.RESET_ALL} - Показать доступные валюты")
    print(f"{Fore.YELLOW}3{Style.RESET_ALL} - Показать курсы")
    print(f"{Fore.YELLOW}4{Style.RESET_ALL} - Обновить курсы валют")
    print(f"{Fore.YELLOW}0{Style.RESET_ALL} - Выход в основное меню")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")


def currency_calculator_menu():
    """Главное меню валютного калькулятора."""
    while True:
        show_currency_menu()
        choice = input(f"{Fore.GREEN}Выберите действие: {Style.RESET_ALL}").strip()
        
        if choice == '0':
            break
        elif choice == '1':
            convert_currency()
        elif choice == '2':
            show_available_currencies()
        elif choice == '3':
            show_currency_rates()
        elif choice == '4':
            update_currency_rates()
        else:
            print(f"{Fore.RED}Неверный выбор! Пожалуйста, выберите число от 0 до 4.{Style.RESET_ALL}")
        
        input(f"\n{Fore.YELLOW}Нажмите Enter для продолжения...{Style.RESET_ALL}")


def get_weather_by_city_name():
    """Получает погоду по названию города."""
    city = input(f"{Fore.GREEN}Введите название города: {Style.RESET_ALL}").strip()
    if not city:
        print(f"{Fore.RED}Название города не может быть пустым!{Style.RESET_ALL}")
        return
    
    try:
        weather_data = get_weather_by_city(city)
        display_weather_by_city(weather_data, city)
    except requests.RequestException as e:
        # Сетевая ошибка после всех попыток retry
        print(f"{Fore.RED}Ошибка: {e}{Style.RESET_ALL}")
        # Предлагаем использовать кэш
        print(f"{Fore.YELLOW}Попробовать использовать данные из кэша? (y/n): {Style.RESET_ALL}", end="")
        use_cache = input().strip().lower()
        if use_cache == 'y':
            cached_data = get_cached_weather_by_city(city)
            if cached_data:
                display_weather_by_city(cached_data, city)
            else:
                print(f"{Fore.RED}Данных для города '{city}' в кэше не найдено.{Style.RESET_ALL}")
    except ValueError as e:
        print(f"{Fore.RED}Ошибка: {e}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Неожиданная ошибка: {e}{Style.RESET_ALL}")


def get_weather_by_coords():
    """Получает погоду по координатам."""
    try:
        lat_str = input(f"{Fore.GREEN}Введите широту: {Style.RESET_ALL}").strip()
        if not lat_str:
            print(f"{Fore.RED}Широта не может быть пустой!{Style.RESET_ALL}")
            return
        
        lon_str = input(f"{Fore.GREEN}Введите долготу: {Style.RESET_ALL}").strip()
        if not lon_str:
            print(f"{Fore.RED}Долгота не может быть пустой!{Style.RESET_ALL}")
            return
        
        try:
            lat = float(lat_str)
            lon = float(lon_str)
        except ValueError:
            print(f"{Fore.RED}Некорректные значения координат!{Style.RESET_ALL}")
            return
        
        weather_data = get_weather_by_coordinates(lat, lon)
        display_weather_by_coordinates(weather_data, lat, lon)
    except requests.RequestException as e:
        # Сетевая ошибка после всех попыток retry
        print(f"{Fore.RED}Ошибка: {e}{Style.RESET_ALL}")
        # Предлагаем использовать кэш
        print(f"{Fore.YELLOW}Попробовать использовать данные из кэша? (y/n): {Style.RESET_ALL}", end="")
        use_cache = input().strip().lower()
        if use_cache == 'y':
            cached_data = get_cached_weather_by_coordinates(lat, lon)
            if cached_data:
                display_weather_by_coordinates(cached_data, lat, lon)
            else:
                print(f"{Fore.RED}Данных для координат (широта={lat}, долгота={lon}) в кэше не найдено.{Style.RESET_ALL}")
    except ValueError as e:
        print(f"{Fore.RED}Ошибка: {e}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Неожиданная ошибка: {e}{Style.RESET_ALL}")


def display_weather_by_city(weather_data: dict, city: str):
    """Отображает погоду по названию города."""
    temp = weather_data.get("main", {}).get("temp", "N/A")
    weather_desc = "N/A"
    
    weather_list = weather_data.get("weather", [])
    if weather_list and len(weather_list) > 0:
        weather_desc = weather_list[0].get("description", "N/A")
    
    coord = weather_data.get("coord", {})
    lat = coord.get("lat", "N/A")
    lon = coord.get("lon", "N/A")
    country_code = weather_data.get("sys", {}).get("country", "N/A")
    
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.CYAN}{' '*20}ПОГОДА В ГОРОДЕ")
    print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")
    print(f"{Fore.GREEN}Погода в городе {city}: {Fore.YELLOW}{temp}°C, {weather_desc}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Координаты города {city} (код страны: {country_code}){Style.RESET_ALL}")
    print(f"{Fore.YELLOW}широта = {lat}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}долгота = {lon}{Style.RESET_ALL}\n")


def display_weather_by_coordinates(weather_data: dict, lat: float, lon: float):
    """Отображает погоду по координатам."""
    country_code = weather_data.get("sys", {}).get("country", "N/A")
    city_name = weather_data.get("name", "N/A")
    
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.CYAN}{' '*20}ПОГОДА ПО КООРДИНАТАМ")
    print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")
    print(f"{Fore.YELLOW}широта = {lat}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}долгота = {lon}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Код страны: {country_code}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Название населенного пункта: {city_name}{Style.RESET_ALL}\n")


def print_weather_basic_info(weather_data: dict):
    """Выводит базовую информацию о погоде."""
    temp = weather_data.get("main", {}).get("temp", "N/A")
    weather_desc = "N/A"
    
    weather_list = weather_data.get("weather", [])
    if weather_list and len(weather_list) > 0:
        weather_desc = weather_list[0].get("description", "N/A")
    
    print(f"{Fore.GREEN}Температура: {temp}°C, {weather_desc}{Style.RESET_ALL}")


def show_weather_menu():
    """Отображает меню погоды."""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}       ПОГОДА")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}1{Style.RESET_ALL} - Погода по названию города")
    print(f"{Fore.YELLOW}2{Style.RESET_ALL} - Погода по координатам")
    print(f"{Fore.YELLOW}0{Style.RESET_ALL} - Выход в основное меню")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")


def weather_menu():
    """Главное меню погоды."""
    while True:
        show_weather_menu()
        choice = input(f"{Fore.GREEN}Выберите действие: {Style.RESET_ALL}").strip()
        
        if choice == '0':
            break
        elif choice == '1':
            get_weather_by_city_name()
        elif choice == '2':
            get_weather_by_coords()
        else:
            print(f"{Fore.RED}Неверный выбор! Пожалуйста, выберите число от 0 до 2.{Style.RESET_ALL}")
        
        input(f"\n{Fore.YELLOW}Нажмите Enter для продолжения...{Style.RESET_ALL}")


def show_menu():
    """Отображает главное меню."""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}          CLI ТЕСТОВЫЙ МОДУЛЬ ДЛЯ API ЗАПРОСОВ")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}1{Style.RESET_ALL} - GET по URL")
    print(f"{Fore.YELLOW}2{Style.RESET_ALL} - Страна")
    print(f"{Fore.YELLOW}3{Style.RESET_ALL} - Случайная собака")
    print(f"{Fore.YELLOW}4{Style.RESET_ALL} - Валютный калькулятор")
    print(f"{Fore.YELLOW}5{Style.RESET_ALL} - Узнать погоду")
    print(f"{Fore.YELLOW}0{Style.RESET_ALL} - Выход")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")


def main():
    """Главная функция приложения."""
    while True:
        show_menu()
        choice = input(f"{Fore.GREEN}Выберите действие: {Style.RESET_ALL}").strip()
        
        if choice == '0':
            print(f"{Fore.CYAN}До свидания!{Style.RESET_ALL}")
            sys.exit(0)
        elif choice == '1':
            get_request()
        elif choice == '2':
            get_country_info()
        elif choice == '3':
            get_random_dog()
        elif choice == '4':
            currency_calculator_menu()
        elif choice == '5':
            weather_menu()
        else:
            print(f"{Fore.RED}Неверный выбор! Пожалуйста, выберите число от 0 до 5.{Style.RESET_ALL}")
        
        input(f"\n{Fore.YELLOW}Нажмите Enter для продолжения...{Style.RESET_ALL}")


if __name__ == "__main__":
    main()

