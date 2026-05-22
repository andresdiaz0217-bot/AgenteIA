"""
graph/workflow.py

Orquestador central basado en LangGraph — Sprint 4.

Flujo completo:
  conversational → tools → analyst → recommender → conversational → END
                         ↘ (un solo tool) → conversational → END

Novedades Sprint 4:
  - recommender_node después del analista
  - SessionMemory para contexto entre turnos
  - El contexto de sesión enriquece las recomendaciones
"""

import json
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
import operator

from agents.conversational import ConversationalAgent
from graph.memory import session_memory


# ── Estado del grafo ──────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]

    # Datos de tools (Sprint 3)
    traffic_data: dict | None
    weather_data: dict | None

    # Análisis (Sprint 3)
    analysis_result: dict | None

    # Recomendación (Sprint 4)
    recommendation_result: dict | None

    # Contexto de sesión (Sprint 4)
    session_context: dict | None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_tool_results(messages: list) -> tuple[dict | None, dict | None]:
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

        if "congestion_level" in content:
            traffic_data = content
        elif "condition" in content and "temperature_celsius" in content:
            weather_data = content

    return traffic_data, weather_data


# ── Nodos del grafo ───────────────────────────────────────────────────────────

def conversational_node(state: AgentState) -> dict:
    """
    Nodo conversacional.
    Sprint 4: usa el contexto de sesión para respuestas de seguimiento,
    y combina análisis + recomendación en el prompt final.
    """
    from langchain_core.messages import SystemMessage
    from prompts.system_prompts import (
        ANALYST_CONTEXT_PROMPT,
        RECOMMENDER_CONTEXT_PROMPT,
        SESSION_CONTEXT_PROMPT,
    )

    agent = ConversationalAgent()
    messages = list(state["messages"])
    analysis = state.get("analysis_result")
    recommendation = state.get("recommendation_result")
    session_ctx = state.get("session_context") or {}

    # Inyectar contexto de sesión si hay turnos previos
    if session_ctx.get("turn_count", 0) > 0:
        session_prompt = SESSION_CONTEXT_PROMPT.format(
            last_zone=session_ctx.get("last_zone") or "ninguna",
            last_weather=session_ctx.get("last_weather_condition") or "desconocido",
            last_congestion=session_ctx.get("last_congestion_score", 0),
            zones_history=", ".join(session_ctx.get("zones_history", [])) or "ninguna",
            turn_count=session_ctx.get("turn_count", 0),
        )
        messages = messages + [SystemMessage(content=session_prompt)]

    # Inyectar análisis si existe
    if analysis:
        analysis_prompt = ANALYST_CONTEXT_PROMPT.format(
            alert_level=analysis["alert_level"],
            main_insight=analysis["main_insight"],
            secondary_insights="\n- ".join(analysis["secondary_insights"]),
            action_recommendation=analysis["action_recommendation"],
            urgency=analysis["urgency"],
            weather_worsening=analysis["weather_worsening_traffic"],
            weather_impact=analysis["weather_impact_percent"],
            congestion_cause=analysis["congestion_cause"],
        )
        messages = messages + [SystemMessage(content=analysis_prompt)]

    # Inyectar recomendación si existe
    if recommendation:
        rec_prompt = RECOMMENDER_CONTEXT_PROMPT.format(
            recommendation_type=recommendation["recommendation_type"],
            primary_recommendation=recommendation["primary_recommendation"],
            alternative_routes="\n- ".join(recommendation["alternative_routes"]) or "ninguna",
            best_departure_time=recommendation["best_departure_time"],
            mobility_tips="\n- ".join(recommendation["mobility_tips"]) or "ninguno",
            public_transport=recommendation["public_transport_suggestion"] or "no aplica",
        )
        messages = messages + [SystemMessage(content=rec_prompt)]

    response = agent.invoke(messages)
    return {
        "messages": [response],
        "analysis_result": None,
        "recommendation_result": None,
    }


def tools_node_wrapper(state: AgentState) -> dict:
    from tools.traffic_tool import get_traffic_status
    from tools.weather_tool import get_weather_status
    from langgraph.prebuilt import ToolNode

    tools = [get_traffic_status, get_weather_status]
    tool_node = ToolNode(tools)

    result = tool_node.invoke(state)
    new_messages = result.get("messages", [])

    all_messages = state["messages"] + new_messages
    traffic_data, weather_data = _extract_tool_results(all_messages)

    return {
        "messages": new_messages,
        "traffic_data": traffic_data or state.get("traffic_data"),
        "weather_data": weather_data or state.get("weather_data"),
    }


def analyst_node(state: AgentState) -> dict:
    from agents.analyst import AnalystAgent

    agent = AnalystAgent()
    result = agent.invoke(state["traffic_data"], state["weather_data"])

    return {
        "analysis_result": agent.to_dict(result),
        "traffic_data": None,
        "weather_data": None,
    }


def recommender_node(state: AgentState) -> dict:
    """
    Nodo recomendador — Sprint 4.
    Recibe el AnalysisResult y el contexto de sesión,
    genera RecommendationResult y actualiza la memoria.
    """
    from agents.recommender import RecommenderAgent

    analysis = state.get("analysis_result")
    session_ctx = state.get("session_context")

    agent = RecommenderAgent()
    result = agent.invoke(analysis, session_ctx)
    rec_dict = agent.to_dict(result)

    # Actualizar memoria de sesión con los datos de este turno
    # Recuperamos traffic/weather del análisis para guardar en memoria
    session_memory.update(
        traffic_data={
            "zone": analysis.get("zone"),
            "congestion_score": int(analysis.get("weather_impact_percent", 0)),
        },
        weather_data={
            "condition": "lluvia" if analysis.get("weather_worsening_traffic") else "despejado",
        },
        recommendation=rec_dict,
    )

    return {
        "recommendation_result": rec_dict,
        "session_context": session_memory.get(),
    }


# ── Routers ───────────────────────────────────────────────────────────────────

def after_conversational(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


def after_tools(state: AgentState) -> str:
    has_traffic = state.get("traffic_data") is not None
    has_weather = state.get("weather_data") is not None

    if has_traffic and has_weather:
        return "analyst"
    return "conversational"


# ── Construcción del grafo ────────────────────────────────────────────────────

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("conversational", conversational_node)
    graph.add_node("tools", tools_node_wrapper)
    graph.add_node("analyst", analyst_node)
    graph.add_node("recommender", recommender_node)

    graph.set_entry_point("conversational")

    graph.add_conditional_edges(
        "conversational",
        after_conversational,
        {"tools": "tools", END: END},
    )

    graph.add_conditional_edges(
        "tools",
        after_tools,
        {"analyst": "analyst", "conversational": "conversational"},
    )

    # analyst → recommender → conversational
    graph.add_edge("analyst", "recommender")
    graph.add_edge("recommender", "conversational")

    return graph.compile()


def build_initial_state(user_message: str) -> AgentState:
    """Estado inicial con contexto de sesión actual."""
    from langchain_core.messages import HumanMessage
    return {
        "messages": [HumanMessage(content=user_message)],
        "traffic_data": None,
        "weather_data": None,
        "analysis_result": None,
        "recommendation_result": None,
        "session_context": session_memory.get(),
    }


transit_graph = build_graph()
