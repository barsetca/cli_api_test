"""Модуль для работы с файловым хранилищем (I/O операции)."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


def read_from_file(path: str = "currency_rate.json") -> Optional[Dict[str, Any]]:
    """
    Читает данные о курсах валют из файла.
    
    Args:
        path: Путь к файлу с данными
        
    Returns:
        Словарь с данными о курсах валют или None, если файл не существует
    """
    file_path = Path(path)
    
    if not file_path.exists():
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except (json.JSONDecodeError, IOError) as e:
        raise IOError(f"Ошибка при чтении файла {path}: {e}")


def save_to_file(data: Dict[str, Any], path: str = "currency_rate.json") -> None:
    """
    Сохраняет данные о курсах валют в файл.
    
    Args:
        data: Словарь с данными для сохранения
        path: Путь к файлу для сохранения
    """
    file_path = Path(path)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except IOError as e:
        raise IOError(f"Ошибка при записи файла {path}: {e}")


def get_file_date(path: str = "currency_rate.json") -> Optional[str]:
    """
    Получает дату создания/модификации файла.
    
    Args:
        path: Путь к файлу
        
    Returns:
        Строка с датой в формате YYYY-MM-DD или None, если файл не существует
    """
    file_path = Path(path)
    
    if not file_path.exists():
        return None
    
    # Получаем время модификации файла
    timestamp = file_path.stat().st_mtime
    file_date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
    return file_date


def is_file_today(path: str = "currency_rate.json") -> bool:
    """
    Проверяет, был ли файл создан/обновлен сегодня.
    
    Args:
        path: Путь к файлу
        
    Returns:
        True, если файл был обновлен сегодня, иначе False
    """
    file_date = get_file_date(path)
    if file_date is None:
        return False
    
    today = datetime.now().strftime('%Y-%m-%d')
    return file_date == today


def get_file_data_date(path: str = "currency_rate.json") -> Optional[str]:
    """
    Получает дату данных из самого файла (если она там сохранена).
    
    Args:
        path: Путь к файлу
        
    Returns:
        Строка с датой из файла или None
    """
    data = read_from_file(path)
    if data and 'date' in data:
        return data['date']
    return None

