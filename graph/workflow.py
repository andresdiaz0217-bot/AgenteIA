"""
graph/workflow.py

Orquestador central basado en LangGraph.

Sprint 1: grafo simple — conversacional + tools.
Sprint 2: APIs reales en tools (sin cambios en el grafo).
Sprint 3: se agrega analyst_node con lógica de correlación clima/tráfico.
Sprint 4: se agrega recommender_node y memoria persistente.

Flujo Sprint 3:
  conversational → tools → analyst (si hay ambos datos) → conversational → END
                         ↘ conversational (si solo hay un tipo de datos) → END
"""

import json
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import operator

from agents.conversational import ConversationalAgent


# ── Estado del grafo ──────────────────────────────────────────────────────────

class AgentState(TypedDict):
    # Historial de mensajes (LangChain format)
    messages: Annotated[list, operator.add]

    # Sprint 3: datos extraídos de los ToolMessages para el analista
    traffic_data: dict | None
    weather_data: dict | None

    # Sprint 3: resultado del agente analista
    analysis_result: dict | None

    # Sprint 4: contexto de sesión y memoria
    # session_id: str | None
    # user_context: dict | None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_tool_results(messages: list) -> tuple[dict | None, dict | None]:
    """
    Recorre los mensajes y extrae los resultados de traffic y weather tools.
    Los ToolMessages contienen el JSON retornado por cada tool.
    """
    from langchain_core.messages import ToolMessage

    traffic_data = None
    weather_data = None

    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        try:
            content = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
        except (json.JSONDecodeError, TypeError):
            continue

        # Identificar por campos únicos de cada tool
        if "congestion_level" in content:
            traffic_data = content
        elif "condition" in content and "temperature_celsius" in content:
            weather_data = content

    return traffic_data, weather_data


# ── Nodos del grafo ───────────────────────────────────────────────────────────

def conversational_node(state: AgentState) -> dict:
    """
    Nodo conversacional.
    Sprint 3: si hay analysis_result en el estado, lo inyecta en el contexto
    para que el LLM redacte la respuesta final basada en el análisis.
    """
    from langchain_core.messages import HumanMessage, SystemMessage
    from prompts.system_prompts import CONVERSATIONAL_AGENT_PROMPT, ANALYST_CONTEXT_PROMPT

    agent = ConversationalAgent()
    messages = state["messages"]
    analysis = state.get("analysis_result")

    # Si hay análisis disponible, agregar contexto al final del historial
    if analysis:
        analysis_context = ANALYST_CONTEXT_PROMPT.format(
            alert_level=analysis["alert_level"],
            main_insight=analysis["main_insight"],
            secondary_insights="\n- ".join(analysis["secondary_insights"]),
            action_recommendation=analysis["action_recommendation"],
            urgency=analysis["urgency"],
            weather_worsening=analysis["weather_worsening_traffic"],
            weather_impact=analysis["weather_impact_percent"],
            congestion_cause=analysis["congestion_cause"],
        )
        # Inyectamos el análisis como un mensaje de sistema adicional
        from langchain_core.messages import SystemMessage
        messages = messages + [SystemMessage(content=analysis_context)]

    response = agent.invoke(messages)
    return {
        "messages": [response],
        # Limpiar el análisis después de usarlo para no repetirlo en el próximo turno
        "analysis_result": None,
    }


def tools_node_wrapper(state: AgentState) -> dict:
    """
    Wrapper del ToolNode que además extrae los datos para el analista.
    Ejecuta las tools y actualiza traffic_data / weather_data en el estado.
    """
    from tools.traffic_tool import get_traffic_status
    from tools.weather_tool import get_weather_status

    tools = [get_traffic_status, get_weather_status]
    tool_node = ToolNode(tools)

    # Ejecutar las tools
    result = tool_node.invoke(state)
    new_messages = result.get("messages", [])

    # Extraer resultados del tool para el analista
    all_messages = state["messages"] + new_messages
    traffic_data, weather_data = _extract_tool_results(all_messages)

    return {
        "messages": new_messages,
        "traffic_data": traffic_data or state.get("traffic_data"),
        "weather_data": weather_data or state.get("weather_data"),
    }


def analyst_node(state: AgentState) -> dict:
    """
    Nodo analista: correlaciona clima y tráfico y genera AnalysisResult.
    Solo se ejecuta cuando hay AMBOS datos disponibles en el estado.
    """
    from agents.analyst import AnalystAgent

    traffic_data = state.get("traffic_data")
    weather_data = state.get("weather_data")

    agent = AnalystAgent()
    result = agent.invoke(traffic_data, weather_data)

    return {
        "analysis_result": agent.to_dict(result),
        # Limpiar datos usados para no acumularlos entre turnos
        "traffic_data": None,
        "weather_data": None,
    }


# ── Routers ───────────────────────────────────────────────────────────────────

def after_conversational(state: AgentState) -> str:
    """
    Después del nodo conversacional:
    - Si el LLM quiere usar tools → ir a tools
    - Si no → terminar
    """
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


def after_tools(state: AgentState) -> str:
    """
    Después de ejecutar tools:
    - Si tenemos AMBOS datos (tráfico + clima) → ir al analista
    - Si solo tenemos uno → volver al conversacional directamente
    """
    has_traffic = state.get("traffic_data") is not None
    has_weather = state.get("weather_data") is not None

    if has_traffic and has_weather:
        return "analyst"
    return "conversational"


# ── Construcción del grafo ────────────────────────────────────────────────────

def build_graph():
    """Construye y compila el grafo LangGraph para Sprint 3."""

    graph = StateGraph(AgentState)

    # Nodos
    graph.add_node("conversational", conversational_node)
    graph.add_node("tools", tools_node_wrapper)
    graph.add_node("analyst", analyst_node)

    # Punto de entrada
    graph.set_entry_point("conversational")

    # Aristas desde conversacional
    graph.add_conditional_edges(
        "conversational",
        after_conversational,
        {"tools": "tools", END: END},
    )

    # Aristas desde tools: ¿ir al analista o directo al conversacional?
    graph.add_conditional_edges(
        "tools",
        after_tools,
        {"analyst": "analyst", "conversational": "conversational"},
    )

    # Después del analista siempre vuelve al conversacional para redactar
    graph.add_edge("analyst", "conversational")

    return graph.compile()


# Estado inicial por defecto
def initial_state(user_message: str) -> AgentState:
    """Crea el estado inicial para una nueva consulta."""
    from langchain_core.messages import HumanMessage
    return {
        "messages": [HumanMessage(content=user_message)],
        "traffic_data": None,
        "weather_data": None,
        "analysis_result": None,
    }


# Instancia global del grafo
transit_graph = build_graph()