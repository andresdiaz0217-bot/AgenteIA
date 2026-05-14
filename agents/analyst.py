"""
agents/analyst.py — Sprint 3

Agente analista: correlaciona datos de tránsito y clima para generar insights.
Recibe TrafficData + WeatherData del estado del grafo y produce AnalysisResult.

No usa LLM — es lógica determinista basada en reglas.
Esto es intencional: la correlación clima/tráfico es objetiva y no necesita
inferencia del modelo. El LLM entra después para redactar la respuesta.

Sprint 4: el recomendador recibirá AnalysisResult como input.
"""

from dataclasses import dataclass


@dataclass
class AnalysisResult:
    """
    Resultado estructurado del análisis clima + tráfico.
    Este es el contrato que usará el agente recomendador en Sprint 4.
    """
    zone: str
    city: str

    # Nivel de alerta general: "normal", "precaución", "alerta", "crítico"
    alert_level: str

    # ¿El clima está empeorando activamente el tráfico?
    weather_worsening_traffic: bool

    # Estimación del impacto porcentual del clima sobre el tráfico
    weather_impact_percent: int        # 0, 10, 20, 30, 50

    # Causa principal del tráfico: "climática", "no_climática", "mixta", "desconocida"
    congestion_cause: str

    # Insight principal para mostrar al usuario
    main_insight: str

    # Insights secundarios (lista de observaciones adicionales)
    secondary_insights: list[str]

    # Recomendación de acción concreta
    action_recommendation: str

    # Nivel de urgencia: "informativo", "precaución", "urgente"
    urgency: str


# ── Reglas de correlación ─────────────────────────────────────────────────────
# Cada regla recibe traffic_data y weather_data y retorna True si aplica.
# El orden importa: se evalúan de más crítico a menos crítico.

def _es_lluvia_activa(weather: dict) -> bool:
    return weather.get("condition") in ("lluvia", "tormenta", "garúa")


def _es_condicion_critica(weather: dict) -> bool:
    return weather.get("condition") == "tormenta"


def _congestion_alta(traffic: dict) -> bool:
    return traffic.get("congestion_score", 0) >= 60


def _congestion_critica(traffic: dict) -> bool:
    return traffic.get("congestion_score", 0) >= 85


def _visibilidad_reducida(weather: dict) -> bool:
    return weather.get("visibility_km", 10) < 5.0


def _calcular_impacto_clima(weather: dict, traffic: dict) -> int:
    """
    Estima el porcentaje del tráfico atribuible al clima.
    Lógica: si hay lluvia Y congestión alta, parte de esa congestión
    probablemente es por el clima.
    """
    condition = weather.get("condition")
    score = traffic.get("congestion_score", 0)

    if condition == "tormenta":
        return 50 if score >= 60 else 30
    elif condition == "lluvia":
        return 30 if score >= 60 else 20
    elif condition == "garúa":
        return 20 if score >= 60 else 10
    else:
        return 0


# ── Agente analista ───────────────────────────────────────────────────────────

class AnalystAgent:
    """
    Analista de correlación clima/tráfico.
    Recibe los dicts de TrafficData y WeatherData y retorna AnalysisResult.
    """

    def invoke(self, traffic_data: dict, weather_data: dict) -> AnalysisResult:
        zone = traffic_data.get("zone", "zona desconocida")
        city = weather_data.get("city", "Medellín")
        score = traffic_data.get("congestion_score", 0)
        condition = weather_data.get("condition", "despejado")
        affects_traffic = weather_data.get("affects_traffic", False)
        congestion_level = traffic_data.get("congestion_level", "bajo")
        delay = traffic_data.get("estimated_delay_minutes", 0)
        visibility = weather_data.get("visibility_km", 10.0)
        temp = weather_data.get("temperature_celsius", 22.0)

        lluvia_activa = _es_lluvia_activa(weather_data)
        condicion_critica = _es_condicion_critica(weather_data)
        congestion_alta = _congestion_alta(traffic_data)
        congestion_critica = _congestion_critica(traffic_data)
        vis_reducida = _visibilidad_reducida(weather_data)
        impacto_clima = _calcular_impacto_clima(weather_data, traffic_data)

        secondary_insights = []
        weather_worsening = False

        # ── CASO 1: Tormenta + cualquier nivel de tráfico ──────────────────────
        if condicion_critica and congestion_alta:
            alert_level = "crítico"
            weather_worsening = True
            congestion_cause = "mixta"
            urgency = "urgente"
            main_insight = (
                f"Situación crítica en {zone}: tormenta eléctrica con congestión {congestion_level}. "
                f"La tormenta está empeorando el tráfico aproximadamente un {impacto_clima}%."
            )
            action_recommendation = (
                f"Evita salir si es posible. Si debes hacerlo, usa transporte público "
                f"y cuenta con al menos {delay + 15} minutos adicionales de retraso."
            )
            secondary_insights.append("Riesgo de semáforos apagados por la tormenta.")
            secondary_insights.append("Visibilidad crítica: conduce con luces encendidas.")

        elif condicion_critica and not congestion_alta:
            alert_level = "alerta"
            weather_worsening = True
            congestion_cause = "climática"
            urgency = "urgente"
            main_insight = (
                f"Tormenta eléctrica en {city} con tráfico {congestion_level} en {zone}. "
                f"El clima puede deteriorar la situación rápidamente."
            )
            action_recommendation = (
                "Considera postponer el viaje hasta que pase la tormenta. "
                "Si debes salir, hazlo con precaución extrema."
            )
            secondary_insights.append("Las tormentas en Medellín suelen durar entre 30 y 90 minutos.")

        # ── CASO 2: Lluvia + congestión alta ──────────────────────────────────
        elif lluvia_activa and congestion_alta:
            alert_level = "alerta"
            weather_worsening = True
            congestion_cause = "mixta"
            urgency = "precaución"
            main_insight = (
                f"La {condition} está empeorando el tráfico en {zone} aproximadamente un {impacto_clima}%. "
                f"La congestión es {congestion_level} con {delay} minutos de retraso estimado."
            )
            action_recommendation = (
                f"Si puedes esperar 30-45 minutos, el tráfico podría mejorar cuando "
                f"pase la {condition}. Alternativas: {', '.join(traffic_data.get('recommended_alternatives', ['consulta rutas alternativas']))}"
            )
            if vis_reducida:
                secondary_insights.append(f"Visibilidad reducida a {visibility} km: mantén distancia de seguridad.")
            secondary_insights.append("Las vías mojadas aumentan la distancia de frenado.")

        # ── CASO 3: Lluvia moderada + tráfico bajo/moderado ───────────────────
        elif lluvia_activa and not congestion_alta:
            alert_level = "precaución"
            weather_worsening = False
            congestion_cause = "climática" if score > 30 else "normal"
            urgency = "precaución"
            main_insight = (
                f"Hay {condition} en {city} pero el tráfico en {zone} está {congestion_level}. "
                f"El clima no está causando congestión significativa en este momento."
            )
            action_recommendation = (
                "Puedes circular con normalidad pero con precaución. "
                "Activa las luces de posición y mantén distancia de seguridad."
            )
            if vis_reducida:
                secondary_insights.append(f"Visibilidad de {visibility} km: reduce la velocidad.")

        # ── CASO 4: Clima despejado + congestión alta ─────────────────────────
        elif not lluvia_activa and congestion_alta:
            alert_level = "precaución"
            weather_worsening = False
            congestion_cause = "no_climática"
            urgency = "precaución"
            main_insight = (
                f"Congestión {congestion_level} en {zone} con {delay} minutos de retraso. "
                f"El clima está despejado ({temp}°C), la causa es probablemente hora pico, "
                f"eventos o incidentes viales."
            )
            action_recommendation = (
                f"Considera rutas alternativas: {', '.join(traffic_data.get('recommended_alternatives', ['consulta Google Maps']))}"
            )
            secondary_insights.append("Sin factor climático que empeore la situación.")

        # ── CASO 5: Condiciones normales ──────────────────────────────────────
        else:
            alert_level = "normal"
            weather_worsening = False
            congestion_cause = "normal"
            urgency = "informativo"
            main_insight = (
                f"Buenas condiciones en {zone}: tráfico {congestion_level} "
                f"y clima {condition} a {temp}°C. Sin factores de riesgo."
            )
            action_recommendation = "Puedes circular con normalidad."
            secondary_insights.append("Buen momento para desplazarse si tienes planes pendientes.")

        return AnalysisResult(
            zone=zone,
            city=city,
            alert_level=alert_level,
            weather_worsening_traffic=weather_worsening,
            weather_impact_percent=impacto_clima,
            congestion_cause=congestion_cause,
            main_insight=main_insight,
            secondary_insights=secondary_insights,
            action_recommendation=action_recommendation,
            urgency=urgency,
        )

    def to_dict(self, result: AnalysisResult) -> dict:
        """Convierte AnalysisResult a dict para pasar al estado del grafo."""
        return {
            "zone": result.zone,
            "city": result.city,
            "alert_level": result.alert_level,
            "weather_worsening_traffic": result.weather_worsening_traffic,
            "weather_impact_percent": result.weather_impact_percent,
            "congestion_cause": result.congestion_cause,
            "main_insight": result.main_insight,
            "secondary_insights": result.secondary_insights,
            "action_recommendation": result.action_recommendation,
            "urgency": result.urgency,
        }