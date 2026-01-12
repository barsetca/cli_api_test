"""Модуль для форматирования и вывода информации о стране."""

from colorama import Fore, Style
from typing import Dict, Any, List, Optional


def format_country_info(country_data: List[Dict[str, Any]]) -> None:
    """
    Форматирует и выводит информацию о стране с красивым оформлением.
    
    Args:
        country_data: Список словарей с данными о стране от restcountries API
    """
    if not country_data or len(country_data) == 0:
        print(f"{Fore.RED}Данные о стране не найдены!{Style.RESET_ALL}")
        return
    
    # Берем первую страну из списка
    country = country_data[0]
    
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.CYAN}{' '*20}ИНФОРМАЦИЯ О СТРАНЕ")
    print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")
    
    # Основная информация
    _print_section_header("ОСНОВНАЯ ИНФОРМАЦИЯ")
    name = country.get('name', {})
    if name:
        print(f"{Fore.YELLOW}Название:{Style.RESET_ALL}")
        if 'common' in name:
            print(f"  {Fore.GREEN}Обычное:{Style.RESET_ALL} {name['common']}")
        if 'official' in name:
            print(f"  {Fore.GREEN}Официальное:{Style.RESET_ALL} {name['official']}")
    
    # Столица
    capital = country.get('capital', [])
    if capital:
        print(f"{Fore.YELLOW}Столица:{Style.RESET_ALL} {Fore.CYAN}{', '.join(capital)}{Style.RESET_ALL}")
    
    # Коды стран
    codes = []
    if 'cca2' in country:
        codes.append(f"CCA2: {country['cca2']}")
    if 'cca3' in country:
        codes.append(f"CCA3: {country['cca3']}")
    if codes:
        print(f"{Fore.YELLOW}Коды страны:{Style.RESET_ALL} {Fore.CYAN}{', '.join(codes)}{Style.RESET_ALL}")
    
    # Флаг (эмодзи)
    if 'flag' in country:
        print(f"{Fore.YELLOW}Флаг:{Style.RESET_ALL} {country['flag']}")
    
    print()
    
    # Географическая информация
    _print_section_header("ГЕОГРАФИЯ")
    
    region = country.get('region')
    if region:
        print(f"{Fore.YELLOW}Регион:{Style.RESET_ALL} {Fore.CYAN}{region}{Style.RESET_ALL}")
    
    subregion = country.get('subregion')
    if subregion:
        print(f"{Fore.YELLOW}Субрегион:{Style.RESET_ALL} {Fore.CYAN}{subregion}{Style.RESET_ALL}")
    
    continents = country.get('continents', [])
    if continents:
        print(f"{Fore.YELLOW}Континент(ы):{Style.RESET_ALL} {Fore.CYAN}{', '.join(continents)}{Style.RESET_ALL}")
    
    area = country.get('area')
    if area:
        print(f"{Fore.YELLOW}Площадь:{Style.RESET_ALL} {Fore.CYAN}{area:,.0f} км²{Style.RESET_ALL}")
    
    latlng = country.get('latlng', [])
    if len(latlng) == 2:
        print(f"{Fore.YELLOW}Координаты:{Style.RESET_ALL} {Fore.CYAN}{latlng[0]}°N, {latlng[1]}°E{Style.RESET_ALL}")
    
    landlocked = country.get('landlocked', False)
    print(f"{Fore.YELLOW}Выход к морю:{Style.RESET_ALL} {Fore.CYAN}{'Нет' if landlocked else 'Да'}{Style.RESET_ALL}")
    
    borders = country.get('borders', [])
    if borders:
        print(f"{Fore.YELLOW}Граничит с:{Style.RESET_ALL} {Fore.CYAN}{', '.join(borders)}{Style.RESET_ALL}")
    
    print()
    
    # Демографическая информация
    _print_section_header("ДЕМОГРАФИЯ")
    
    population = country.get('population')
    if population:
        print(f"{Fore.YELLOW}Население:{Style.RESET_ALL} {Fore.CYAN}{population:,} человек{Style.RESET_ALL}")
    
    print()
    
    # Экономика
    _print_section_header("ЭКОНОМИКА")
    
    currencies = country.get('currencies', {})
    if currencies:
        print(f"{Fore.YELLOW}Валюты:{Style.RESET_ALL}")
        for code, currency_info in currencies.items():
            name = currency_info.get('name', '')
            symbol = currency_info.get('symbol', '')
            print(f"  {Fore.GREEN}{code}:{Style.RESET_ALL} {name} ({symbol})")
    
    print()
    
    # Языки
    _print_section_header("ЯЗЫКИ")
    
    languages = country.get('languages', {})
    if languages:
        lang_list = [f"{code}: {name}" for code, name in languages.items()]
        print(f"{Fore.CYAN}{', '.join(lang_list)}{Style.RESET_ALL}")
    
    print()
    
    # Временные зоны
    timezones = country.get('timezones', [])
    if timezones:
        _print_section_header("ВРЕМЕННЫЕ ЗОНЫ")
        for tz in timezones:
            print(f"  {Fore.CYAN}{tz}{Style.RESET_ALL}")
        print()
    
    # Телефонный код
    idd = country.get('idd', {})
    if idd:
        root = idd.get('root', '')
        suffixes = idd.get('suffixes', [])
        if root and suffixes:
            _print_section_header("ТЕЛЕФОННЫЙ КОД")
            print(f"{Fore.CYAN}{root}{suffixes[0]}{Style.RESET_ALL}\n")
    
    # Почтовый индекс
    postal_code = country.get('postalCode', {})
    if postal_code:
        _print_section_header("ПОЧТОВЫЙ ИНДЕКС")
        format_str = postal_code.get('format', '')
        if format_str:
            print(f"{Fore.CYAN}Формат: {format_str}{Style.RESET_ALL}\n")
    
    # Карты
    maps = country.get('maps', {})
    if maps:
        _print_section_header("КАРТЫ")
        google_maps = maps.get('googleMaps')
        openstreetmap = maps.get('openStreetMaps')
        if google_maps:
            print(f"{Fore.YELLOW}Google Maps:{Style.RESET_ALL} {Fore.CYAN}{google_maps}{Style.RESET_ALL}")
        if openstreetmap:
            print(f"{Fore.YELLOW}OpenStreetMap:{Style.RESET_ALL} {Fore.CYAN}{openstreetmap}{Style.RESET_ALL}")
        print()
    
    # Флаги (изображения)
    flags = country.get('flags', {})
    if flags:
        _print_section_header("ИЗОБРАЖЕНИЯ ФЛАГОВ")
        png = flags.get('png')
        svg = flags.get('svg')
        if png:
            print(f"{Fore.YELLOW}PNG:{Style.RESET_ALL} {Fore.CYAN}{png}{Style.RESET_ALL}")
        if svg:
            print(f"{Fore.YELLOW}SVG:{Style.RESET_ALL} {Fore.CYAN}{svg}{Style.RESET_ALL}")
        print()
    
    # Дополнительная информация
    _print_section_header("ДОПОЛНИТЕЛЬНО")
    
    independent = country.get('independent', None)
    if independent is not None:
        status = "Да" if independent else "Нет"
        print(f"{Fore.YELLOW}Независимое государство:{Style.RESET_ALL} {Fore.CYAN}{status}{Style.RESET_ALL}")
    
    un_member = country.get('unMember', False)
    if un_member:
        print(f"{Fore.YELLOW}Член ООН:{Style.RESET_ALL} {Fore.CYAN}Да{Style.RESET_ALL}")
    
    status = country.get('status')
    if status:
        print(f"{Fore.YELLOW}Статус:{Style.RESET_ALL} {Fore.CYAN}{status}{Style.RESET_ALL}")
    
    print()
    print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")


def _print_section_header(title: str) -> None:
    """Выводит заголовок секции."""
    print(f"{Fore.MAGENTA}{'─'*70}{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{title.center(70)}{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{'─'*70}{Style.RESET_ALL}")

