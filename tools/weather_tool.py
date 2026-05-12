"""
tools/weather_tool.py

Sprint 1: datos simulados.
Sprint 2: OpenWeatherMap API (tier gratuito, 1000 calls/día).
          Registro: https://openweathermap.org/api
          .env → OPENWEATHER_API_KEY

Migración futura: solo tocar _fetch_real().
La interfaz pública nunca cambia.
"""

import os
import random
import httpx
from dataclasses import dataclass
from datetime import datetime
from langchain_core.tools import tool


@dataclass
class WeatherData:
    """Estructura de datos climáticos. Igual en mock y en real."""
    city: str
    condition: str
    temperature_celsius: float
    humidity_percent: int
    wind_speed_kmh: float
    visibility_km: float
    affects_traffic: bool
    traffic_impact_reason: str
    data_source: str            # "mock" | "openweather"
    timestamp: str


# ── Mapeo de códigos OpenWeatherMap → condición normalizada ───────────────────

def _map_owm_condition(weather_id: int, description: str) -> tuple[str, bool, str]:
    """
    Convierte el código numérico de OWM a nuestra condición normalizada.
    Referencia: https://openweathermap.org/weather-conditions
    Retorna: (condition, affects_traffic, traffic_impact_reason)
    """
    if 200 <= weather_id < 300:
        return ("tormenta", True,
                "Tormenta eléctrica: visibilidad crítica, posibles cierres viales y semáforos apagados.")
    elif 300 <= weather_id < 400:
        return ("garúa", True,
                "Garúa hace las vías resbaladizas. Aumenta accidentalidad en curvas.")
    elif 500 <= weather_id < 600:
        if weather_id >= 502:
            return ("tormenta", True,
                    "Lluvia intensa: visibilidad muy reducida y alto riesgo de accidentes.")
        return ("lluvia", True,
                "Lluvia reduce visibilidad y aumenta tiempos de frenado. Se esperan retrasos del 20-30%.")
    elif 600 <= weather_id < 700:
        return ("nublado", False, "Clima frío sin impacto significativo en la movilidad.")
    elif 700 <= weather_id < 800:
        return ("nublado", True, f"Visibilidad reducida por {description}. Conduce con precaución.")
    elif weather_id == 800:
        return ("despejado", False, "Sin impacto climático en la movilidad.")
    else:
        return ("nublado", False, "Clima nublado sin impacto significativo.")


# ── Mock ──────────────────────────────────────────────────────────────────────

_MEDELLIN_CONDITIONS = [
    {"condition": "despejado", "temperature_celsius": 27.0, "humidity_percent": 55,
     "wind_speed_kmh": 8.0, "visibility_km": 10.0, "affects_traffic": False,
     "traffic_impact_reason": "Sin impacto climático en la movilidad."},
    {"condition": "nublado", "temperature_celsius": 22.0, "humidity_percent": 72,
     "wind_speed_kmh": 12.0, "visibility_km": 8.0, "affects_traffic": False,
     "traffic_impact_reason": "Clima nublado sin impacto significativo."},
    {"condition": "lluvia", "temperature_celsius": 18.0, "humidity_percent": 88,
     "wind_speed_kmh": 15.0, "visibility_km": 4.0, "affects_traffic": True,
     "traffic_impact_reason": "Lluvia reduce visibilidad y aumenta tiempos de frenado. Se esperan retrasos del 20-30%."},
    {"condition": "tormenta", "temperature_celsius": 15.0, "humidity_percent": 95,
     "wind_speed_kmh": 35.0, "visibility_km": 1.5, "affects_traffic": True,
     "traffic_impact_reason": "Tormenta eléctrica: visibilidad crítica, posibles cierres viales y semáforos apagados."},
    {"condition": "garúa", "temperature_celsius": 20.0, "humidity_percent": 80,
     "wind_speed_kmh": 10.0, "visibility_km": 6.0, "affects_traffic": True,
     "traffic_impact_reason": "Garúa hace las vías resbaladizas. Aumenta accidentalidad en curvas."},
]


def _fetch_mock(city: str) -> WeatherData:
    weights = [35, 25, 28, 5, 7]
    condition_data = random.choices(_MEDELLIN_CONDITIONS, weights=weights, k=1)[0]
    return WeatherData(
        city=city, **condition_data,
        data_source="mock",
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )


# ── Real: OpenWeatherMap ──────────────────────────────────────────────────────

def _fetch_real(city: str) -> WeatherData:
    """
    OpenWeatherMap Current Weather API.
    Docs: https://openweathermap.org/current
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key or api_key == "tu_key_aqui":
        raise ValueError("OPENWEATHER_API_KEY no configurada en .env")

    response = httpx.get(
        "https://api.openweathermap.org/data/2.5/weather",
        params={"q": f"{city},CO", "appid": api_key, "units": "metric", "lang": "es"},
        timeout=10.0,
    )

    if response.status_code == 401:
        raise ValueError("OPENWEATHER_API_KEY inválida.")
    if response.status_code == 404:
        raise ValueError(f"Ciudad '{city}' no encontrada.")
    response.raise_for_status()

    data = response.json()
    weather_id = data["weather"][0]["id"]
    description = data["weather"][0]["description"]
    condition, affects_traffic, impact_reason = _map_owm_condition(weather_id, description)

    visibility_km = min(data.get("visibility", 10000) / 1000, 10.0)
    wind_kmh = round(data.get("wind", {}).get("speed", 0) * 3.6, 1)

    return WeatherData(
        city=city,
        condition=condition,
        temperature_celsius=round(data["main"]["temp"], 1),
        humidity_percent=data["main"]["humidity"],
        wind_speed_kmh=wind_kmh,
        visibility_km=visibility_km,
        affects_traffic=affects_traffic,
        traffic_impact_reason=impact_reason,
        data_source="openweather",
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )


# ── Tool pública ──────────────────────────────────────────────────────────────

@tool
def get_weather_status(city: str = "Medellín") -> dict:
    """
    Consulta las condiciones climáticas actuales en una ciudad.

    Args:
        city: Ciudad a consultar. Por defecto "Medellín".

    Returns:
        Diccionario con condición climática, temperatura, humedad
        y si el clima está afectando la movilidad.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY", "")
    use_real = bool(api_key and api_key != "tu_key_aqui")

    try:
        data = _fetch_real(city) if use_real else _fetch_mock(city)
    except Exception as e:
        print(f"⚠️  OpenWeatherMap no disponible ({e}), usando datos mock.")
        data = _fetch_mock(city)

    return {
        "city": data.city,
        "condition": data.condition,
        "temperature_celsius": data.temperature_celsius,
        "humidity_percent": data.humidity_percent,
        "wind_speed_kmh": data.wind_speed_kmh,
        "visibility_km": data.visibility_km,
        "affects_traffic": data.affects_traffic,
        "traffic_impact_reason": data.traffic_impact_reason,
        "data_source": data.data_source,
        "timestamp": data.timestamp,
    }