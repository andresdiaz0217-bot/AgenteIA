"""
api/main.py

Backend FastAPI del agente de tránsito.
Sprint 5: sistema completo con todos los agentes integrados.
"""

import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

load_dotenv()

# ── Import a nivel de módulo para que los mocks de tests funcionen ────────────
from graph.workflow import transit_graph, build_initial_state


# ── Modelos de request/response ───────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    intent: str
    sources_used: list[str]
    data_source: str


class HealthResponse(BaseModel):
    status: str
    model: str
    sprint: str
    tools_available: list[str]


# ── Lifecycle ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚦 Transit Agent arrancando...")
    print(f"   Modelo: {os.getenv('OLLAMA_MODEL', 'llama3.2')}")
    print(f"   Ollama URL: {os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}")
    print(f"   Sprint: 5 — Sistema multiagente completo")
    yield
    print("🛑 Transit Agent detenido.")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Transit Agent API",
    description="Agente de IA para información de tránsito en tiempo real — Medellín",
    version="1.0.0-sprint5",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health():
    """Estado del sistema y herramientas disponibles."""
    weather_src = "OpenWeatherMap" if os.getenv("OPENWEATHER_API_KEY", "tu_key_aqui") != "tu_key_aqui" else "mock"
    traffic_src = "TomTom" if os.getenv("TOMTOM_API_KEY", "tu_key_aqui") != "tu_key_aqui" else "mock"
    return HealthResponse(
        status="ok",
        model=os.getenv("OLLAMA_MODEL", "llama3.2"),
        sprint="5 - Sistema multiagente completo",
        tools_available=[
            f"get_traffic_status ({traffic_src})",
            f"get_weather_status ({weather_src})",
            "analyst_agent",
            "recommender_agent",
        ],
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Endpoint principal: recibe una pregunta y retorna respuesta del agente.
    El grafo decide automáticamente qué agentes y tools invocar.
    """
    from agents.conversational import ConversationalAgent

    try:
        agent = ConversationalAgent()
        intent = agent.detect_intent(request.message)

        initial_state = build_initial_state(request.message)
        result = transit_graph.invoke(initial_state)
        messages = result["messages"]

        final_response = ""
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                final_response = msg.content
                break

        if not final_response:
            raise HTTPException(status_code=500, detail="El agente no generó respuesta")

        sources_used = []
        for msg in messages:
            if isinstance(msg, ToolMessage):
                sources_used.append(msg.name if hasattr(msg, "name") else "tool")

        data_source = "real" if sources_used else "llm"

        return ChatResponse(
            response=final_response,
            intent=intent,
            sources_used=list(set(sources_used)),
            data_source=data_source,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=os.getenv("DEBUG", "true").lower() == "true",
    )