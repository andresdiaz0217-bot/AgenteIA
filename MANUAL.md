# Transit Agent — Medellín

Agente de IA multiagente para información de tránsito y movilidad urbana en tiempo real. Combina datos de tráfico y clima para generar respuestas inteligentes y recomendaciones contextuales.

---

## ¿Qué hace?

- Consulta el estado del tráfico en zonas de Medellín en tiempo real (TomTom API)
- Consulta condiciones climáticas actuales (OpenWeatherMap API)
- Analiza si el clima está empeorando el tráfico y en qué porcentaje
- Genera recomendaciones concretas: rutas alternativas, mejor horario de salida, transporte público
- Mantiene contexto de la sesión para responder preguntas de seguimiento
- Interfaz web tipo chat con panel de datos en tiempo real

---

## Arquitectura

El sistema está construido como una red de agentes coordinados por LangGraph:

```
Usuario
  ↓
Agente Conversacional   ← interpreta la pregunta en lenguaje natural
  ↓
Router LangGraph        ← decide qué agentes activar
  ↓
┌─────────────────────────────────────┐
│  Tool: get_traffic_status (TomTom)  │
│  Tool: get_weather_status (OWM)     │
└─────────────────────────────────────┘
  ↓ (si hay ambos datos)
Agente Analista         ← correlaciona clima + tráfico, genera insight
  ↓
Agente Recomendador     ← rutas alternativas, horario, tips
  ↓
Agente Conversacional   ← redacta respuesta final en lenguaje natural
  ↓
Usuario
```

### Estructura de carpetas

```
transit-agent/
├── agents/
│   ├── conversational.py   # Agente principal — NLP e intención
│   ├── analyst.py          # Correlación clima/tráfico (5 reglas deterministas)
│   ├── recommender.py      # Rutas alternativas y recomendaciones
│   ├── traffic.py          # Stub para agente de tránsito futuro
│   └── weather.py          # Stub para agente climático futuro
├── tools/
│   ├── traffic_tool.py     # LangChain tool — TomTom Traffic Flow API
│   └── weather_tool.py     # LangChain tool — OpenWeatherMap API
├── graph/
│   ├── workflow.py         # Grafo LangGraph — orquestador central
│   └── memory.py           # Memoria de sesión en RAM
├── prompts/
│   └── system_prompts.py   # Prompts centralizados para todos los agentes
├── api/
│   └── main.py             # Backend FastAPI
├── frontend/
│   └── app.py              # Dashboard Streamlit
├── tests/
│   └── test_sprint1.py     # 31 tests (tools, agentes, API, memoria)
├── cli.py                  # Cliente de terminal
├── .env.example            # Plantilla de variables de entorno
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## Requisitos

- Python 3.12+
- [Ollama](https://ollama.com/download) instalado localmente
- Modelo `llama3.2` descargado en Ollama

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone <url-del-repo>
cd transit-agent
```

### 2. Crear entorno virtual e instalar dependencias

```bash
# Crear entorno virtual
python -m venv .venv

# Activar (Windows)
.venv\Scripts\activate

# Activar (macOS / Linux)
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Editar `.env` con tus keys:

```env
OLLAMA_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434

OPENWEATHER_API_KEY=tu_key_aqui
TOMTOM_API_KEY=tu_key_aqui
```

**Obtener las API keys (ambas gratuitas, sin tarjeta de crédito):**
- **OpenWeatherMap**: https://openweathermap.org/api → 1,000 llamadas/día gratis
- **TomTom**: https://developer.tomtom.com → 2,500 llamadas/día gratis, activar *Traffic API* en tu app

### 4. Descargar el modelo de Ollama

```bash
ollama pull llama3.2
```

> Si tienes poca RAM, usa `ollama pull llama3.2:1b` (1.3 GB, más liviano).

---

## Uso

### Opción 1 — Dashboard web (recomendado)

```bash
# Terminal 1: tener Ollama corriendo
ollama serve

# Terminal 2: levantar el dashboard
streamlit run frontend/app.py
```

Abre `http://localhost:8501` en el navegador.

El dashboard tiene:
- **Chat** a la izquierda para hacer preguntas en lenguaje natural
- **Panel de datos** a la derecha con clima, tráfico, análisis y recomendaciones en tiempo real
- **Botones rápidos** para consultas frecuentes
- **Historial** de la sesión y botón para limpiarla

### Opción 2 — CLI interactivo

```bash
python cli.py
```

```
🚦  TRANSIT AGENT — Medellín
    Modelo : llama3.2 (local)
    Clima  : OpenWeatherMap
    Tráfico: TomTom

Tú: ¿Cómo está el tráfico en El Poblado?
🤖 Agente [trafico]: El tráfico en El Poblado está bajo con 7 minutos de retraso...

Tú: ¿Y el clima está afectando?
🤖 Agente [combinado]: Actualmente está nublado pero sin impacto en la movilidad...
```

Para un mensaje único sin modo interactivo:

```bash
python cli.py --message "¿Hay trancón en la Autopista Sur?"
```

### Opción 3 — API REST

```bash
# Levantar el servidor
uvicorn api.main:app --reload
```

Endpoints disponibles en `http://localhost:8000/docs`:

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/health` | Estado del sistema y fuentes de datos activas |
| POST | `/chat` | Enviar una pregunta al agente |

Ejemplo de llamada (Windows PowerShell):

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/chat" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"message": "Como esta el trafico en Laureles?"}'
```

Ejemplo de llamada (macOS / Linux):

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "¿Cómo está el tráfico en Laureles?"}'
```

### Opción 4 — Docker

```bash
# Ollama debe estar corriendo en el host
docker-compose up --build
```

Servicios levantados:
- API: `http://localhost:8000`
- Dashboard: `http://localhost:8501`

---

## Pruebas

```bash
pytest tests/test_sprint1.py -v
```

Resultado esperado: **31 passed** (no requiere Ollama corriendo — usa mocks).

Las pruebas cubren:
- Tools de tránsito y clima (estructura, rangos, valores válidos)
- Detección de intención del agente conversacional
- Agente analista (5 escenarios de correlación clima/tráfico)
- Agente recomendador (3 tipos de recomendación)
- Memoria de sesión (acumulación, actualización, reset)
- Endpoints de la API (health, chat)

---

## Ejemplos de consultas

```
¿Cómo está el tráfico en El Poblado?
¿Hay congestión en la Autopista Sur?
¿Está lloviendo en Medellín?
¿El clima está afectando el tráfico hoy?
¿La lluvia está empeorando el trancón en el centro?
¿Cuál es la mejor hora para salir hacia Laureles?
¿Hay alternativas para llegar a Envigado?
```

### Zonas reconocidas

El Poblado · Laureles · Centro · Bello · Envigado · Itagüí · Belén · Robledo · Sabaneta · La Estrella · Autopista Sur · Autopista Norte

---

## Cómo funciona internamente

Cuando el usuario hace una pregunta, el flujo es el siguiente:

1. **Agente conversacional** recibe el mensaje y detecta la intención (tráfico, clima, combinado o general)
2. **Router LangGraph** decide qué tools invocar según la intención
3. **Tools** consultan TomTom y/o OpenWeatherMap con datos reales
4. Si hay **ambos datos** (tráfico + clima), el **agente analista** aplica reglas de correlación:
   - Tormenta + congestión alta → alerta crítica
   - Lluvia + congestión alta → la lluvia empeora el tráfico ~30%
   - Lluvia + congestión baja → precaución sin impacto significativo
   - Clima despejado + congestión alta → causa no climática
   - Condiciones normales → todo fluye bien
5. El **agente recomendador** genera sugerencias concretas basadas en el análisis
6. El **agente conversacional** redacta la respuesta final en lenguaje natural
7. La **memoria de sesión** guarda zona, clima y congestión para responder preguntas de seguimiento

---

## Tecnologías

| Componente | Tecnología |
|---|---|
| LLM | Ollama + llama3.2 (local, sin costo) |
| Orquestación de agentes | LangGraph + LangChain |
| API de tránsito | TomTom Traffic Flow API |
| API de clima | OpenWeatherMap API |
| Backend | FastAPI |
| Frontend | Streamlit |
| Pruebas | Pytest |
| Contenedores | Docker + Docker Compose |