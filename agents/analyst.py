"""
agents/analyst.py — Sprint 3

Agente analista: correlaciona datos de tránsito y clima para generar insights.
Sprint 1: stub vacío. Se implementa en Sprint 3.

Lógica prevista:
- lluvia + congestión alta → "La lluvia está empeorando el tráfico un ~30%"
- tormenta + hora pico → alerta crítica
- clima despejado + tráfico alto → causa no climática (evento, accidente)
"""


class AnalystAgent:
    """
    Sprint 3: recibe TrafficData + WeatherData y genera AnalysisResult.
    Será un nodo en el grafo LangGraph (workflow.py).
    """

    def invoke(self, traffic_data: dict, weather_data: dict) -> dict:
        raise NotImplementedError("Sprint 3: implementar AnalystAgent")
