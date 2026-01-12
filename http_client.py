"""Модуль для выполнения HTTP запросов."""

import requests
from typing import Optional, Dict, Any


def get(url: str, params: Optional[Dict[str, Any]] = None, timeout: int = 10) -> requests.Response:
    """
    Выполняет GET запрос к указанному URL.
    
    Args:
        url: URL для запроса
        params: Параметры запроса (query parameters)
        timeout: Таймаут запроса в секундах
        
    Returns:
        Response объект от requests
        
    Raises:
        requests.RequestException: При ошибке выполнения запроса
    """
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()  # Проверка статуса
        return response
    except requests.exceptions.HTTPError as e:
        raise requests.RequestException(f"HTTP ошибка: {e}")
    except requests.exceptions.RequestException as e:
        raise requests.RequestException(f"Ошибка при выполнении GET запроса: {e}")


def post(url: str, data: Optional[Dict[str, Any]] = None, 
         json: Optional[Dict[str, Any]] = None, 
         timeout: int = 10) -> requests.Response:
    """
    Выполняет POST запрос к указанному URL.
    
    Args:
        url: URL для запроса
        data: Данные для отправки (form data)
        json: JSON данные для отправки
        timeout: Таймаут запроса в секундах
        
    Returns:
        Response объект от requests
        
    Raises:
        requests.RequestException: При ошибке выполнения запроса
    """
    try:
        response = requests.post(url, data=data, json=json, timeout=timeout)
        response.raise_for_status()  # Проверка статуса
        return response
    except requests.exceptions.HTTPError as e:
        raise requests.RequestException(f"HTTP ошибка: {e}")
    except requests.exceptions.RequestException as e:
        raise requests.RequestException(f"Ошибка при выполнении POST запроса: {e}")

