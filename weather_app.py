"""Модуль для работы с погодным API OpenWeatherMap."""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

import requests
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

API_KEY = os.getenv("API_KEY")
WEATHER_CACHE_FILE = "weather_cache.json"
GEOCODING_API_URL = "https://api.openweathermap.org/geo/1.0/direct"
WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_API_URL = "https://api.openweathermap.org/data/2.5/forecast"
AIR_POLLUTION_API_URL = "https://api.openweathermap.org/data/2.5/air_pollution"


def _make_request_with_retry(
    url: str,
    params: Dict[str, Any],
    max_retries: int = 3,
    base_delay: float = 1.0
) -> requests.Response:
    """
    Выполняет HTTP запрос с повторными попытками при ошибках.
    
    Args:
        url: URL для запроса
        params: Параметры запроса
        max_retries: Максимальное количество попыток
        base_delay: Базовая задержка в секундах для экспоненциального backoff
        
    Returns:
        Response объект
        
    Raises:
        requests.RequestException: При ошибке выполнения запроса после всех попыток
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=10)
            
            # Если успешный ответ или ошибка не требующая повтора
            if response.status_code == 200:
                return response
            
            # Если 429 (Too Many Requests) или временная ошибка - повторяем
            if response.status_code == 429 or (500 <= response.status_code < 600):
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                else:
                    raise requests.RequestException(
                        f"Ошибка сервера после {max_retries} попыток: {response.status_code}"
                    )
            
            # Для других ошибок сразу возвращаем ответ
            return response
            
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)
            else:
                raise requests.RequestException(f"Сетевая ошибка после {max_retries} попыток: {e}")
    
    if last_exception:
        raise last_exception
    
    raise requests.RequestException("Не удалось выполнить запрос")


def _load_cache() -> list:
    """Загружает данные из кэша. Возвращает список записей кэша."""
    cache_path = Path(WEATHER_CACHE_FILE)
    if not cache_path.exists():
        return []
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            # Поддержка старого формата (одиночная запись)
            if isinstance(cache_data, dict) and "weather_data" in cache_data:
                return [cache_data]
            # Новый формат (массив)
            if isinstance(cache_data, dict) and "cache" in cache_data:
                return cache_data.get("cache", [])
            # Если уже массив
            if isinstance(cache_data, list):
                return cache_data
            return []
    except (json.JSONDecodeError, IOError):
        return []


def _save_cache_entry(data: Dict[str, Any], city: Optional[str] = None, 
                      lat: Optional[float] = None, lon: Optional[float] = None) -> None:
    """
    Сохраняет данные в кэш с метаданными.
    Кэш содержит максимум 10 записей, при добавлении новой удаляется самая старая.
    """
    MAX_CACHE_SIZE = 10
    
    cache_entry = {
        "city": city,
        "lat": lat,
        "lon": lon,
        "fetched_at": datetime.now().isoformat(),
        "weather_data": data
    }
    
    # Загружаем существующий кэш
    cache_list = _load_cache()
    
    # Добавляем новую запись в начало (самая свежая)
    cache_list.insert(0, cache_entry)
    
    # Ограничиваем размер кэша (удаляем самые старые)
    if len(cache_list) > MAX_CACHE_SIZE:
        cache_list = cache_list[:MAX_CACHE_SIZE]
    
    # Сохраняем обратно
    try:
        with open(WEATHER_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump({"cache": cache_list}, f, ensure_ascii=False, indent=2)
    except IOError:
        # Не критично, если не удалось сохранить кэш
        pass


def _find_in_cache_by_city(city: str) -> Optional[Dict[str, Any]]:
    """
    Ищет в кэше запись по названию города.
    Возвращает самую свежую запись, если найдено несколько.
    
    Args:
        city: Название города для поиска
        
    Returns:
        Словарь с данными о погоде или None, если не найдено
    """
    cache_list = _load_cache()
    
    # Ищем все записи с совпадающим городом (без учета регистра)
    matches = [
        entry for entry in cache_list
        if entry.get("city") and entry.get("city").lower() == city.lower()
    ]
    
    if not matches:
        return None
    
    # Возвращаем самую свежую (первую в списке, так как они отсортированы по дате)
    return matches[0].get("weather_data")


def _find_in_cache_by_coordinates(lat: float, lon: float, tolerance: float = 0.01) -> Optional[Dict[str, Any]]:
    """
    Ищет в кэше запись по координатам.
    Возвращает самую свежую запись, если найдено несколько.
    
    Args:
        lat: Широта
        lon: Долгота
        tolerance: Допустимая погрешность для сравнения координат
        
    Returns:
        Словарь с данными о погоде или None, если не найдено
    """
    cache_list = _load_cache()
    
    # Ищем все записи с совпадающими координатами (с учетом погрешности)
    matches = []
    for entry in cache_list:
        entry_lat = entry.get("lat")
        entry_lon = entry.get("lon")
        
        if entry_lat is not None and entry_lon is not None:
            if abs(float(entry_lat) - float(lat)) <= tolerance and abs(float(entry_lon) - float(lon)) <= tolerance:
                matches.append(entry)
    
    if not matches:
        return None
    
    # Возвращаем самую свежую (первую в списке)
    return matches[0].get("weather_data")


def get_coordinates(city: str) -> Tuple[float, float]:
    """
    Получает координаты города через Geocoding API.
    
    Args:
        city: Название города
        
    Returns:
        Кортеж (широта, долгота)
        
    Raises:
        ValueError: При ошибке получения координат
    """
    if not API_KEY:
        raise ValueError("API ключ не найден. Убедитесь, что файл .env содержит API_KEY")
    
    if not city:
        raise ValueError("Название города не может быть пустым")
    
    params = {
        "q": city,
        "limit": 1,
        "appid": API_KEY,
        "lang": "ru"
    }
    
    try:
        response = _make_request_with_retry(GEOCODING_API_URL, params)
        
        if response.status_code != 200:
            error_msg = f"Ошибка API: статус {response.status_code}"
            try:
                error_data = response.json()
                if "message" in error_data:
                    error_msg = error_data["message"]
                    # Русификация сообщений об ошибках
                    if "city not found" in error_msg.lower():
                        error_msg = "Город с таким названием не найден"
            except:
                pass
            raise ValueError(error_msg)
        
        data = response.json()
        
        if not data or len(data) == 0:
            raise ValueError(f"Город '{city}' не найден")
        
        location = data[0]
        lat = location.get("lat")
        lon = location.get("lon")
        
        if lat is None or lon is None:
            raise ValueError("Координаты не найдены в ответе API")
        
        return (float(lat), float(lon))
        
    except requests.RequestException as e:
        # При сетевой ошибке после всех попыток - пробрасываем исключение
        raise requests.RequestException(f"Сетевая ошибка: {e}")


def get_weather_by_coordinates(lat: float, lon: float) -> Dict[str, Any]:
    """
    Получает погоду по координатам через Current Weather API.
    
    Args:
        lat: Широта
        lon: Долгота
        
    Returns:
        Словарь с данными о погоде
        
    Raises:
        ValueError: При ошибке получения погоды
        requests.RequestException: При сетевой ошибке после всех попыток
    """
    if not API_KEY:
        raise ValueError("API ключ не найден. Убедитесь, что файл .env содержит API_KEY")
    
    params = {
        "lat": lat,
        "lon": lon,
        "appid": API_KEY,
        "units": "metric",
        "lang": "ru"
    }
    
    try:
        response = _make_request_with_retry(WEATHER_API_URL, params)
        
        if response.status_code != 200:
            error_msg = f"Ошибка API: статус {response.status_code}"
            try:
                error_data = response.json()
                if "message" in error_data:
                    error_msg = error_data["message"]
                    # Русификация сообщений об ошибках
                    if "city not found" in error_msg.lower():
                        error_msg = "Город с таким названием не найден"
            except:
                pass
            raise ValueError(error_msg)
        
        data = response.json()
        
        # Сохраняем в кэш
        _save_cache_entry(data, lat=lat, lon=lon)
        
        return data
        
    except requests.RequestException as e:
        # При сетевой ошибке после всех попыток - пробрасываем исключение
        # Предложение использовать кэш будет в main.py
        raise requests.RequestException(f"Сетевая ошибка: {e}")


def get_weather_by_city(city: str) -> Dict[str, Any]:
    """
    Получает погоду по названию города.
    
    Args:
        city: Название города
        
    Returns:
        Словарь с данными о погоде
        
    Raises:
        ValueError: При ошибке получения погоды
        requests.RequestException: При сетевой ошибке после всех попыток
    """
    if not API_KEY:
        raise ValueError("API ключ не найден. Убедитесь, что файл .env содержит API_KEY")
    
    if not city:
        raise ValueError("Название города не может быть пустым")
    
    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric",
        "lang": "ru"
    }
    
    try:
        response = _make_request_with_retry(WEATHER_API_URL, params)
        
        if response.status_code != 200:
            error_msg = f"Ошибка API: статус {response.status_code}"
            try:
                error_data = response.json()
                if "message" in error_data:
                    error_msg = error_data["message"]
                    # Русификация сообщений об ошибках
                    if "city not found" in error_msg.lower():
                        error_msg = "Город с таким названием не найден"
            except:
                pass
            raise ValueError(error_msg)
        
        data = response.json()
        
        # Сохраняем в кэш
        coord = data.get("coord", {})
        lat = coord.get("lat")
        lon = coord.get("lon")
        _save_cache_entry(data, city=city, lat=lat, lon=lon)
        
        return data
        
    except requests.RequestException as e:
        # При сетевой ошибке после всех попыток - пробрасываем исключение
        # Предложение использовать кэш будет в main.py
        raise requests.RequestException(f"Сетевая ошибка: {e}")


def get_cached_weather_by_city(city: str) -> Optional[Dict[str, Any]]:
    """
    Получает данные о погоде из кэша по названию города.
    
    Args:
        city: Название города
        
    Returns:
        Словарь с данными о погоде или None, если не найдено
    """
    return _find_in_cache_by_city(city)


def get_cached_weather_by_coordinates(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """
    Получает данные о погоде из кэша по координатам.
    
    Args:
        lat: Широта
        lon: Долгота
        
    Returns:
        Словарь с данными о погоде или None, если не найдено
    """
    return _find_in_cache_by_coordinates(lat, lon)


def get_forecast_5d3h(lat: float, lon: float) -> List[Dict[str, Any]]:
    """
    Получает прогноз погоды на 5 дней с интервалом 3 часа через Forecast API.
    
    Args:
        lat: Широта
        lon: Долгота
        
    Returns:
        Список словарей с данными прогноза
        
    Raises:
        ValueError: При ошибке получения прогноза
        requests.RequestException: При сетевой ошибке после всех попыток
    """
    if not API_KEY:
        raise ValueError("API ключ не найден. Убедитесь, что файл .env содержит API_KEY")
    
    params = {
        "lat": lat,
        "lon": lon,
        "appid": API_KEY,
        "units": "metric",
        "lang": "ru"
    }
    
    try:
        response = _make_request_with_retry(FORECAST_API_URL, params)
        
        if response.status_code != 200:
            error_msg = f"Ошибка API: статус {response.status_code}"
            try:
                error_data = response.json()
                if "message" in error_data:
                    error_msg = error_data["message"]
                    # Русификация сообщений об ошибках
                    if "city not found" in error_msg.lower():
                        error_msg = "Город с таким названием не найден"
            except:
                pass
            raise ValueError(error_msg)
        
        data = response.json()
        
        # Возвращаем список прогнозов
        forecast_list = data.get("list", [])
        city_info = data.get("city", {})
        
        # Добавляем информацию о городе к каждому элементу для удобства
        result = []
        for item in forecast_list:
            item_with_city = item.copy()
            item_with_city["_city_info"] = city_info
            result.append(item_with_city)
        
        return result
        
    except requests.RequestException as e:
        # При сетевой ошибке после всех попыток - пробрасываем исключение
        raise requests.RequestException(f"Сетевая ошибка: {e}")


def get_air_pollution(lat: float, lon: float) -> Dict[str, Any]:
    """
    Получает данные о качестве воздуха через Air Pollution API.
    
    Args:
        lat: Широта
        lon: Долгота
        
    Returns:
        Словарь с данными о качестве воздуха (list[0].components)
        
    Raises:
        ValueError: При ошибке получения данных
        requests.RequestException: При сетевой ошибке после всех попыток
    """
    if not API_KEY:
        raise ValueError("API ключ не найден. Убедитесь, что файл .env содержит API_KEY")
    
    params = {
        "lat": lat,
        "lon": lon,
        "appid": API_KEY
    }
    
    try:
        response = _make_request_with_retry(AIR_POLLUTION_API_URL, params)
        
        if response.status_code != 200:
            error_msg = f"Ошибка API: статус {response.status_code}"
            try:
                error_data = response.json()
                if "message" in error_data:
                    error_msg = error_data["message"]
            except:
                pass
            raise ValueError(error_msg)
        
        data = response.json()
        
        # Возвращаем компоненты из первого элемента списка
        if "list" in data and len(data["list"]) > 0:
            return data["list"][0].get("components", {})
        else:
            raise ValueError("Данные о качестве воздуха не найдены в ответе API")
        
    except requests.RequestException as e:
        raise requests.RequestException(f"Сетевая ошибка: {e}")


def analyze_air_pollution(components: Dict[str, Any], extended: bool = False) -> Dict[str, Any]:
    """
    Анализирует качество воздуха на основе компонентов и сравнивает с нормами.
    
    Args:
        components: Словарь с компонентами загрязнения воздуха
        extended: Если True, возвращает расширенную информацию
        
    Returns:
        Словарь с общим статусом и деталями:
        - overall_status: общий статус (строка)
        - overall_index: общий индекс AQI (1-5)
        - exceeded_norms: список превышений нормы (если extended=True)
        - within_norms: список в пределах нормы (если extended=True)
    """
    # Таблица норм из изображения
    AQI_LEVELS = {
        "so2": [
            (0, 20, 1, "Хорошо"),
            (20, 80, 2, "Удовлетворительно"),
            (80, 250, 3, "Умеренно"),
            (250, 350, 4, "Плохо"),
            (350, float('inf'), 5, "Очень плохо")
        ],
        "no2": [
            (0, 40, 1, "Хорошо"),
            (40, 70, 2, "Удовлетворительно"),
            (70, 150, 3, "Умеренно"),
            (150, 200, 4, "Плохо"),
            (200, float('inf'), 5, "Очень плохо")
        ],
        "pm10": [
            (0, 20, 1, "Хорошо"),
            (20, 50, 2, "Удовлетворительно"),
            (50, 100, 3, "Умеренно"),
            (100, 200, 4, "Плохо"),
            (200, float('inf'), 5, "Очень плохо")
        ],
        "pm2_5": [
            (0, 10, 1, "Хорошо"),
            (10, 25, 2, "Удовлетворительно"),
            (25, 50, 3, "Умеренно"),
            (50, 75, 4, "Плохо"),
            (75, float('inf'), 5, "Очень плохо")
        ],
        "o3": [
            (0, 60, 1, "Хорошо"),
            (60, 100, 2, "Удовлетворительно"),
            (100, 140, 3, "Умеренно"),
            (140, 180, 4, "Плохо"),
            (180, float('inf'), 5, "Очень плохо")
        ],
        "co": [
            (0, 4400, 1, "Хорошо"),
            (4400, 9400, 2, "Удовлетворительно"),
            (9400, 12400, 3, "Умеренно"),
            (12400, 15400, 4, "Плохо"),
            (15400, float('inf'), 5, "Очень плохо")
        ]
    }
    
    # Названия компонентов для вывода
    COMPONENT_NAMES = {
        "so2": "SO2",
        "no2": "NO2",
        "pm10": "PM10",
        "pm2_5": "PM2.5",
        "o3": "O3",
        "co": "CO"
    }
    
    # Определяем уровень для каждого компонента
    component_levels = {}
    max_index = 1
    max_status = "Хорошо"
    
    for component_key, value in components.items():
        if component_key in AQI_LEVELS and value is not None:
            # Находим уровень для данного значения
            for min_val, max_val, index, status in AQI_LEVELS[component_key]:
                if min_val <= value < max_val:
                    component_levels[component_key] = {
                        "value": value,
                        "index": index,
                        "status": status,
                        "name": COMPONENT_NAMES.get(component_key, component_key.upper())
                    }
                    # Обновляем максимальный индекс (худший показатель)
                    if index > max_index:
                        max_index = index
                        max_status = status
                    break
    
    # Определяем общий статус на основе худшего показателя
    result = {
        "overall_status": max_status,
        "overall_index": max_index
    }
    
    if extended:
        # Формируем список превышений нормы (индекс >= 2)
        exceeded = []
        for comp_key, comp_data in component_levels.items():
            if comp_data["index"] >= 2:
                exceeded.append({
                    "name": comp_data["name"],
                    "value": comp_data["value"],
                    "status": comp_data["status"],
                    "index": comp_data["index"]
                })
        
        # Сортируем по индексу (от худшего к лучшему)
        exceeded.sort(key=lambda x: x["index"], reverse=True)
        
        result["exceeded_norms"] = exceeded
        result["component_levels"] = component_levels
    
    return result
