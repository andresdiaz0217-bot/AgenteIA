"""
frontend/app.py

Dashboard Streamlit — Sprint 5.
Layout: chat principal + panel lateral de datos.

Ejecutar:
    streamlit run frontend/app.py
"""

import streamlit as st
import sys
import os
from datetime import datetime

# Asegurar que el módulo raíz del proyecto esté en el path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# ── Configuración de página ───────────────────────────────────────────────────

st.set_page_config(
    page_title="Transit Agent — Medellín",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Estilos ───────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* Fondo general */
    .stApp { background-color: #0f1117; }

    /* Tarjetas del panel lateral */
    .metric-card {
        background: #1e2130;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        border-left: 4px solid #4CAF50;
    }
    .metric-card.warning { border-left-color: #FF9800; }
    .metric-card.danger  { border-left-color: #F44336; }
    .metric-card.info    { border-left-color: #2196F3; }

    .metric-label {
        font-size: 11px;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 22px;
        font-weight: 700;
        color: #fff;
    }
    .metric-sub {
        font-size: 12px;
        color: #aaa;
        margin-top: 2px;
    }

    /* Burbujas de chat */
    .chat-user {
        background: #2d3250;
        border-radius: 18px 18px 4px 18px;
        padding: 12px 16px;
        margin: 8px 0;
        margin-left: 20%;
        color: #fff;
        font-size: 14px;
    }
    .chat-agent {
        background: #1e2130;
        border-radius: 18px 18px 18px 4px;
        padding: 12px 16px;
        margin: 8px 0;
        margin-right: 20%;
        color: #e0e0e0;
        font-size: 14px;
        border-left: 3px solid #4CAF50;
    }
    .chat-timestamp {
        font-size: 10px;
        color: #555;
        margin-top: 4px;
    }

    /* Badges de intención */
    .badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 10px;
        font-weight: 600;
        margin-left: 6px;
    }
    .badge-trafico  { background: #1565C0; color: #90CAF9; }
    .badge-clima    { background: #1B5E20; color: #A5D6A7; }
    .badge-combinado{ background: #4A148C; color: #CE93D8; }
    .badge-general  { background: #37474F; color: #B0BEC5; }

    /* Header lateral */
    .sidebar-header {
        font-size: 11px;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin: 16px 0 8px 0;
        padding-bottom: 4px;
        border-bottom: 1px solid #2a2a2a;
    }

    /* Alerta level */
    .alert-normal   { color: #4CAF50; }
    .alert-precaucion { color: #FF9800; }
    .alert-alerta   { color: #FF5722; }
    .alert-critico  { color: #F44336; font-weight: 700; }

    /* Input area */
    .stTextInput > div > div > input {
        background: #1e2130 !important;
        color: #fff !important;
        border-radius: 24px !important;
        border: 1px solid #333 !important;
        padding: 12px 20px !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Estado de sesión ──────────────────────────────────────────────────────────

def init_session():
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "last_traffic" not in st.session_state:
        st.session_state.last_traffic = None
    if "last_weather" not in st.session_state:
        st.session_state.last_weather = None
    if "last_analysis" not in st.session_state:
        st.session_state.last_analysis = None
    if "last_recommendation" not in st.session_state:
        st.session_state.last_recommendation = None
    if "memory_initialized" not in st.session_state:
        from graph.memory import session_memory
        session_memory.clear()
        st.session_state.memory_initialized = True


init_session()

# ── Helpers ───────────────────────────────────────────────────────────────────

def detect_intent(text: str) -> str:
    from agents.conversational import ConversationalAgent
    agent = ConversationalAgent()
    return agent.detect_intent(text)


def badge_html(intent: str) -> str:
    labels = {
        "trafico": ("Tráfico", "trafico"),
        "clima": ("Clima", "clima"),
        "combinado": ("Combinado", "combinado"),
        "general": ("General", "general"),
    }
    label, css = labels.get(intent, ("General", "general"))
    return f'<span class="badge badge-{css}">{label}</span>'


def congestion_color(level: str) -> str:
    return {
        "bajo": "#4CAF50",
        "moderado": "#FF9800",
        "alto": "#FF5722",
        "crítico": "#F44336",
    }.get(level, "#888")


def alert_css(level: str) -> str:
    return {
        "normal": "alert-normal",
        "precaución": "alert-precaucion",
        "alerta": "alert-alerta",
        "crítico": "alert-critico",
    }.get(level, "alert-normal")


def condition_emoji(condition: str) -> str:
    return {
        "despejado": "☀️",
        "nublado": "☁️",
        "lluvia": "🌧️",
        "tormenta": "⛈️",
        "garúa": "🌦️",
    }.get(condition, "🌡️")


def process_message(user_input: str) -> dict:
    """Invoca el grafo y retorna respuesta + datos del estado."""
    from graph.workflow import transit_graph, build_initial_state
    from langchain_core.messages import AIMessage, ToolMessage
    import json

    intent = detect_intent(user_input)
    state = build_initial_state(user_input)
    result = transit_graph.invoke(state)
    messages = result["messages"]

    # Respuesta final
    response_text = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            response_text = msg.content
            break

    # Extraer datos de tools del resultado
    traffic_data = None
    weather_data = None
    for msg in messages:
        if isinstance(msg, ToolMessage):
            try:
                content = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                if "congestion_level" in content:
                    traffic_data = content
                elif "condition" in content and "temperature_celsius" in content:
                    weather_data = content
            except Exception:
                pass

    return {
        "response": response_text,
        "intent": intent,
        "traffic_data": traffic_data,
        "weather_data": weather_data,
        "analysis_result": result.get("analysis_result"),
        "recommendation_result": result.get("recommendation_result"),
        "timestamp": datetime.now().strftime("%H:%M"),
    }


# ── Layout: columna principal + sidebar ──────────────────────────────────────

col_chat, col_panel = st.columns([2, 1], gap="large")

# ════════════════════════════════════════════════════════════════
# PANEL LATERAL — datos en tiempo real
# ════════════════════════════════════════════════════════════════

with col_panel:
    st.markdown("## 📊 Panel de datos")

    # ── Clima ─────────────────────────────────────────────────
    st.markdown('<div class="sidebar-header">🌤 Clima actual</div>', unsafe_allow_html=True)

    weather = st.session_state.last_weather
    if weather:
        emoji = condition_emoji(weather.get("condition", ""))
        card_cls_w = "warning" if weather.get("affects_traffic") else ""
        condition_str = weather.get("condition", "N/A").capitalize()
        temp = weather.get("temperature_celsius", "—")
        humidity = weather.get("humidity_percent", "—")
        wind = weather.get("wind_speed_kmh", "—")
        vis = weather.get("visibility_km", "—")
        source_w = weather.get("data_source", "—")
        ts_w = weather.get("timestamp", "")
        impact_html = (
            f'<div class="metric-sub" style="color:#FF9800;margin-top:6px">⚠️ {weather.get("traffic_impact_reason","")}</div>'
            if weather.get("affects_traffic") else ""
        )
        st.markdown(
            f'<div class="metric-card {card_cls_w}">'
            f'<div class="metric-label">Condición</div>'
            f'<div class="metric-value">{emoji} {condition_str}</div>'
            f'<div class="metric-sub">{temp}°C · {humidity}% humedad</div>'
            f'<div class="metric-sub">Viento: {wind} km/h · Visibilidad: {vis} km</div>'
            + impact_html +
            f'<div class="metric-sub" style="margin-top:6px;color:#555">Fuente: {source_w} · {ts_w}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown("""
        <div class="metric-card info">
            <div class="metric-label">Clima</div>
            <div class="metric-value" style="font-size:14px;color:#666">Pregunta sobre el clima para ver datos aquí</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Tráfico ───────────────────────────────────────────────
    st.markdown('<div class="sidebar-header">🚗 Tráfico</div>', unsafe_allow_html=True)

    traffic = st.session_state.last_traffic
    if traffic:
        score = traffic.get("congestion_score", 0)
        level = traffic.get("congestion_level", "bajo")
        color = congestion_color(level)
        card_cls = "danger" if level == "crítico" else ("warning" if level in ("alto", "moderado") else "metric-card")

        zone_t = traffic.get('zone','—')
        delay_t = traffic.get('estimated_delay_minutes','—')
        source_t = traffic.get('data_source','—')
        ts_t = traffic.get('timestamp','')
        st.markdown(
            f'<div class="metric-card {card_cls}">'
            f'<div class="metric-label">Zona: {zone_t}</div>'
            f'<div class="metric-value" style="color:{color}">{level.upper()}</div>'
            f'<div class="metric-sub">Congestión: {score}/100 · Retraso: ~{delay_t} min</div>'
            f'<div class="metric-sub" style="margin-top:6px;color:#555">Fuente: {source_t} · {ts_t}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        # Barra de congestión
        st.progress(score / 100, text=f"Congestión: {score}%")

        # Incidentes
        incidents = traffic.get("main_incidents", [])
        if incidents:
            st.markdown('<div class="sidebar-header">⚠️ Incidentes</div>', unsafe_allow_html=True)
            for inc in incidents:
                st.markdown(f"- {inc}")

        # Alternativas
        alts = traffic.get("recommended_alternatives", [])
        if alts:
            st.markdown('<div class="sidebar-header">🔀 Alternativas</div>', unsafe_allow_html=True)
            for alt in alts:
                st.markdown(f"- {alt}")
    else:
        st.markdown("""
        <div class="metric-card info">
            <div class="metric-label">Tráfico</div>
            <div class="metric-value" style="font-size:14px;color:#666">Pregunta sobre tráfico para ver datos aquí</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Análisis ──────────────────────────────────────────────
    analysis = st.session_state.last_analysis
    if analysis:
        st.markdown('<div class="sidebar-header">🧠 Análisis</div>', unsafe_allow_html=True)
        alert = analysis.get("alert_level", "normal")
        css = alert_css(alert)
        cause = analysis.get('congestion_cause','—')
        impact_a = analysis.get('weather_impact_percent', 0)
        worsening_html = (
            f'<div class="metric-sub" style="color:#FF9800">Clima empeora tráfico: ~{impact_a}%</div>'
            if analysis.get('weather_worsening_traffic') else ""
        )
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-label">Nivel de alerta</div>'
            f'<div class="metric-value {css}">{alert.upper()}</div>'
            f'<div class="metric-sub">Causa: {cause}</div>'
            + worsening_html +
            f'</div>',
            unsafe_allow_html=True
        )

    # ── Recomendación ─────────────────────────────────────────
    rec = st.session_state.last_recommendation
    if rec:
        st.markdown('<div class="sidebar-header">💡 Recomendación</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="metric-card info">
            <div class="metric-label">Mejor momento para salir</div>
            <div class="metric-value" style="font-size:15px">{rec.get('best_departure_time','—')}</div>
        </div>
        """, unsafe_allow_html=True)

        tips = rec.get("mobility_tips", [])
        if tips:
            for tip in tips:
                st.info(f"💡 {tip}")

        public = rec.get("public_transport_suggestion")
        if public:
            st.success(f"🚇 {public}")

    # ── Historial de zonas ────────────────────────────────────
    from graph.memory import session_memory
    ctx = session_memory.get()
    zones = ctx.get("zones_history", [])
    if zones:
        st.markdown('<div class="sidebar-header">📍 Zonas consultadas</div>', unsafe_allow_html=True)
        for z in reversed(zones):
            st.markdown(f"- {z}")


# ════════════════════════════════════════════════════════════════
# CHAT PRINCIPAL
# ════════════════════════════════════════════════════════════════

with col_chat:
    st.markdown("## 🚦 Transit Agent — Medellín")
    st.markdown(
        "<p style='color:#666;font-size:13px'>Asistente inteligente de movilidad urbana · "
        "Datos en tiempo real de OpenWeatherMap y TomTom</p>",
        unsafe_allow_html=True
    )

    # ── Área de mensajes ──────────────────────────────────────
    chat_container = st.container(height=520)

    with chat_container:
        if not st.session_state.chat_history:
            st.markdown("""
            <div style="text-align:center;padding:60px 20px;color:#444;">
                <div style="font-size:48px;margin-bottom:16px">🚦</div>
                <div style="font-size:16px;margin-bottom:8px;color:#666">¡Hola! Soy tu asistente de movilidad para Medellín.</div>
                <div style="font-size:13px;color:#444">Pregúntame sobre tráfico, clima o rutas.</div>
                <div style="margin-top:24px;font-size:12px;color:#333">
                    Ejemplos:<br>
                    "¿Cómo está el tráfico en El Poblado?"<br>
                    "¿Está lloviendo en Medellín?"<br>
                    "¿La lluvia está afectando el tráfico en el centro?"
                </div>
            </div>
            """, unsafe_allow_html=True)

        for entry in st.session_state.chat_history:
            # Mensaje del usuario
            st.markdown(f"""
            <div class="chat-user">
                {entry['user']}
                {badge_html(entry['intent'])}
                <div class="chat-timestamp">{entry['timestamp']}</div>
            </div>
            """, unsafe_allow_html=True)

            # Respuesta del agente
            st.markdown(f"""
            <div class="chat-agent">
                🤖 {entry['response']}
                <div class="chat-timestamp">{entry['timestamp']}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Input ─────────────────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    with st.form(key="chat_form", clear_on_submit=True):
        col_input, col_btn = st.columns([5, 1])
        with col_input:
            user_input = st.text_input(
                label="mensaje",
                placeholder="¿Cómo está el tráfico en Laureles?",
                label_visibility="collapsed",
            )
        with col_btn:
            submitted = st.form_submit_button("Enviar", use_container_width=True)

    # ── Sugerencias rápidas ───────────────────────────────────
    st.markdown("<div style='margin-top:8px'>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    quick = None
    with c1:
        if st.button("🚗 Tráfico centro", use_container_width=True):
            quick = "¿Cómo está el tráfico en el centro?"
    with c2:
        if st.button("🌧️ ¿Está lloviendo?", use_container_width=True):
            quick = "¿Está lloviendo en Medellín?"
    with c3:
        if st.button("🔀 El Poblado", use_container_width=True):
            quick = "¿La lluvia afecta el tráfico en El Poblado?"
    with c4:
        if st.button("🚇 Laureles", use_container_width=True):
            quick = "¿Cómo está el tráfico en Laureles?"
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Procesar mensaje ──────────────────────────────────────
    message_to_process = quick or (user_input if submitted and user_input.strip() else None)

    if message_to_process:
        with st.spinner("Consultando datos en tiempo real..."):
            try:
                result = process_message(message_to_process)

                # Guardar en historial
                st.session_state.chat_history.append({
                    "user": message_to_process,
                    "response": result["response"],
                    "intent": result["intent"],
                    "timestamp": result["timestamp"],
                })

                # Actualizar panel lateral
                if result["traffic_data"]:
                    st.session_state.last_traffic = result["traffic_data"]
                if result["weather_data"]:
                    st.session_state.last_weather = result["weather_data"]
                if result.get("analysis_result"):
                    st.session_state.last_analysis = result["analysis_result"]
                if result.get("recommendation_result"):
                    st.session_state.last_recommendation = result["recommendation_result"]

            except Exception as e:
                st.error(f"Error al procesar la consulta: {e}")
                st.info("Verifica que Ollama esté corriendo: `ollama serve`")

        st.rerun()

    # ── Footer ────────────────────────────────────────────────
    if st.session_state.chat_history:
        st.markdown(
            f"<div style='text-align:right;font-size:11px;color:#333;margin-top:4px'>"
            f"{len(st.session_state.chat_history)} consultas en esta sesión</div>",
            unsafe_allow_html=True
        )
        if st.button("🗑️ Limpiar sesión", help="Borra el historial y reinicia la memoria"):
            st.session_state.chat_history = []
            st.session_state.last_traffic = None
            st.session_state.last_weather = None
            st.session_state.last_analysis = None
            st.session_state.last_recommendation = None
            from graph.memory import session_memory
            session_memory.clear()
            st.rerun()