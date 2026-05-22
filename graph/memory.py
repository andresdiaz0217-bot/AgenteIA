"""
graph/memory.py — Sprint 4

Memoria de sesión en RAM.
Guarda el contexto de la conversación actual para que el agente
pueda responder preguntas de seguimiento coherentemente.

Sprint 5: reemplazar SessionMemory por una implementación con PostgreSQL.
          La interfaz (get, update, clear) no cambiará.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SessionContext:
    """
    Contexto que se preserva entre turnos de una sesión.
    """
    # Última zona consultada por el usuario
    last_zone: str | None = None

    # Última condición climática observada
    last_weather_condition: str | None = None

    # Último score de congestión observado
    last_congestion_score: int = 0

    # Última recomendación dada al usuario
    last_recommendation_type: str | None = None

    # Historial de zonas consultadas en esta sesión (últimas 5)
    zones_history: list[str] = field(default_factory=list)

    # Timestamp de la última actualización
    last_updated: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))

    # Número de turnos en esta sesión
    turn_count: int = 0


class SessionMemory:
    """
    Store de memoria en RAM para una sesión.

    Uso:
        memory = SessionMemory()
        memory.update(traffic_data=..., weather_data=..., recommendation=...)
        context = memory.get()

    Sprint 5: esta clase se reemplaza por una implementación con SQLAlchemy + PostgreSQL.
    La interfaz pública (get, update, clear) se mantiene idéntica.
    """

    def __init__(self):
        self._context = SessionContext()

    def get(self) -> dict:
        """Retorna el contexto actual como dict para inyectar en el estado del grafo."""
        return {
            "last_zone": self._context.last_zone,
            "last_weather_condition": self._context.last_weather_condition,
            "last_congestion_score": self._context.last_congestion_score,
            "last_recommendation_type": self._context.last_recommendation_type,
            "zones_history": self._context.zones_history.copy(),
            "turn_count": self._context.turn_count,
        }

    def update(
        self,
        traffic_data: dict | None = None,
        weather_data: dict | None = None,
        recommendation: dict | None = None,
    ) -> None:
        """Actualiza la memoria con los datos del turno actual."""
        self._context.turn_count += 1
        self._context.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M")

        if traffic_data:
            zone = traffic_data.get("zone")
            if zone:
                self._context.last_zone = zone
                # Mantener historial de últimas 5 zonas
                if zone not in self._context.zones_history:
                    self._context.zones_history.append(zone)
                    if len(self._context.zones_history) > 5:
                        self._context.zones_history.pop(0)
            self._context.last_congestion_score = traffic_data.get("congestion_score", 0)

        if weather_data:
            self._context.last_weather_condition = weather_data.get("condition")

        if recommendation:
            self._context.last_recommendation_type = recommendation.get("recommendation_type")

    def clear(self) -> None:
        """Reinicia la memoria (nueva sesión)."""
        self._context = SessionContext()

    def has_context(self) -> bool:
        """True si hay al menos un turno previo con datos."""
        return self._context.turn_count > 0

    def summary(self) -> str:
        """Resumen legible del contexto para debugging."""
        ctx = self._context
        if not self.has_context():
            return "Sin contexto previo en esta sesión."
        return (
            f"Turno {ctx.turn_count} | "
            f"Última zona: {ctx.last_zone or 'N/A'} | "
            f"Clima: {ctx.last_weather_condition or 'N/A'} | "
            f"Congestión: {ctx.last_congestion_score} | "
            f"Zonas visitadas: {', '.join(ctx.zones_history)}"
        )


# Instancia global de memoria para la sesión actual del CLI
# La API FastAPI creará una instancia por sesión (Sprint 5)
session_memory = SessionMemory()
