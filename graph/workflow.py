"""
graph/workflow.py

Orquestador central basado en LangGraph.

Sprint 1: grafo simple con un solo agente (conversacional + tools).
Sprint 2: se agregan nodos para agentes de tránsito y clima.
Sprint 3: se agrega nodo analista con lógica de correlación.
Sprint 4: se agrega nodo recomendador y memoria persistente.

La estructura del grafo está diseñada para crecer sin reescrituras.
"""

from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import operator

from agents.conversational import ConversationalAgent


# ── Estado del grafo ──────────────────────────────────────────────────────────
# TypedDict que se pasa entre nodos. Se expande en sprints futuros.

class AgentState(TypedDict):
    # Historial de mensajes (LangChain format)
    messages: Annotated[list, operator.add]
    
    # Sprint 2+: resultados de herramientas individuales
    # traffic_data: dict | None
    # weather_data: dict | None
    
    # Sprint 3+: análisis del agente analista
    # analysis_result: dict | None
    
    # Sprint 4+: contexto de sesión y memoria
    # session_id: str | None
    # user_context: dict | None


# ── Nodos del grafo ───────────────────────────────────────────────────────────

def conversational_node(state: AgentState) -> dict:
    """
    Nodo principal Sprint 1.
    Invoca al agente conversacional que decide qué tools usar.
    """
    agent = ConversationalAgent()
    response = agent.invoke(state["messages"])
    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    """
    Router del grafo: decide si continuar con tool calls o terminar.
    LangGraph usa esta función para determinar la siguiente arista.
    
    Sprint 2+: aquí se pueden agregar rutas hacia agentes especializados.
    """
    last_message = state["messages"][-1]
    
    # Si el último mensaje tiene tool_calls, ir al nodo de tools
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    
    # Si no, la respuesta está completa
    return END


# ── Construcción del grafo ────────────────────────────────────────────────────

def build_graph():
    """
    Construye y compila el grafo LangGraph.
    Se llama una vez al iniciar la aplicación.
    """
    from tools.traffic_tool import get_traffic_status
    from tools.weather_tool import get_weather_status

    tools = [get_traffic_status, get_weather_status]
    tool_node = ToolNode(tools)

    graph = StateGraph(AgentState)

    # Nodos
    graph.add_node("conversational", conversational_node)
    graph.add_node("tools", tool_node)

    # Punto de entrada
    graph.set_entry_point("conversational")

    # Aristas condicionales: después del agente, ¿usar tools o terminar?
    graph.add_conditional_edges(
        "conversational",
        should_continue,
        {"tools": "tools", END: END},
    )

    # Después de ejecutar tools, volver al agente para procesar resultados
    graph.add_edge("tools", "conversational")

    return graph.compile()


# Instancia global del grafo (se crea una sola vez)
transit_graph = build_graph()
