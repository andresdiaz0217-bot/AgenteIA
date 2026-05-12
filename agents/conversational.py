"""
agents/conversational.py

Agente conversacional — núcleo del Sprint 1.

Responsabilidades:
- Recibir mensajes del usuario en lenguaje natural
- Detectar intención (tráfico, clima, análisis combinado)
- Detectar ubicación/zona mencionada
- Invocar las tools necesarias via LangChain
- Generar respuesta en lenguaje natural

Usa Ollama local como LLM (sin costo, sin API key).
"""

import os
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import BaseTool

from prompts.system_prompts import CONVERSATIONAL_AGENT_PROMPT
from tools.traffic_tool import get_traffic_status
from tools.weather_tool import get_weather_status


class ConversationalAgent:
    """
    Agente conversacional con capacidad de usar tools.
    
    En Sprint 1 maneja directamente las tools de tránsito y clima.
    En Sprint 2+, el orquestador (workflow.py) distribuirá trabajo
    a agentes especializados y este agente se enfocará solo en NLP.
    """

    def __init__(self):
        model_name = os.getenv("OLLAMA_MODEL", "llama3.2")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

        self.llm = ChatOllama(
            model=model_name,
            base_url=base_url,
            temperature=0.3,   # respuestas más consistentes para datos factuales
        )

        self.tools: list[BaseTool] = [get_traffic_status, get_weather_status]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.system_message = SystemMessage(content=CONVERSATIONAL_AGENT_PROMPT)

    def invoke(self, messages: list) -> AIMessage:
        """
        Invoca el agente con el historial de mensajes.
        
        Args:
            messages: Lista de mensajes en formato LangChain
                      (HumanMessage, AIMessage, ToolMessage)
        
        Returns:
            AIMessage con la respuesta del agente (puede incluir tool_calls)
        """
        full_messages = [self.system_message] + messages
        response = self.llm_with_tools.invoke(full_messages)
        return response

    def detect_intent(self, text: str) -> str:
        """
        Detección simple de intención para logging y métricas.
        El LLM hace la detección real; esto es solo para observabilidad.
        
        Returns: "trafico" | "clima" | "combinado" | "general"
        """
        text_lower = text.lower()
        
        traffic_keywords = ["tráfico", "trafico", "congestión", "congestion",
                           "vía", "via", "ruta", "carro", "moto", "transporte",
                           "demorar", "demorado", "atasco", "trancón", "trancon",
                           "llego", "llegar", "desde", "hacia", "ir a", "cómo voy",
                           "como voy", "cuánto tardo", "cuanto tardo", "camino",
                           "recorrido", "trayecto", "movilidad", "circular"]
        
        weather_keywords = ["clima", "lluvia", "llueve", "lloviendo", "temperatura",
                           "calor", "frío", "frio", "nublado", "sol", "tormenta",
                           "garúa", "garua", "paraguas", "mojado", "llueve",
                           "va a llover", "está lloviendo", "hace calor", "hace frío",
                           "despejado", "aguacero", "chubasco", "humedad"]
        
        has_traffic = any(kw in text_lower for kw in traffic_keywords)
        has_weather = any(kw in text_lower for kw in weather_keywords)
        
        if has_traffic and has_weather:
            return "combinado"
        elif has_traffic:
            return "trafico"
        elif has_weather:
            return "clima"
        else:
            return "general"