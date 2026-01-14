"""Telegram-бот для получения информации о погоде."""

import json
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

import telebot
from telebot import types
from dotenv import load_dotenv

from weather_app import (
    get_coordinates,
    get_weather_by_coordinates,
    get_weather_by_city,
    get_forecast_5d3h,
    get_air_pollution,
    analyze_air_pollution
)

# Загрузка переменных окружения
load_dotenv()

# Токен бота из .env
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле. Добавьте BOT_TOKEN=ваш_токен")

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)

# Файлы для хранения данных пользователей
USERS_DATA_FILE = "users_data.json"
NOTIFICATIONS_FILE = "notifications.json"

# Русские названия дней недели
WEEKDAYS_RU = {
    0: "Понедельник",
    1: "Вторник",
    2: "Среда",
    3: "Четверг",
    4: "Пятница",
    5: "Суббота",
    6: "Воскресенье"
}

# Уровни UV индекса
UV_LEVELS = {
    (0, 3): "Низкий",
    (3, 6): "Умеренный",
    (6, 8): "Высокий",
    (8, 11): "Очень высокий",
    (11, float('inf')): "Экстремальный"
}


def load_users_data() -> Dict[str, Any]:
    """Загружает данные пользователей из файла."""
    if Path(USERS_DATA_FILE).exists():
        try:
            with open(USERS_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_users_data(data: Dict[str, Any]) -> None:
    """Сохраняет данные пользователей в файл."""
    with open(USERS_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_notifications() -> Dict[str, Dict[str, Any]]:
    """Загружает подписки на уведомления."""
    if Path(NOTIFICATIONS_FILE).exists():
        try:
            with open(NOTIFICATIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_notifications(data: Dict[str, Dict[str, Any]]) -> None:
    """Сохраняет подписки на уведомления."""
    with open(NOTIFICATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user_location(user_id: str) -> Optional[tuple]:
    """Получает сохраненную геолокацию пользователя."""
    users_data = load_users_data()
    user_data = users_data.get(user_id, {})
    lat = user_data.get("lat")
    lon = user_data.get("lon")
    if lat and lon:
        return (float(lat), float(lon))
    return None


def save_user_location(user_id: str, lat: float, lon: float) -> None:
    """Сохраняет геолокацию пользователя."""
    users_data = load_users_data()
    if user_id not in users_data:
        users_data[user_id] = {}
    users_data[user_id]["lat"] = lat
    users_data[user_id]["lon"] = lon
    save_users_data(users_data)


def format_weather_message(weather_data: Dict[str, Any], city_name: str = None) -> str:
    """Форматирует сообщение о текущей погоде."""
    if not city_name:
        city_name = weather_data.get("name", "Неизвестно")
    
    main_data = weather_data.get("main", {})
    temp = main_data.get("temp", "N/A")
    feels_like = main_data.get("feels_like", "N/A")
    humidity = main_data.get("humidity", "N/A")
    pressure = main_data.get("pressure", "N/A")
    
    wind_data = weather_data.get("wind", {})
    wind_speed = wind_data.get("speed", "N/A")
    wind_deg = wind_data.get("deg", "N/A")
    
    weather_list = weather_data.get("weather", [])
    description = "N/A"
    if weather_list and len(weather_list) > 0:
        description = weather_list[0].get("description", "N/A").capitalize()
    
    visibility = weather_data.get("visibility", "N/A")
    if isinstance(visibility, (int, float)):
        visibility_km = visibility / 1000.0
        visibility_str = f"{visibility_km:.1f} км"
    else:
        visibility_str = str(visibility)
    
    message = f"🌤️ <b>Погода в {city_name}</b>\n\n"
    message += f"🌡️ Температура: {temp}°C\n"
    message += f"💭 Ощущается как: {feels_like}°C\n"
    message += f"💧 Влажность: {humidity}%\n"
    message += f"📊 Давление: {pressure} гПа\n"
    message += f"💨 Ветер: {wind_speed} м/с"
    if isinstance(wind_deg, (int, float)):
        message += f" ({wind_deg}°)\n"
    else:
        message += "\n"
    message += f"👁️ Видимость: {visibility_str}\n"
    message += f"☁️ {description}"
    
    return message


def format_extended_weather(weather_data: Dict[str, Any], air_analysis: Dict[str, Any], city_name: str) -> str:
    """Форматирует расширенные данные о погоде."""
    message = f"📊 <b>Расширенные данные о погоде</b>\n\n"
    message += f"📍 <b>Город:</b> {city_name}\n\n"
    
    # Данные о погоде
    main_data = weather_data.get("main", {})
    temp = main_data.get("temp", "N/A")
    humidity = main_data.get("humidity", "N/A")
    pressure = main_data.get("pressure", "N/A")
    
    wind_data = weather_data.get("wind", {})
    wind_speed = wind_data.get("speed", "N/A")
    
    visibility = weather_data.get("visibility", "N/A")
    if isinstance(visibility, (int, float)):
        visibility_km = visibility / 1000.0
        visibility_str = f"{visibility_km:.1f} км"
    else:
        visibility_str = str(visibility)
    
    sys_data = weather_data.get("sys", {})
    sunrise = sys_data.get("sunrise")
    sunset = sys_data.get("sunset")
    
    sunrise_str = "N/A"
    sunset_str = "N/A"
    if sunrise:
        try:
            sunrise_dt = datetime.fromtimestamp(sunrise)
            sunrise_str = sunrise_dt.strftime("%H:%M")
        except:
            pass
    if sunset:
        try:
            sunset_dt = datetime.fromtimestamp(sunset)
            sunset_str = sunset_dt.strftime("%H:%M")
        except:
            pass
    
    # UV индекс (если доступен)
    uv_index = weather_data.get("uv", 0)
    uv_level = "Низкий"
    if isinstance(uv_index, (int, float)):
        for (min_val, max_val), level in UV_LEVELS.items():
            if min_val <= uv_index < max_val:
                uv_level = level
                break
        uv_display = f"{uv_index:.1f} ({uv_level})"
    else:
        uv_display = "N/A"
    
    # Облачность
    clouds = weather_data.get("clouds", {}).get("all", "N/A")
    
    message += f"🌡️ <b>Температура:</b> {temp}°C\n"
    message += f"💧 <b>Влажность:</b> {humidity}%\n"
    message += f"📊 <b>Давление:</b> {pressure} гПа\n"
    message += f"💨 <b>Ветер:</b> {wind_speed} м/с\n"
    message += f"👁️ <b>Видимость:</b> {visibility_str}\n"
    message += f"☁️ <b>Облачность:</b> {clouds}%\n"
    message += f"🌅 <b>Восход солнца:</b> {sunrise_str}\n"
    message += f"🌇 <b>Закат солнца:</b> {sunset_str}\n"
    message += f"☀️ <b>UV индекс:</b> {uv_display}\n\n"
    
    # Качество воздуха
    message += f"🌬️ <b>Качество воздуха:</b>\n"
    overall_status = air_analysis.get("overall_status", "N/A")
    message += f"Общий статус: {overall_status}\n"
    
    exceeded_norms = air_analysis.get("exceeded_norms", [])
    if exceeded_norms:
        first_exceeded = exceeded_norms[0]
        message += f"Превышение нормы: {first_exceeded['name']} : {first_exceeded['value']:.2f} мкг/м³ - {first_exceeded['status']}\n"
    else:
        message += "Превышение нормы: Нет превышений\n"
    
    weather_list = weather_data.get("weather", [])
    conditions = "N/A"
    if weather_list and len(weather_list) > 0:
        conditions = weather_list[0].get("description", "N/A").capitalize()
    message += f"Условия: {conditions}"
    
    return message


def get_weather_icon(weather_main: str, weather_id: int = None) -> str:
    """Возвращает иконку на основе погодных условий."""
    if not weather_main:
        return "🌤️"
    
    weather_main_lower = weather_main.lower()
    
    # Определяем иконку на основе основного типа погоды
    if "clear" in weather_main_lower or weather_main == "Clear":
        return "☀️"
    elif "clouds" in weather_main_lower or weather_main == "Clouds":
        if weather_id:
            # 801-802: мало облаков, 803-804: много облаков
            if 801 <= weather_id <= 802:
                return "⛅"
            else:
                return "☁️"
        return "☁️"
    elif "rain" in weather_main_lower or weather_main == "Rain":
        return "🌧️"
    elif "drizzle" in weather_main_lower or weather_main == "Drizzle":
        return "🌦️"
    elif "thunderstorm" in weather_main_lower or weather_main == "Thunderstorm":
        return "⛈️"
    elif "snow" in weather_main_lower or weather_main == "Snow":
        return "❄️"
    elif "mist" in weather_main_lower or "fog" in weather_main_lower or weather_main in ["Mist", "Fog"]:
        return "🌫️"
    else:
        return "🌤️"


def format_forecast_day(forecast_list: list, date_str: str, city_name: str) -> str:
    """Форматирует прогноз для одного дня."""
    date_forecasts = [
        item for item in forecast_list
        if item.get("dt_txt", "").startswith(date_str)
    ]
    
    if not date_forecasts:
        return "Нет данных для выбранной даты."
    
    date_forecasts.sort(key=lambda x: x.get("dt_txt", ""))
    
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        weekday = WEEKDAYS_RU[date_obj.weekday()]
        formatted_date = date_obj.strftime("%d.%m.%Y")
    except:
        formatted_date = date_str
        weekday = ""
    
    message = f"📅 <b>Прогноз на {formatted_date}"
    if weekday:
        message += f" - {weekday}"
    message += f"</b>\n\n"
    message += f"📍 <b>Город:</b> {city_name}\n\n"
    
    for item in date_forecasts:
        dt_txt = item.get("dt_txt", "")
        time_str = dt_txt.split()[1] if " " in dt_txt else ""
        if time_str:
            try:
                time_obj = datetime.strptime(time_str, "%H:%M:%S")
                formatted_time = time_obj.strftime("%H:%M")
            except:
                formatted_time = time_str[:5]
        else:
            formatted_time = "N/A"
        
        temp = item.get("main", {}).get("temp", "N/A")
        if isinstance(temp, (int, float)):
            temp_str = f"{temp:.2f}°C"
        else:
            temp_str = str(temp)
        
        weather_desc = "N/A"
        weather_main = "Clear"
        weather_id = None
        weather_list = item.get("weather", [])
        if weather_list and len(weather_list) > 0:
            weather_desc = weather_list[0].get("description", "N/A").capitalize()
            weather_main = weather_list[0].get("main", "Clear")
            weather_id = weather_list[0].get("id")
        
        # Получаем иконку на основе погодных условий
        icon = get_weather_icon(weather_main, weather_id)
        
        message += f"{icon} {formatted_time}: {temp_str}, {weather_desc}\n"
    
    return message


def format_city_comparison(city1: str, weather1: Dict[str, Any], city2: str, weather2: Dict[str, Any]) -> str:
    """Форматирует сравнение двух городов."""
    message = f"⚖️ <b>Сравнение городов</b>\n\n"
    
    temp1 = weather1.get("main", {}).get("temp", "N/A")
    temp2 = weather2.get("main", {}).get("temp", "N/A")
    
    humidity1 = weather1.get("main", {}).get("humidity", "N/A")
    humidity2 = weather2.get("main", {}).get("humidity", "N/A")
    
    wind1 = weather1.get("wind", {}).get("speed", "N/A")
    wind2 = weather2.get("wind", {}).get("speed", "N/A")
    
    desc1 = "N/A"
    desc2 = "N/A"
    weather_list1 = weather1.get("weather", [])
    weather_list2 = weather2.get("weather", [])
    if weather_list1 and len(weather_list1) > 0:
        desc1 = weather_list1[0].get("description", "N/A").capitalize()
    if weather_list2 and len(weather_list2) > 0:
        desc2 = weather_list2[0].get("description", "N/A").capitalize()
    
    message += f"<b>{city1}</b> vs <b>{city2}</b>\n\n"
    message += f"🌡️ Температура:\n"
    message += f"   {city1}: {temp1}°C\n"
    message += f"   {city2}: {temp2}°C\n\n"
    message += f"💧 Влажность:\n"
    message += f"   {city1}: {humidity1}%\n"
    message += f"   {city2}: {humidity2}%\n\n"
    message += f"💨 Ветер:\n"
    message += f"   {city1}: {wind1} м/с\n"
    message += f"   {city2}: {wind2} м/с\n\n"
    message += f"☁️ Условия:\n"
    message += f"   {city1}: {desc1}\n"
    message += f"   {city2}: {desc2}"
    
    return message


def get_main_menu_keyboard():
    """Возвращает клавиатуру главного меню."""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        types.KeyboardButton("🌡️ Текущая погода"),
        types.KeyboardButton("📅 Прогноз на 5 дней"),
        types.KeyboardButton("📍 Моя геолокация"),
        types.KeyboardButton("⚖️ Сравнить города"),
        types.KeyboardButton("📊 Расширенные данные"),
        types.KeyboardButton("🔔 Уведомления")
    )
    return keyboard


def get_back_to_menu_keyboard():
    """Возвращает inline-клавиатуру с кнопкой 'Вернуться в меню'."""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("◀️ Вернуться в меню", callback_data="back_to_menu"))
    return keyboard


@bot.message_handler(commands=['start'])
def start_command(message):
    """Обработчик команды /start."""
    welcome_text = (
        "🌤️ <b>Добро пожаловать в бота погоды!</b>\n\n"
        "Я помогу вам узнать актуальную информацию о погоде:\n"
        "• Текущая погода по городу или геолокации\n"
        "• Прогноз на 5 дней вперед\n"
        "• Сравнение погоды в разных городах\n"
        "• Расширенные данные (погода + качество воздуха)\n"
        "• Уведомления о погоде\n\n"
        "Выберите действие из меню ниже:"
    )
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_menu_keyboard(), parse_mode='HTML')


@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def back_to_menu_callback(call):
    """Обработчик кнопки 'Вернуться в меню'."""
    welcome_text = (
        "🌤️ <b>Главное меню</b>\n\n"
        "Выберите действие:"
    )
    bot.send_message(call.message.chat.id, welcome_text, reply_markup=get_main_menu_keyboard(), parse_mode='HTML')
    bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda message: message.text == "🌡️ Текущая погода")
def current_weather_handler(message):
    """Обработчик запроса текущей погоды."""
    user_location = get_user_location(str(message.chat.id))
    
    if user_location:
        # Предлагаем выбрать: использовать сохраненную геолокацию или ввести новую
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("📍 Использовать сохраненную геолокацию", callback_data="weather_use_saved"))
        keyboard.add(types.InlineKeyboardButton("🆕 Ввести новый город/геолокацию", callback_data="weather_new_input"))
        bot.send_message(
            message.chat.id,
            "У вас есть сохраненная геолокация. Выберите действие:",
            reply_markup=keyboard
        )
    else:
        msg = bot.send_message(
            message.chat.id,
            "Введите название города или отправьте геолокацию:",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(msg, process_weather_input)


@bot.callback_query_handler(func=lambda call: call.data == "weather_use_saved")
def weather_use_saved_callback(call):
    """Обработчик использования сохраненной геолокации для текущей погоды."""
    try:
        user_location = get_user_location(str(call.message.chat.id))
        if user_location:
            lat, lon = user_location
            
            try:
                weather_data = get_weather_by_coordinates(lat, lon)
                city_name = weather_data.get("name", "Неизвестно")
                response = format_weather_message(weather_data, city_name)
                bot.send_message(
                    call.message.chat.id,
                    f"📍 <b>Используется сохраненная геолокация</b>\n\n{response}",
                    reply_markup=get_back_to_menu_keyboard(),
                    parse_mode='HTML'
                )
                bot.answer_callback_query(call.id)
            except Exception as e:
                bot.send_message(
                    call.message.chat.id,
                    f"❌ Ошибка получения погоды: {str(e)}",
                    reply_markup=get_back_to_menu_keyboard()
                )
                bot.answer_callback_query(call.id)
        else:
            bot.answer_callback_query(call.id, "Сохраненная геолокация не найдена.", show_alert=True)
    except Exception as e:
        bot.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data == "weather_new_input")
def weather_new_input_callback(call):
    """Обработчик ввода нового города/геолокации для текущей погоды."""
    try:
        msg = bot.send_message(
            call.message.chat.id,
            "Введите название города или отправьте геолокацию:",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(msg, process_weather_input)
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)


def process_weather_input(message):
    """Обрабатывает ввод города или геолокации для текущей погоды."""
    city_name = None
    try:
        if message.location:
            lat = message.location.latitude
            lon = message.location.longitude
            weather_data = get_weather_by_coordinates(lat, lon)
            city_name = weather_data.get("name", "Неизвестно")
            response = format_weather_message(weather_data, city_name)
        else:
            city = message.text.strip()
            city_name = city
            if not city:
                bot.send_message(message.chat.id, "Пожалуйста, введите название города.")
                return
            weather_data = get_weather_by_city(city)
            response = format_weather_message(weather_data, city)
        
        bot.send_message(message.chat.id, response, reply_markup=get_back_to_menu_keyboard(), parse_mode='HTML')
    except ValueError as e:
        error_msg = str(e)
        if "не найден" in error_msg.lower():
            if city_name:
                bot.send_message(
                    message.chat.id,
                    f"❌ Город '{city_name}' не найден. Попробуйте еще раз.",
                    reply_markup=get_back_to_menu_keyboard()
                )
            else:
                bot.send_message(
                    message.chat.id,
                    "❌ Город с таким названием не найден. Попробуйте еще раз.",
                    reply_markup=get_back_to_menu_keyboard()
                )
        else:
            bot.send_message(message.chat.id, f"❌ Ошибка: {error_msg}", reply_markup=get_back_to_menu_keyboard())
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Произошла ошибка: {str(e)}", reply_markup=get_back_to_menu_keyboard())


@bot.callback_query_handler(func=lambda call: call.data == "location_new_input")
def location_new_input_callback(call):
    """Обработчик ввода новой геолокации."""
    try:
        msg = bot.send_message(
            call.message.chat.id,
            "Введите геолокацию",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(msg, process_location_input)
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)


def process_location_input(message):
    """Обрабатывает ввод геолокации для сохранения."""
    try:
        if message.location:
            lat = message.location.latitude
            lon = message.location.longitude
            save_user_location(str(message.chat.id), lat, lon)
            
            try:
                weather_data = get_weather_by_coordinates(lat, lon)
                city_name = weather_data.get("name", "Неизвестно")
                response = format_weather_message(weather_data, city_name)
                bot.send_message(
                    message.chat.id,
                    f"✅ Геолокация сохранена!\n\n{response}",
                    reply_markup=get_back_to_menu_keyboard(),
                    parse_mode='HTML'
                )
            except Exception as e:
                bot.send_message(
                    message.chat.id,
                    f"✅ Геолокация сохранена!\n❌ Ошибка получения погоды: {str(e)}",
                    reply_markup=get_back_to_menu_keyboard()
                )
        else:
            bot.send_message(
                message.chat.id,
                "❌ Геолокация не получена. Пожалуйста, отправьте вашу геолокацию.",
                reply_markup=get_back_to_menu_keyboard()
            )
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"❌ Произошла ошибка: {str(e)}",
            reply_markup=get_back_to_menu_keyboard()
        )


@bot.message_handler(func=lambda message: message.text == "📅 Прогноз на 5 дней")
def forecast_handler(message):
    """Обработчик запроса прогноза на 5 дней."""
    user_location = get_user_location(str(message.chat.id))
    
    if user_location:
        # Предлагаем выбрать: использовать сохраненную геолокацию или ввести новую
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("📍 Использовать сохраненную геолокацию", callback_data="forecast_use_saved"))
        keyboard.add(types.InlineKeyboardButton("🆕 Ввести новый город/геолокацию", callback_data="forecast_new_input"))
        bot.send_message(
            message.chat.id,
            "У вас есть сохраненная геолокация. Выберите действие:",
            reply_markup=keyboard
        )
    else:
        msg = bot.send_message(
            message.chat.id,
            "Введите название города или отправьте геолокацию:",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(msg, process_forecast_input)


def process_forecast_input(message):
    """Обрабатывает ввод для прогноза."""
    city_name = None
    try:
        if message.location:
            lat = message.location.latitude
            lon = message.location.longitude
            save_user_location(str(message.chat.id), lat, lon)
        else:
            city = message.text.strip()
            city_name = city
            if not city:
                bot.send_message(message.chat.id, "Пожалуйста, введите название города.")
                return
            lat, lon = get_coordinates(city)
        
        show_forecast_menu(message.chat.id, lat, lon)
    except ValueError as e:
        error_msg = str(e)
        if "не найден" in error_msg.lower():
            if city_name:
                bot.send_message(
                    message.chat.id,
                    f"❌ Город '{city_name}' не найден. Попробуйте еще раз.",
                    reply_markup=get_back_to_menu_keyboard()
                )
            else:
                bot.send_message(
                    message.chat.id,
                    "❌ Город с таким названием не найден. Попробуйте еще раз.",
                    reply_markup=get_back_to_menu_keyboard()
                )
        else:
            bot.send_message(message.chat.id, f"❌ Ошибка: {error_msg}", reply_markup=get_back_to_menu_keyboard())
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Произошла ошибка: {str(e)}", reply_markup=get_back_to_menu_keyboard())


def show_forecast_menu(chat_id: int, lat: float, lon: float):
    """Показывает меню выбора дня для прогноза."""
    try:
        forecast_data = get_forecast_5d3h(lat, lon)
        
        # Группируем по датам
        dates_dict = {}
        city_name = forecast_data[0].get("_city_info", {}).get("name", "Неизвестно")
        
        for item in forecast_data:
            dt_txt = item.get("dt_txt", "")
            if dt_txt:
                date_str = dt_txt.split()[0]
                if date_str not in dates_dict:
                    dates_dict[date_str] = []
                dates_dict[date_str].append(item)
        
        sorted_dates = sorted(dates_dict.keys())[:5]
        
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for i, date_str in enumerate(sorted_dates):
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                weekday = WEEKDAYS_RU[date_obj.weekday()]
                formatted_date = date_obj.strftime("%d.%m.%Y")
                button_text = f"{formatted_date} - {weekday}"
            except:
                button_text = date_str
            
            callback_data = f"forecast_day_{date_str}_{lat}_{lon}"
            keyboard.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))
        
        bot.send_message(
            chat_id,
            f"📅 <b>Прогноз на 5 дней для {city_name}</b>\n\nВыберите день:",
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    except Exception as e:
        bot.send_message(chat_id, f"❌ Произошла ошибка: {str(e)}")


@bot.callback_query_handler(func=lambda call: call.data.startswith("forecast_day_"))
def forecast_day_callback(call):
    """Обработчик выбора дня в прогнозе."""
    try:
        parts = call.data.split("_")
        date_str = parts[2]
        lat = float(parts[3])
        lon = float(parts[4])
        
        forecast_data = get_forecast_5d3h(lat, lon)
        city_name = forecast_data[0].get("_city_info", {}).get("name", "Неизвестно")
        
        message_text = format_forecast_day(forecast_data, date_str, city_name)
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("◀️ Назад", callback_data=f"forecast_back_{lat}_{lon}"))
        keyboard.add(types.InlineKeyboardButton("🏠 Вернуться в меню", callback_data="back_to_menu"))
        
        bot.send_message(
            call.message.chat.id,
            message_text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data == "forecast_use_saved")
def forecast_use_saved_callback(call):
    """Обработчик использования сохраненной геолокации для прогноза."""
    try:
        user_location = get_user_location(str(call.message.chat.id))
        if user_location:
            lat, lon = user_location
            show_forecast_menu(call.message.chat.id, lat, lon)
            bot.answer_callback_query(call.id)
        else:
            bot.answer_callback_query(call.id, "Сохраненная геолокация не найдена.", show_alert=True)
    except Exception as e:
        bot.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data == "forecast_new_input")
def forecast_new_input_callback(call):
    """Обработчик ввода нового города/геолокации для прогноза."""
    try:
        msg = bot.send_message(
            call.message.chat.id,
            "Введите название города или отправьте геолокацию:",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(msg, process_forecast_input)
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data == "extended_use_saved")
def extended_use_saved_callback(call):
    """Обработчик использования сохраненной геолокации для расширенных данных."""
    try:
        user_location = get_user_location(str(call.message.chat.id))
        if user_location:
            lat, lon = user_location
            
            weather_data = get_weather_by_coordinates(lat, lon)
            city_name = weather_data.get("name", "Неизвестно")
            
            air_components = get_air_pollution(lat, lon)
            air_analysis = analyze_air_pollution(air_components, extended=True)
            
            response = format_extended_weather(weather_data, air_analysis, city_name)
            bot.send_message(call.message.chat.id, response, reply_markup=get_back_to_menu_keyboard(), parse_mode='HTML')
            bot.answer_callback_query(call.id)
        else:
            bot.answer_callback_query(call.id, "Сохраненная геолокация не найдена.", show_alert=True)
    except Exception as e:
        bot.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data == "extended_new_input")
def extended_new_input_callback(call):
    """Обработчик ввода нового города/геолокации для расширенных данных."""
    try:
        msg = bot.send_message(
            call.message.chat.id,
            "Введите название города или отправьте геолокацию:",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(msg, process_extended_data)
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith("forecast_back_"))
def forecast_back_callback(call):
    """Обработчик кнопки 'Назад' в прогнозе."""
    try:
        parts = call.data.split("_")
        lat = float(parts[2])
        lon = float(parts[3])
        show_forecast_menu(call.message.chat.id, lat, lon)
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"Ошибка: {str(e)}", show_alert=True)


@bot.message_handler(func=lambda message: message.text == "📍 Моя геолокация")
def location_handler(message):
    """Обработчик сохранения геолокации."""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("📍 Ввести новую геолокацию", callback_data="location_new_input"))
    keyboard.add(types.InlineKeyboardButton("◀️ Вернуться в меню", callback_data="back_to_menu"))
    bot.send_message(
        message.chat.id,
        "📍 <b>Геолокация</b>",
        reply_markup=keyboard,
        parse_mode='HTML'
    )




@bot.message_handler(func=lambda message: message.text == "⚖️ Сравнить города")
def compare_cities_handler(message):
    """Обработчик сравнения городов."""
    msg = bot.send_message(
        message.chat.id,
        "Введите названия двух городов через запятую (например: Москва, Санкт-Петербург):",
        reply_markup=types.ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(msg, process_city_comparison)


def process_city_comparison(message):
    """Обрабатывает сравнение двух городов."""
    try:
        cities = message.text.strip().split(",")
        if len(cities) != 2:
            bot.send_message(message.chat.id, "Пожалуйста, введите два города через запятую.")
            return
        
        city1 = cities[0].strip()
        city2 = cities[1].strip()
        
        if not city1 or not city2:
            bot.send_message(message.chat.id, "Оба города должны быть указаны.")
            return
        
        # Пытаемся получить погоду для обоих городов
        try:
            weather1 = get_weather_by_city(city1)
        except ValueError as e1:
            error_msg1 = str(e1)
            if "не найден" in error_msg1.lower():
                bot.send_message(
                    message.chat.id,
                    f"❌ Город '{city1}' не найден. Проверьте правильность написания.",
                    reply_markup=get_back_to_menu_keyboard()
                )
                return
            else:
                raise e1
        
        try:
            weather2 = get_weather_by_city(city2)
        except ValueError as e2:
            error_msg2 = str(e2)
            if "не найден" in error_msg2.lower():
                bot.send_message(
                    message.chat.id,
                    f"❌ Город '{city2}' не найден. Проверьте правильность написания.",
                    reply_markup=get_back_to_menu_keyboard()
                )
                return
            else:
                raise e2
        
        response = format_city_comparison(city1, weather1, city2, weather2)
        bot.send_message(message.chat.id, response, reply_markup=get_back_to_menu_keyboard(), parse_mode='HTML')
    except ValueError as e:
        error_msg = str(e)
        bot.send_message(message.chat.id, f"❌ Ошибка: {error_msg}", reply_markup=get_back_to_menu_keyboard())
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Произошла ошибка: {str(e)}", reply_markup=get_back_to_menu_keyboard())


@bot.message_handler(func=lambda message: message.text == "📊 Расширенные данные")
def extended_data_handler(message):
    """Обработчик расширенных данных."""
    user_location = get_user_location(str(message.chat.id))
    
    if user_location:
        # Предлагаем выбрать: использовать сохраненную геолокацию или ввести новую
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("📍 Использовать сохраненную геолокацию", callback_data="extended_use_saved"))
        keyboard.add(types.InlineKeyboardButton("🆕 Ввести новый город/геолокацию", callback_data="extended_new_input"))
        bot.send_message(
            message.chat.id,
            "У вас есть сохраненная геолокация. Выберите действие:",
            reply_markup=keyboard
        )
    else:
        msg = bot.send_message(
            message.chat.id,
            "Введите название города или отправьте геолокацию:",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(msg, process_extended_data)


def process_extended_data(message):
    """Обрабатывает запрос расширенных данных."""
    try:
        if message.location:
            lat = message.location.latitude
            lon = message.location.longitude
            weather_data = get_weather_by_coordinates(lat, lon)
            city_name = weather_data.get("name", "Неизвестно")
        else:
            city = message.text.strip()
            if not city:
                bot.send_message(message.chat.id, "Пожалуйста, введите название города.")
                return
            lat, lon = get_coordinates(city)
            weather_data = get_weather_by_coordinates(lat, lon)
            city_name = city
        
        air_components = get_air_pollution(lat, lon)
        air_analysis = analyze_air_pollution(air_components, extended=True)
        
        response = format_extended_weather(weather_data, air_analysis, city_name)
        bot.send_message(message.chat.id, response, reply_markup=get_back_to_menu_keyboard(), parse_mode='HTML')
    except ValueError as e:
        error_msg = str(e)
        city_name = None
        if message.location:
            pass  # Для геолокации не нужно выводить название
        else:
            city_name = message.text.strip() if message.text else None
        
        if "не найден" in error_msg.lower():
            if city_name:
                bot.send_message(
                    message.chat.id,
                    f"❌ Город '{city_name}' не найден. Попробуйте еще раз.",
                    reply_markup=get_back_to_menu_keyboard()
                )
            else:
                bot.send_message(
                    message.chat.id,
                    "❌ Город с таким названием не найден. Попробуйте еще раз.",
                    reply_markup=get_back_to_menu_keyboard()
                )
        else:
            bot.send_message(message.chat.id, f"❌ Ошибка: {error_msg}", reply_markup=get_back_to_menu_keyboard())
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Произошла ошибка: {str(e)}", reply_markup=get_back_to_menu_keyboard())


@bot.message_handler(func=lambda message: message.text == "🔔 Уведомления")
def notifications_handler(message):
    """Обработчик управления уведомлениями."""
    notifications = load_notifications()
    user_id = str(message.chat.id)
    
    if user_id in notifications and notifications[user_id].get("enabled", False):
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("❌ Отключить уведомления", callback_data="notif_disable"))
        bot.send_message(
            message.chat.id,
            "🔔 Уведомления включены.\nВы будете получать уведомления о погоде каждые 2 часа.",
            reply_markup=keyboard
        )
    else:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("✅ Включить уведомления", callback_data="notif_enable"))
        bot.send_message(
            message.chat.id,
            "🔕 Уведомления отключены.\nНажмите кнопку, чтобы включить уведомления о погоде.",
            reply_markup=keyboard
        )


@bot.callback_query_handler(func=lambda call: call.data == "notif_enable")
def enable_notifications(call):
    """Включает уведомления для пользователя."""
    notifications = load_notifications()
    user_id = str(call.message.chat.id)
    
    user_location = get_user_location(user_id)
    if not user_location:
        bot.answer_callback_query(
            call.id,
            "Сначала сохраните вашу геолокацию через '📍 Моя геолокация'",
            show_alert=True
        )
        return
    
    notifications[user_id] = {
        "enabled": True,
        "last_check": datetime.now().isoformat(),
        "lat": user_location[0],
        "lon": user_location[1]
    }
    save_notifications(notifications)
    
    bot.answer_callback_query(call.id, "Уведомления включены!")
    bot.send_message(
        call.message.chat.id,
        "✅ Уведомления включены!\nВы будете получать уведомления о погоде каждые 2 часа.",
        reply_markup=get_back_to_menu_keyboard()
    )


@bot.callback_query_handler(func=lambda call: call.data == "notif_disable")
def disable_notifications(call):
    """Отключает уведомления для пользователя."""
    notifications = load_notifications()
    user_id = str(call.message.chat.id)
    
    if user_id in notifications:
        notifications[user_id]["enabled"] = False
        save_notifications(notifications)
    
    bot.answer_callback_query(call.id, "Уведомления отключены!")
    bot.send_message(
        call.message.chat.id,
        "❌ Уведомления отключены.",
        reply_markup=get_back_to_menu_keyboard()
    )


def check_notifications():
    """Проверяет и отправляет уведомления пользователям."""
    notifications = load_notifications()
    current_time = datetime.now()
    
    for user_id, notif_data in notifications.items():
        if not notif_data.get("enabled", False):
            continue
        
        last_check_str = notif_data.get("last_check")
        if not last_check_str:
            continue
        
        try:
            last_check = datetime.fromisoformat(last_check_str)
            time_diff = current_time - last_check
            
            # Проверяем каждые 2 часа
            if time_diff >= timedelta(hours=2):
                lat = notif_data.get("lat")
                lon = notif_data.get("lon")
                
                if lat and lon:
                    try:
                        weather_data = get_weather_by_coordinates(lat, lon)
                        city_name = weather_data.get("name", "вашем городе")
                        
                        # Проверяем на дождь или значительные изменения
                        weather_list = weather_data.get("weather", [])
                        description = ""
                        if weather_list and len(weather_list) > 0:
                            description = weather_list[0].get("main", "").lower()
                        
                        temp = weather_data.get("main", {}).get("temp", "N/A")
                        
                        message = f"🔔 <b>Уведомление о погоде</b>\n\n"
                        message += f"📍 {city_name}\n"
                        message += f"🌡️ Температура: {temp}°C\n"
                        
                        if "rain" in description or "drizzle" in description:
                            message += "⚠️ Ожидается дождь! Не забудьте зонт! ☂️"
                        
                        bot.send_message(int(user_id), message, parse_mode='HTML')
                        
                        # Обновляем время последней проверки
                        notif_data["last_check"] = current_time.isoformat()
                        save_notifications(notifications)
                    except Exception:
                        pass  # Игнорируем ошибки при отправке уведомлений
        except Exception:
            pass


def notification_worker():
    """Рабочий поток для проверки уведомлений."""
    while True:
        try:
            check_notifications()
        except Exception:
            pass
        time.sleep(300)  # Проверяем каждые 5 минут


# Универсальный обработчик геолокации удален, т.к. геолокация обрабатывается через process_location_input и process_weather_input


@bot.message_handler(func=lambda message: True)
def default_handler(message):
    """Обработчик всех остальных сообщений."""
    bot.send_message(
        message.chat.id,
        "Используйте кнопки меню или команду /start для начала работы."
    )


if __name__ == "__main__":
    # Запускаем поток для проверки уведомлений
    notification_thread = threading.Thread(target=notification_worker, daemon=True)
    notification_thread.start()
    
    print("Бот запущен...")
    bot.infinity_polling()
