"""
api/main.py

Backend FastAPI del agente de tránsito.

Sprint 1: endpoint /chat funcional con agente conversacional.
Sprint 2+: se agregan endpoints para datos en tiempo real, historial, etc.
"""

import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

load_dotenv()


# ── Modelos de request/response ───────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None  # Sprint 4: usado para memoria persistente


class ChatResponse(BaseModel):
    response: str
    intent: str           # tráfico | clima | combinado | general
    sources_used: list[str]   # ["traffic_tool", "weather_tool"] para transparencia
    data_source: str      # "mock" en S1, "real" en S2+


class HealthResponse(BaseModel):
    status: str
    model: str
    sprint: str
    tools_available: list[str]


# ── Lifecycle ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializar recursos al arrancar la app."""
    print("🚦 Transit Agent arrancando...")
    print(f"   Modelo: {os.getenv('OLLAMA_MODEL', 'llama3.2')}")
    print(f"   Ollama URL: {os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}")
    print(f"   Sprint: 1 — Agente conversacional con datos mock")
    yield
    print(" Transit Agent detenido.")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Transit Agent API",
    description="Agente de IA para información de tránsito en tiempo real — Medellín",
    version="1.0.0-sprint1",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Sprint 5: restringir al dominio del frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health():
    """Estado del sistema y herramientas disponibles."""
    return HealthResponse(
        status="ok",
        model=os.getenv("OLLAMA_MODEL", "llama3.2"),
        sprint="1 - Agente conversacional",
        tools_available=["get_traffic_status (mock)", "get_weather_status (mock)"],
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Endpoint principal: recibe una pregunta y retorna respuesta del agente.
    
    El agente decide automáticamente qué tools usar basándose en la pregunta.
    """
    from graph.workflow import transit_graph
    from agents.conversational import ConversationalAgent

    try:
        # Detectar intención para el response (el LLM hace la detección real)
        agent = ConversationalAgent()
        intent = agent.detect_intent(request.message)

        # Invocar el grafo LangGraph con estado Sprint 4
        from graph.workflow import build_initial_state
        initial_state = build_initial_state(request.message)
        
        result = transit_graph.invoke(initial_state)
        messages = result["messages"]

        # Extraer respuesta final (último AIMessage)
        final_response = ""
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                final_response = msg.content
                break

        if not final_response:
            raise HTTPException(status_code=500, detail="El agente no generó respuesta")

        # Detectar qué tools fueron usadas
        sources_used = []
        for msg in messages:
            if isinstance(msg, ToolMessage):
                sources_used.append(msg.name if hasattr(msg, 'name') else "tool")

        return ChatResponse(
            response=final_response,
            intent=intent,
            sources_used=list(set(sources_used)),
            data_source="mock",
        )

    except Exception as e:
        # En desarrollo, exponer el error. Sprint 5: manejar con más gracia.
        raise HTTPException(status_code=500, detail=str(e))


# ── Sprint 2+: endpoints adicionales ──────────────────────────────────────────
# GET /traffic/{zone}   → datos de tránsito en tiempo real
# GET /weather/{city}   → datos climáticos en tiempo real  
# GET /history          → historial de consultas (Sprint 4, requiere DB)
# POST /feedback        → retroalimentación del usuario (Sprint 4)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=os.getenv("DEBUG", "true").lower() == "true",
    )
