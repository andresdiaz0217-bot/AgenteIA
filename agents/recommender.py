"""
agents/recommender.py — Sprint 4

Agente recomendador: genera sugerencias concretas de rutas y movilidad
basándose en el AnalysisResult del agente analista.

Como el analista, usa lógica determinista — no LLM.
El LLM entra después para redactar la respuesta final.

Sprint 5: las recomendaciones pueden enriquecerse con datos históricos
         y patrones de hora pico almacenados en PostgreSQL.
"""

from dataclasses import dataclass


@dataclass
class RecommendationResult:
    """
    Resultado estructurado del agente recomendador.
    Se pasa al estado del grafo para que el LLM lo redacte.
    """
    zone: str

    # Tipo de recomendación principal
    recommendation_type: str    # "esperar", "ruta_alternativa", "transporte_publico", "proceder", "evitar"

    # Recomendaciones ordenadas por prioridad
    primary_recommendation: str
    alternative_routes: list[str]

    # Sugerencia de horario
    best_departure_time: str    # "ahora", "en 30 min", "en 1 hora", "evita esta hora"

    # Tips adicionales según condiciones
    mobility_tips: list[str]

    # Si aplica transporte público
    public_transport_suggestion: str | None


# ── Rutas alternativas conocidas por zona ────────────────────────────────────
# En Sprint 5 esto puede venir de la base de datos o de la API de rutas.

ZONE_ALTERNATIVES = {
    "el poblado": [
        "Avenida Las Vegas (paralela a Av. El Poblado)",
        "Circunvalar hacia el norte",
        "Transversal Inferior (menos transitada en hora pico)",
    ],
    "laureles": [
        "Circular 76 tiene flujo normal generalmente",
        "Avenida Nutibara como alternativa sur",
        "Carrera 70 hacia el norte",
    ],
    "centro": [
        "Usar Metro Línea A (evita el tráfico completamente)",
        "Metrocable desde Acevedo si vienes del norte",
        "Avenida Oriental como alternativa perimetral",
    ],
    "autopista sur": [
        "Avenida Las Palmas (más lenta pero más fluida)",
        "Carretera a Las Palmas si vas al sur",
        "Circular por Envigado por vías internas",
    ],
    "autopista norte": [
        "Carrera 65 como alternativa paralela",
        "Metro Línea B hacia el norte",
        "Avenida Carabobo en horas no pico",
    ],
    "bello": [
        "Metro Línea A hasta Niquía",
        "Carrera 48 como alternativa",
    ],
    "envigado": [
        "Avenida El Poblado continuando al sur",
        "Carretera a Las Palmas bajando",
        "Metro hasta Envigado y caminar/taxi",
    ],
    "itagüí": [
        "Autopista Sur alternando con vías internas",
        "Metro hasta Itagüí",
    ],
    "sabaneta": [
        "Metro hasta Sabaneta",
        "Avenida Las Vegas continuando al sur",
    ],
}

METRO_ZONES = {"centro", "bello", "autopista norte", "laureles", "envigado", "itagüí", "sabaneta"}


def _get_alternatives(zone: str) -> list[str]:
    return ZONE_ALTERNATIVES.get(zone.lower().strip(),
           ["Consulta rutas alternativas en Google Maps o Waze"])


def _suggest_public_transport(zone: str, urgency: str) -> str | None:
    """Sugiere transporte público cuando la situación lo amerita."""
    zone_lower = zone.lower().strip()
    if urgency == "urgente" or zone_lower in METRO_ZONES:
        metro_tips = {
            "centro": "Metro Línea A, estaciones Parque Berrío o San Antonio",
            "bello": "Metro Línea A hasta Niquía",
            "laureles": "Metro Línea B, estación Suramericana o Estadio",
            "envigado": "Metro Línea A, estación Envigado",
            "itagüí": "Metro Línea A, estación Itagüí",
            "sabaneta": "Metro Línea A, estación Sabaneta",
            "autopista norte": "Metro Línea A hacia Bello o Niquía",
        }
        return metro_tips.get(zone_lower, "Considera usar el Metro o buses del sistema integrado")
    return None


def _get_departure_advice(congestion_score: int, weather_condition: str) -> str:
    """Recomienda cuándo salir basándose en congestión y clima."""
    if weather_condition == "tormenta":
        return "Espera a que pase la tormenta (generalmente 30-90 min en Medellín)"
    elif congestion_score >= 85:
        return "Espera al menos 1 hora si puedes — la congestión es crítica"
    elif congestion_score >= 60:
        return "En 30-45 minutos la situación podría mejorar"
    elif congestion_score >= 40:
        return "Puedes salir ahora, pero considera los horarios pico (7-9am, 5-7pm)"
    else:
        return "Buen momento para salir — tráfico fluido"


class RecommenderAgent:
    """
    Agente recomendador: genera sugerencias concretas de movilidad
    basándose en el AnalysisResult del agente analista.
    """

    def invoke(self, analysis_result: dict, session_context: dict | None = None) -> RecommendationResult:
        zone = analysis_result.get("zone", "Medellín")
        alert_level = analysis_result.get("alert_level", "normal")
        urgency = analysis_result.get("urgency", "informativo")
        congestion_cause = analysis_result.get("congestion_cause", "normal")
        weather_worsening = analysis_result.get("weather_worsening_traffic", False)
        action_recommendation = analysis_result.get("action_recommendation", "")
        weather_impact = analysis_result.get("weather_impact_percent", 0)

        # Obtener score de congestión del contexto de sesión si está disponible
        congestion_score = 0
        weather_condition = "despejado"
        if session_context:
            congestion_score = session_context.get("last_congestion_score", 0)
            weather_condition = session_context.get("last_weather_condition", "despejado")

        alternatives = _get_alternatives(zone)
        public_transport = _suggest_public_transport(zone, urgency)
        departure_advice = _get_departure_advice(congestion_score, weather_condition)
        mobility_tips = []

        # ── Lógica de recomendación según nivel de alerta ─────────────────────

        if alert_level == "crítico":
            rec_type = "evitar"
            primary = (
                f"Evita {zone} en este momento si es posible. "
                f"La situación es crítica{' y el clima la está empeorando' if weather_worsening else ''}."
            )
            mobility_tips.append("Si debes salir, avisa a alguien tu ruta y hora estimada de llegada.")
            mobility_tips.append("Activa las luces de emergencia si quedas varado en tráfico.")
            if weather_worsening:
                mobility_tips.append(f"El clima está contribuyendo un ~{weather_impact}% a la congestión.")

        elif alert_level == "alerta":
            if weather_worsening:
                rec_type = "esperar"
                primary = (
                    f"Te recomendamos esperar antes de dirigirte a {zone}. "
                    f"El clima está empeorando el tráfico activamente (~{weather_impact}% de impacto)."
                )
                mobility_tips.append("Las condiciones mejorarán cuando pase la lluvia.")
                mobility_tips.append("Revisa el pronóstico antes de salir: lluvia en Medellín suele durar 30-90 min.")
            else:
                rec_type = "ruta_alternativa"
                primary = f"Hay congestión alta en {zone}. Considera rutas alternativas."
            mobility_tips.append("Mantén distancia de seguridad aumentada en vías mojadas.")

        elif alert_level == "precaución":
            if congestion_cause == "no_climática":
                rec_type = "ruta_alternativa"
                primary = f"Tráfico moderado-alto en {zone} sin causa climática. Considera alternativas si no es urgente."
            else:
                rec_type = "proceder"
                primary = f"Puedes moverte por {zone} con precaución. {action_recommendation}"
            mobility_tips.append("Conduce a velocidad reducida si hay humedad en las vías.")

        else:  # normal
            rec_type = "proceder"
            primary = f"Buenas condiciones en {zone}. Puedes circular con normalidad."
            mobility_tips.append("Buen momento para aprovechar y moverse por la ciudad.")

        return RecommendationResult(
            zone=zone,
            recommendation_type=rec_type,
            primary_recommendation=primary,
            alternative_routes=alternatives if rec_type in ("ruta_alternativa", "evitar", "esperar") else [],
            best_departure_time=departure_advice,
            mobility_tips=mobility_tips,
            public_transport_suggestion=public_transport,
        )

    def to_dict(self, result: RecommendationResult) -> dict:
        return {
            "zone": result.zone,
            "recommendation_type": result.recommendation_type,
            "primary_recommendation": result.primary_recommendation,
            "alternative_routes": result.alternative_routes,
            "best_departure_time": result.best_departure_time,
            "mobility_tips": result.mobility_tips,
            "public_transport_suggestion": result.public_transport_suggestion,
        }
