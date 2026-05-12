"""
agents/recommender.py — Sprint 4

Agente recomendador: genera sugerencias de rutas y movilidad.
Sprint 1: stub vacío. Se implementa en Sprint 4.

Funcionalidades previstas:
- Sugerir rutas alternativas basadas en congestion_score
- Recomendar horario de salida
- Recordar preferencias del usuario (memoria conversacional)
- Integrar análisis de Sprint 3 para recomendaciones contextuales
"""


class RecommenderAgent:
    """
    Sprint 4: recibe AnalysisResult y genera RecommendationResult.
    Incluirá memoria de sesión con PostgreSQL o in-memory store.
    """

    def invoke(self, analysis_result: dict, user_context: dict | None = None) -> dict:
        raise NotImplementedError("Sprint 4: implementar RecommenderAgent")
