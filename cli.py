"""
cli.py

Script de terminal para probar el agente sin levantar FastAPI.
Útil durante desarrollo para iteraciones rápidas.

Uso:
    python cli.py
    python cli.py --message "¿Cómo está el tráfico en El Poblado?"
"""

import argparse
import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()


def run_interactive():
    """Modo interactivo: conversación continua con memoria de sesión."""
    from graph.workflow import transit_graph, build_initial_state
    from graph.memory import session_memory
    from agents.conversational import ConversationalAgent

    agent = ConversationalAgent()
    session_memory.clear()  # sesión nueva

    print("\n" + "="*60)
    weather_src = "OpenWeatherMap" if os.getenv("OPENWEATHER_API_KEY", "tu_key_aqui") != "tu_key_aqui" else "mock"
    traffic_src = "TomTom" if os.getenv("TOMTOM_API_KEY", "tu_key_aqui") != "tu_key_aqui" else "mock"
    print("🚦  TRANSIT AGENT — Medellín")
    print(f"    Modelo : {os.getenv('OLLAMA_MODEL', 'llama3.2')} (local)")
    print(f"    Clima  : {weather_src}")
    print(f"    Tráfico: {traffic_src}")
    print("    Escribe 'salir' para terminar")
    print("="*60 + "\n")

    while True:
        try:
            user_input = input("Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 ¡Hasta luego!")
            break

        if user_input.lower() in ("salir", "exit", "quit", ""):
            print("👋 ¡Hasta luego!")
            break

        # Detectar intención (para mostrar en terminal)
        intent = agent.detect_intent(user_input)

        try:
            state = build_initial_state(user_input)
            result = transit_graph.invoke(state)
            messages = result["messages"]

            # Encontrar la respuesta final
            final_response = ""
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and msg.content:
                    final_response = msg.content
                    break

            print(f"\n Agente [{intent}]: {final_response}\n")

        except Exception as e:
            print(f"\n Error: {e}")
            print("   Verifica que Ollama esté corriendo: ollama serve\n")


def run_single(message: str):
    """Modo de mensaje único para pruebas rápidas."""
    from graph.workflow import transit_graph, build_initial_state
    from agents.conversational import ConversationalAgent

    agent = ConversationalAgent()
    intent = agent.detect_intent(message)

    print(f"\n Pregunta: {message}")
    print(f" Intención detectada: {intent}")
    print(" Procesando...\n")

    result = transit_graph.invoke(build_initial_state(message))

    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and msg.content:
            print(f" Respuesta: {msg.content}\n")
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transit Agent CLI")
    parser.add_argument(
        "--message", "-m",
        type=str,
        help="Mensaje único (si no se provee, entra en modo interactivo)"
    )
    args = parser.parse_args()

    if args.message:
        run_single(args.message)
    else:
        run_interactive()
