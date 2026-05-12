"""
tools/traffic_tool.py

Sprint 1: datos simulados.
Sprint 2: TomTom Traffic API (gratuito, sin tarjeta, 2500 req/día).
          Registro: https://developer.tomtom.com
          .env → TOMTOM_API_KEY

Migración a Google Maps en el futuro:
  1. Cambiar TOMTOM_API_KEY → GOOGLE_MAPS_API_KEY en .env
  2. Reemplazar el contenido de _fetch_real() con la llamada a Routes API
  3. Todo lo demás del proyecto queda igual.

La interfaz pública (TrafficData, get_traffic_status) nunca cambia.
"""

import os
import random
import httpx
from dataclasses import dataclass
from datetime import datetime
from langchain_core.tools import tool


@dataclass
class TrafficData:
    """Estructura de datos de tránsito. Igual en mock y en real."""
    zone: str
    congestion_level: str        # "bajo", "moderado", "alto", "crítico"
    congestion_score: int        # 0-100
    estimated_delay_minutes: int
    main_incidents: list[str]
    recommended_alternatives: list[str]
    data_source: str             # "mock" | "tomtom" | "google_maps"
    timestamp: str


# ── Coordenadas de zonas conocidas de Medellín ────────────────────────────────
# TomTom Traffic Flow API trabaja con coordenadas, no con nombres de zonas.
# Cuando el usuario pide "El Poblado", buscamos las coordenadas aquí.
# En Sprint 2+, se puede ampliar esta tabla o usar Geocoding API.

ZONE_COORDINATES = {
    "el poblado":       (6.2087,  -75.5659),
    "laureles":         (6.2442,  -75.5902),
    "centro":           (6.2518,  -75.5636),
    "bello":            (6.3329,  -75.5581),
    "envigado":         (6.1752,  -75.5891),
    "itagüí":           (6.1843,  -75.5994),
    "itaguí":           (6.1843,  -75.5994),
    "belén":            (6.2280,  -75.6050),
    "belen":            (6.2280,  -75.6050),
    "robledo":          (6.2760,  -75.6010),
    "autopista sur":    (6.1600,  -75.6050),
    "autopista norte":  (6.3200,  -75.5600),
    "sabaneta":         (6.1514,  -75.6153),
    "la estrella":      (6.1578,  -75.6422),
    "medellín":         (6.2442,  -75.5812),  # centro geográfico
}


def _get_coordinates(zone: str) -> tuple[float, float]:
    """Retorna coordenadas (lat, lon) para una zona. Fallback al centro de Medellín."""
    return ZONE_COORDINATES.get(zone.lower().strip(), ZONE_COORDINATES["medellín"])


def _score_to_level(score: int) -> str:
    """Convierte congestion_score 0-100 a nivel textual."""
    if score < 25:
        return "bajo"
    elif score < 50:
        return "moderado"
    elif score < 75:
        return "alto"
    else:
        return "crítico"


# ── Mock ──────────────────────────────────────────────────────────────────────

_ZONES_MOCK = {
    "el poblado": {
        "congestion_score": 75,
        "estimated_delay_minutes": 18,
        "main_incidents": ["Accidente en Avenida El Poblado con Calle 10", "Obras en Transversal Superior"],
        "recommended_alternatives": ["Usar Avenida Las Vegas", "Tomar Circunvalar hacia el norte"],
    },
    "laureles": {
        "congestion_score": 45,
        "estimated_delay_minutes": 8,
        "main_incidents": ["Tráfico denso en Avenida Laureles hora pico"],
        "recommended_alternatives": ["Circular 76 tiene flujo normal"],
    },
    "centro": {
        "congestion_score": 92,
        "estimated_delay_minutes": 35,
        "main_incidents": ["Cierre parcial Calle 52 por evento", "Metro con retrasos en Línea A"],
        "recommended_alternatives": ["Evitar el centro hasta las 8pm", "Usar Metrocable desde Acevedo"],
    },
    "autopista sur": {
        "congestion_score": 55,
        "estimated_delay_minutes": 12,
        "main_incidents": ["Flujo denso entre Itagüí y La Estrella"],
        "recommended_alternatives": ["Avenida Las Palmas como alternativa hacia el sur"],
    },
    "bello": {
        "congestion_score": 20,
        "estimated_delay_minutes": 3,
        "main_incidents": [],
        "recommended_alternatives": [],
    },
}


def _fetch_mock(zone: str) -> TrafficData:
    zone_key = zone.lower().strip()
    data = _ZONES_MOCK.get(zone_key)

    if not data:
        score = random.randint(20, 70)
        data = {
            "congestion_score": score,
            "estimated_delay_minutes": score // 5,
            "main_incidents": ["Flujo denso reportado" if score >= 50 else "Tráfico normal para la hora"],
            "recommended_alternatives": ["Consultar ruta alternativa"],
        }

    score = data["congestion_score"]
    return TrafficData(
        zone=zone,
        congestion_level=_score_to_level(score),
        congestion_score=score,
        estimated_delay_minutes=data["estimated_delay_minutes"],
        main_incidents=data["main_incidents"],
        recommended_alternatives=data["recommended_alternatives"],
        data_source="mock",
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )


# ── Real: TomTom Traffic Flow API ─────────────────────────────────────────────

def _fetch_real(zone: str) -> TrafficData:
    """
    TomTom Traffic Flow Segment Data API.
    Docs: https://developer.tomtom.com/traffic-api/documentation/traffic-flow/flow-segment-data

    Retorna el "traffic flow" (flujo de tráfico) en el punto de las coordenadas
    de la zona solicitada. El campo clave es `currentSpeed` vs `freeFlowSpeed`
    para calcular la congestión.
    """
    api_key = os.getenv("TOMTOM_API_KEY")
    if not api_key or api_key == "tu_key_aqui":
        raise ValueError("TOMTOM_API_KEY no configurada en .env")

    lat, lon = _get_coordinates(zone)

    # Flow Segment Data: flujo en un punto geográfico
    response = httpx.get(
        f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json",
        params={
            "key": api_key,
            "point": f"{lat},{lon}",
        },
        timeout=10.0,
    )

    if response.status_code == 400:
        raise ValueError(f"Coordenadas inválidas para la zona '{zone}'.")
    if response.status_code == 403:
        raise ValueError("TOMTOM_API_KEY inválida o sin permisos para Traffic API.")
    response.raise_for_status()

    data = response.json().get("flowSegmentData", {})

    # Calcular congestion_score a partir de la relación velocidad actual / velocidad libre
    current_speed = data.get("currentSpeed", 0)
    free_flow_speed = data.get("freeFlowSpeed", 1)

    if free_flow_speed > 0:
        flow_ratio = current_speed / free_flow_speed   # 1.0 = sin congestión, 0.0 = total
        congestion_score = max(0, min(100, int((1 - flow_ratio) * 100)))
    else:
        congestion_score = 50  # valor neutro si no hay datos

    # Estimar delay en minutos proporcional al score
    # (sin datos de ruta completa, es una estimación)
    delay_minutes = int(congestion_score * 0.4)

    # TomTom Flow no retorna incidentes (eso es Traffic Incidents API, Sprint 3+)
    # Por ahora generamos un mensaje descriptivo basado en el score
    congestion_level = _score_to_level(congestion_score)
    if congestion_score < 25:
        incidents = ["Tráfico fluye con normalidad"]
        alternatives = []
    elif congestion_score < 50:
        incidents = ["Flujo moderado, velocidad reducida respecto a condiciones normales"]
        alternatives = ["Considera salir fuera de horas pico"]
    elif congestion_score < 75:
        incidents = ["Congestión alta, velocidad actual significativamente reducida"]
        alternatives = ["Busca rutas alternativas si es posible"]
    else:
        incidents = ["Congestión crítica, tráfico casi detenido en la zona"]
        alternatives = ["Evita la zona o usa transporte público"]

    return TrafficData(
        zone=zone,
        congestion_level=congestion_level,
        congestion_score=congestion_score,
        estimated_delay_minutes=delay_minutes,
        main_incidents=incidents,
        recommended_alternatives=alternatives,
        data_source="tomtom",
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )


# ── Tool pública ──────────────────────────────────────────────────────────────

@tool
def get_traffic_status(zone: str) -> dict:
    """
    Consulta el estado del tráfico en una zona o ruta de Medellín.

    Args:
        zone: Nombre de la zona, barrio o vía a consultar.
              Ejemplos: "El Poblado", "Autopista Sur", "Centro", "Laureles"

    Returns:
        Diccionario con nivel de congestión, incidentes y alternativas.
    """
    api_key = os.getenv("TOMTOM_API_KEY", "")
    use_real = bool(api_key and api_key != "tu_key_aqui")

    try:
        data = _fetch_real(zone) if use_real else _fetch_mock(zone)
    except Exception as e:
        print(f"⚠️  TomTom no disponible ({e}), usando datos mock.")
        data = _fetch_mock(zone)

    return {
        "zone": data.zone,
        "congestion_level": data.congestion_level,
        "congestion_score": data.congestion_score,
        "estimated_delay_minutes": data.estimated_delay_minutes,
        "main_incidents": data.main_incidents,
        "recommended_alternatives": data.recommended_alternatives,
        "data_source": data.data_source,
        "timestamp": data.timestamp,
    }