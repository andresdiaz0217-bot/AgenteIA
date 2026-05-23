"""
tests/test_sprint1.py

Pruebas del proyecto completo (Sprints 1-5).
Ejecución:
    pytest tests/test_sprint1.py -v
"""

import pytest
from unittest.mock import patch, MagicMock


# ── Tests de Tools ────────────────────────────────────────────────────────────

class TestTrafficTool:
    def test_returns_required_fields(self):
        from tools.traffic_tool import get_traffic_status
        result = get_traffic_status.invoke({"zone": "El Poblado"})
        for field in ["zone", "congestion_level", "congestion_score",
                      "estimated_delay_minutes", "main_incidents",
                      "recommended_alternatives", "data_source", "timestamp"]:
            assert field in result, f"Falta campo: {field}"

    def test_congestion_level_valid_values(self):
        from tools.traffic_tool import get_traffic_status
        result = get_traffic_status.invoke({"zone": "Centro"})
        assert result["congestion_level"] in {"bajo", "moderado", "alto", "crítico"}

    def test_congestion_score_range(self):
        from tools.traffic_tool import get_traffic_status
        result = get_traffic_status.invoke({"zone": "Laureles"})
        assert 0 <= result["congestion_score"] <= 100

    def test_unknown_zone_returns_data(self):
        from tools.traffic_tool import get_traffic_status
        result = get_traffic_status.invoke({"zone": "Zona desconocida XYZ"})
        assert result["zone"] == "Zona desconocida XYZ"
        assert "congestion_level" in result

    def test_data_source_present(self):
        from tools.traffic_tool import get_traffic_status
        result = get_traffic_status.invoke({"zone": "Bello"})
        assert result["data_source"] in {"mock", "tomtom", "google_maps"}


class TestWeatherTool:
    def test_returns_required_fields(self):
        from tools.weather_tool import get_weather_status
        result = get_weather_status.invoke({"city": "Medellín"})
        for field in ["city", "condition", "temperature_celsius", "humidity_percent",
                      "wind_speed_kmh", "visibility_km", "affects_traffic",
                      "traffic_impact_reason", "data_source", "timestamp"]:
            assert field in result, f"Falta campo: {field}"

    def test_affects_traffic_is_bool(self):
        from tools.weather_tool import get_weather_status
        result = get_weather_status.invoke({"city": "Medellín"})
        assert isinstance(result["affects_traffic"], bool)

    def test_temperature_reasonable_for_medellin(self):
        from tools.weather_tool import get_weather_status
        result = get_weather_status.invoke({"city": "Medellín"})
        assert 10 <= result["temperature_celsius"] <= 35

    def test_valid_condition_values(self):
        from tools.weather_tool import get_weather_status
        result = get_weather_status.invoke({"city": "Medellín"})
        assert result["condition"] in {"despejado", "nublado", "lluvia", "tormenta", "garúa"}

    def test_data_source_present(self):
        from tools.weather_tool import get_weather_status
        result = get_weather_status.invoke({"city": "Medellín"})
        assert result["data_source"] in {"mock", "openweather"}


# ── Tests de Detección de Intención ──────────────────────────────────────────

class TestIntentDetection:
    def setup_method(self):
        from agents.conversational import ConversationalAgent
        with patch("agents.conversational.ChatOllama"):
            self.agent = ConversationalAgent()

    def test_detects_traffic_intent(self):
        assert self.agent.detect_intent("¿Cómo está el tráfico en Medellín?") == "trafico"
        assert self.agent.detect_intent("Hay trancón en la autopista sur?") == "trafico"
        assert self.agent.detect_intent("¿Cuánto me demoro en llegar?") == "trafico"

    def test_detects_weather_intent(self):
        assert self.agent.detect_intent("¿Está lloviendo en Medellín?") == "clima"
        assert self.agent.detect_intent("¿Cómo está el clima hoy?") == "clima"

    def test_detects_combined_intent(self):
        assert self.agent.detect_intent("¿La lluvia está afectando el tráfico?") == "combinado"

    def test_general_intent_fallback(self):
        assert self.agent.detect_intent("Hola, buenos días") == "general"


# ── Tests del Agente Analista (Sprint 3) ──────────────────────────────────────

class TestAnalystAgent:
    def setup_method(self):
        from agents.analyst import AnalystAgent
        self.agent = AnalystAgent()

    def _make_traffic(self, score=50, level="moderado", zone="El Poblado"):
        return {"zone": zone, "congestion_level": level,
                "congestion_score": score, "estimated_delay_minutes": score // 5,
                "main_incidents": [], "recommended_alternatives": [],
                "data_source": "mock", "timestamp": "2026-01-01 12:00"}

    def _make_weather(self, condition="despejado", affects=False, visibility=10.0):
        return {"city": "Medellín", "condition": condition,
                "temperature_celsius": 22.0, "humidity_percent": 65,
                "wind_speed_kmh": 10.0, "visibility_km": visibility,
                "affects_traffic": affects,
                "traffic_impact_reason": "Lluvia" if affects else "Sin impacto",
                "data_source": "mock", "timestamp": "2026-01-01 12:00"}

    def test_returns_required_fields(self):
        result = self.agent.invoke(self._make_traffic(), self._make_weather())
        d = self.agent.to_dict(result)
        for field in ["zone", "alert_level", "weather_worsening_traffic",
                      "weather_impact_percent", "congestion_cause",
                      "main_insight", "secondary_insights",
                      "action_recommendation", "urgency"]:
            assert field in d, f"Falta campo: {field}"

    def test_lluvia_alta_congestion_is_alerta(self):
        traffic = self._make_traffic(score=75, level="alto")
        weather = self._make_weather(condition="lluvia", affects=True, visibility=4.0)
        result = self.agent.invoke(traffic, weather)
        assert result.alert_level == "alerta"
        assert result.weather_worsening_traffic is True

    def test_despejado_baja_congestion_is_normal(self):
        traffic = self._make_traffic(score=15, level="bajo")
        weather = self._make_weather(condition="despejado", affects=False)
        result = self.agent.invoke(traffic, weather)
        assert result.alert_level == "normal"
        assert result.weather_worsening_traffic is False

    def test_tormenta_congestion_critica_is_critico(self):
        traffic = self._make_traffic(score=90, level="crítico")
        weather = self._make_weather(condition="tormenta", affects=True, visibility=1.5)
        result = self.agent.invoke(traffic, weather)
        assert result.alert_level == "crítico"
        assert result.urgency == "urgente"

    def test_despejado_congestion_alta_causa_no_climatica(self):
        traffic = self._make_traffic(score=80, level="alto")
        weather = self._make_weather(condition="despejado", affects=False)
        result = self.agent.invoke(traffic, weather)
        assert result.congestion_cause == "no_climática"


# ── Tests del Agente Recomendador (Sprint 4) ─────────────────────────────────

class TestRecommenderAgent:
    def setup_method(self):
        from agents.recommender import RecommenderAgent
        self.agent = RecommenderAgent()

    def _make_analysis(self, alert="normal", urgency="informativo",
                       worsening=False, impact=0, cause="normal", zone="Laureles"):
        return {
            "zone": zone, "city": "Medellín",
            "alert_level": alert, "urgency": urgency,
            "weather_worsening_traffic": worsening,
            "weather_impact_percent": impact,
            "congestion_cause": cause,
            "main_insight": "Insight de prueba",
            "secondary_insights": [],
            "action_recommendation": "Recomendación de prueba",
        }

    def test_returns_required_fields(self):
        result = self.agent.invoke(self._make_analysis())
        d = self.agent.to_dict(result)
        for field in ["zone", "recommendation_type", "primary_recommendation",
                      "alternative_routes", "best_departure_time",
                      "mobility_tips", "public_transport_suggestion"]:
            assert field in d, f"Falta campo: {field}"

    def test_critico_recomienda_evitar(self):
        analysis = self._make_analysis(alert="crítico", urgency="urgente",
                                       worsening=True, impact=50)
        result = self.agent.invoke(analysis)
        assert result.recommendation_type == "evitar"

    def test_normal_recomienda_proceder(self):
        result = self.agent.invoke(self._make_analysis(alert="normal"))
        assert result.recommendation_type == "proceder"

    def test_alerta_con_lluvia_recomienda_esperar(self):
        analysis = self._make_analysis(alert="alerta", urgency="precaución",
                                       worsening=True, impact=30)
        result = self.agent.invoke(analysis)
        assert result.recommendation_type == "esperar"


# ── Tests de Memoria de Sesión (Sprint 4) ────────────────────────────────────

class TestSessionMemory:
    def setup_method(self):
        from graph.memory import SessionMemory
        self.memory = SessionMemory()

    def test_starts_empty(self):
        assert not self.memory.has_context()
        ctx = self.memory.get()
        assert ctx["turn_count"] == 0

    def test_updates_zone_from_traffic(self):
        self.memory.update(traffic_data={"zone": "El Poblado", "congestion_score": 75})
        ctx = self.memory.get()
        assert ctx["last_zone"] == "El Poblado"
        assert ctx["turn_count"] == 1

    def test_updates_weather_condition(self):
        self.memory.update(weather_data={"condition": "lluvia"})
        ctx = self.memory.get()
        assert ctx["last_weather_condition"] == "lluvia"

    def test_zones_history_accumulates(self):
        self.memory.update(traffic_data={"zone": "El Poblado", "congestion_score": 40})
        self.memory.update(traffic_data={"zone": "Laureles", "congestion_score": 30})
        ctx = self.memory.get()
        assert "El Poblado" in ctx["zones_history"]
        assert "Laureles" in ctx["zones_history"]

    def test_clear_resets_state(self):
        self.memory.update(traffic_data={"zone": "Centro", "congestion_score": 90})
        self.memory.clear()
        assert not self.memory.has_context()


# ── Tests de FastAPI ──────────────────────────────────────────────────────────

class TestAPI:
    def setup_method(self):
        from fastapi.testclient import TestClient
        from api.main import app
        self.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "tools_available" in data
        assert len(data["tools_available"]) == 4  # traffic, weather, analyst, recommender

    @patch("api.main.transit_graph")
    def test_chat_endpoint_structure(self, mock_graph):
        """Prueba la estructura del endpoint sin invocar Ollama."""
        from langchain_core.messages import AIMessage

        mock_ai = MagicMock()
        mock_ai.content = "El tráfico en El Poblado está moderado."
        mock_ai.__class__ = AIMessage
        mock_ai.tool_calls = []

        mock_graph.invoke.return_value = {
            "messages": [mock_ai],
            "analysis_result": None,
            "recommendation_result": None,
        }

        response = self.client.post("/chat", json={
            "message": "¿Cómo está el tráfico en El Poblado?"
        })

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "intent" in data
        assert "data_source" in data
        assert "sources_used" in data

    @patch("api.main.transit_graph")
    def test_chat_returns_intent(self, mock_graph):
        from langchain_core.messages import AIMessage

        mock_ai = MagicMock()
        mock_ai.content = "Está lloviendo en Medellín."
        mock_ai.__class__ = AIMessage
        mock_ai.tool_calls = []

        mock_graph.invoke.return_value = {
            "messages": [mock_ai],
            "analysis_result": None,
            "recommendation_result": None,
        }

        response = self.client.post("/chat", json={"message": "¿Está lloviendo?"})
        assert response.status_code == 200
        assert response.json()["intent"] in {"trafico", "clima", "combinado", "general"}