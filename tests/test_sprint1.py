"""
tests/test_sprint1.py

Pruebas del Sprint 1.

Cubren:
- Tools: que retornen la estructura correcta
- Intención: que el agente detecte correctamente
- API: que el endpoint /health y /chat respondan bien
- Grafo: que el workflow procese mensajes

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
        
        required_fields = [
            "zone", "congestion_level", "congestion_score",
            "estimated_delay_minutes", "main_incidents",
            "recommended_alternatives", "data_source", "timestamp"
        ]
        for field in required_fields:
            assert field in result, f"Falta campo: {field}"

    def test_congestion_level_valid_values(self):
        from tools.traffic_tool import get_traffic_status
        result = get_traffic_status.invoke({"zone": "Centro"})
        
        valid_levels = {"bajo", "moderado", "alto", "crítico"}
        assert result["congestion_level"] in valid_levels

    def test_congestion_score_range(self):
        from tools.traffic_tool import get_traffic_status
        result = get_traffic_status.invoke({"zone": "Laureles"})
        
        assert 0 <= result["congestion_score"] <= 100

    def test_unknown_zone_returns_data(self):
        from tools.traffic_tool import get_traffic_status
        # Zona no mapeada: debe retornar datos genéricos, no error
        result = get_traffic_status.invoke({"zone": "Zona desconocida XYZ"})
        assert result["zone"] == "Zona desconocida XYZ"
        assert "congestion_level" in result

    def test_data_source_is_mock(self):
        from tools.traffic_tool import get_traffic_status
        result = get_traffic_status.invoke({"zone": "Bello"})
        assert result["data_source"] == "mock"


class TestWeatherTool:
    def test_returns_required_fields(self):
        from tools.weather_tool import get_weather_status
        result = get_weather_status.invoke({"city": "Medellín"})
        
        required_fields = [
            "city", "condition", "temperature_celsius", "humidity_percent",
            "wind_speed_kmh", "visibility_km", "affects_traffic",
            "traffic_impact_reason", "data_source", "timestamp"
        ]
        for field in required_fields:
            assert field in result, f"Falta campo: {field}"

    def test_affects_traffic_is_bool(self):
        from tools.weather_tool import get_weather_status
        result = get_weather_status.invoke({"city": "Medellín"})
        assert isinstance(result["affects_traffic"], bool)

    def test_temperature_reasonable_for_medellin(self):
        from tools.weather_tool import get_weather_status
        # Medellín: entre 12°C y 32°C aproximadamente
        result = get_weather_status.invoke({"city": "Medellín"})
        assert 10 <= result["temperature_celsius"] <= 35

    def test_valid_condition_values(self):
        from tools.weather_tool import get_weather_status
        valid_conditions = {"despejado", "nublado", "lluvia", "tormenta", "garúa"}
        result = get_weather_status.invoke({"city": "Medellín"})
        assert result["condition"] in valid_conditions


# ── Tests de Detección de Intención ──────────────────────────────────────────

class TestIntentDetection:
    def setup_method(self):
        from agents.conversational import ConversationalAgent
        # Mock del LLM para que no necesite Ollama corriendo
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
        assert self.agent.detect_intent(
            "¿La lluvia está afectando el tráfico?"
        ) == "combinado"

    def test_general_intent_fallback(self):
        assert self.agent.detect_intent("Hola, buenos días") == "general"


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

    @patch("api.main.transit_graph")
    def test_chat_endpoint_structure(self, mock_graph):
        """Prueba la estructura del endpoint sin invocar Ollama."""
        from langchain_core.messages import AIMessage
        
        mock_graph.invoke.return_value = {
            "messages": [
                MagicMock(spec=AIMessage, content="El tráfico en El Poblado está alto.", 
                         tool_calls=[], __class__=AIMessage)
            ]
        }
        
        response = self.client.post("/chat", json={
            "message": "¿Cómo está el tráfico en El Poblado?"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "intent" in data
        assert "data_source" in data
