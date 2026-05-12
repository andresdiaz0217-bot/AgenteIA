```txt
RECOMENDACIÓN TÉCNICA Y PLAN DE SPRINTS
Proyecto: Agente de IA para Información de Tránsito en Tiempo Real

------------------------------------------------------------
1. VISIÓN DEL PROYECTO
------------------------------------------------------------

El objetivo del proyecto es desarrollar un sistema basado en agentes de inteligencia artificial capaz de responder consultas relacionadas con movilidad y tránsito en Medellín utilizando información en tiempo real.

El sistema integrará:
- APIs de tránsito,
- APIs de clima,
- análisis contextual,
- y generación de respuestas inteligentes.

El valor diferencial del proyecto será combinar tráfico y clima para generar respuestas más útiles y cercanas a la realidad.

------------------------------------------------------------
2. ENFOQUE DE AGENTES DE IA
------------------------------------------------------------

El proyecto debe implementarse como una arquitectura orientada a agentes.

Agentes propuestos:

- Agente Conversacional:
  recibe y entiende preguntas del usuario.

- Agente de Tránsito:
  consulta APIs de movilidad y rutas.

- Agente Climático:
  consulta APIs meteorológicas.

- Agente Analista:
  interpreta el impacto del clima sobre la movilidad.

- Agente Recomendador:
  genera recomendaciones de rutas o movilidad.

Todos los agentes estarán coordinados mediante un flujo agentic (LangGraph o routing por tools).

------------------------------------------------------------
3. TECNOLOGÍAS RECOMENDADAS
------------------------------------------------------------

Lenguaje:
- Python

Framework de agentes:
- LangGraph
- LangChain

Modelo:
- OpenAI GPT-4o / mini
- opcional Ollama

Backend:
- FastAPI

Frontend:
- Streamlit

APIs:
- Google Maps Routes API
- SIATA (si aplica)
- OpenWeather o WeatherAPI

Base de datos:
- PostgreSQL

Infraestructura:
- Docker

Pruebas:
- Pytest

------------------------------------------------------------
4. ARQUITECTURA PROPUESTA
------------------------------------------------------------

Usuario
   ↓
Agente Conversacional
   ↓
Router / Orquestador
   ↓
┌────────────────────┐
│ Agente Tránsito    │
│ Agente Climático   │
│ Agente Analista    │
└────────────────────┘
   ↓
Agente Recomendador
   ↓
Respuesta final

------------------------------------------------------------
5. PLAN DE SPRINTS
------------------------------------------------------------

------------------------------------------------------------
SPRINT 1 — Arquitectura Base y Agente Conversacional
------------------------------------------------------------

Objetivo:
Construir la arquitectura inicial y el primer agente funcional.

Historias de usuario:
- Como usuario, quiero preguntar sobre tráfico.
- Como sistema, quiero interpretar preguntas básicas.

Tareas:
- definir arquitectura del sistema
- estructurar repositorio
- configurar entorno de desarrollo
- integrar modelo LLM
- implementar agente conversacional
- detectar intención básica:
  - tráfico
  - clima
- detectar ubicación simple
- construir respuestas simuladas
- documentar arquitectura

Entregables:
- arquitectura inicial
- agente conversacional funcional
- flujo básico de preguntas

Criterios de aceptación:
- el agente recibe preguntas
- identifica intención
- responde correctamente
- arquitectura documentada

Resultado visible:
El sistema ya tiene un agente funcional que entiende preguntas simples.

------------------------------------------------------------
SPRINT 2 — Integración de APIs (Tránsito y Clima)
------------------------------------------------------------

Objetivo:
Integrar APIs reales para convertir el sistema en un agente útil.

Historias de usuario:
- Como usuario, quiero consultar tráfico real.
- Como usuario, quiero saber si el clima afecta la movilidad.

Tareas:
- integrar Google Maps API
- integrar API climática
- crear:
  - traffic_tool.py
  - weather_tool.py
- normalizar respuestas de APIs
- integrar tools con LangChain
- conectar tools al agente
- generar respuestas naturales
- manejar errores de APIs

Entregables:
- tools funcionales
- agente conectado a APIs reales

Criterios de aceptación:
- el sistema consulta APIs reales
- responde con datos reales
- maneja errores correctamente

Resultado visible:
El sistema ya responde usando datos reales de tránsito y clima.

------------------------------------------------------------
SPRINT 3 — Agente Analista (Clima + Tránsito)
------------------------------------------------------------

Objetivo:
Implementar lógica de análisis y correlación entre movilidad y clima.

Historias de usuario:
- Como usuario, quiero entender si la lluvia afecta el tráfico.
- Como sistema, quiero generar insights básicos.

Tareas:
- implementar agente analista
- crear reglas de correlación:
  - lluvia + congestión
  - calor + movilidad
- generar análisis contextual
- mejorar prompts
- detectar niveles de congestión
- generar insights simples
- conectar flujo completo de análisis

Entregables:
- agente analista funcional
- respuestas contextualizadas

Criterios de aceptación:
- el sistema combina clima y tráfico
- genera recomendaciones útiles
- responde consultas compuestas

Resultado visible:
El agente ya interpreta información, no solo la muestra.

------------------------------------------------------------
SPRINT 4 — Agente Recomendador y Memoria
------------------------------------------------------------

Objetivo:
Agregar recomendaciones inteligentes y memoria conversacional.

Historias de usuario:
- Como usuario, quiero recomendaciones de rutas.
- Como usuario, quiero una conversación más natural.

Tareas:
- implementar agente recomendador
- sugerir rutas alternativas
- implementar memoria básica
- recordar contexto:
  - ubicación
  - ruta
  - última consulta
- mejorar experiencia conversacional
- manejar preguntas de seguimiento
- integrar flujo multiagente

Entregables:
- recomendaciones de movilidad
- memoria conversacional

Criterios de aceptación:
- el sistema recuerda contexto
- genera recomendaciones útiles
- mantiene coherencia conversacional

Resultado visible:
El agente se comporta como asistente de movilidad inteligente.

------------------------------------------------------------
SPRINT 5 — Producto Final y Dashboard
------------------------------------------------------------

Objetivo:
Entregar un sistema completo y demostrable.

Historias de usuario:
- Como usuario, quiero consultar tráfico desde una interfaz amigable.
- Como evaluador, quiero un sistema funcional y bien documentado.

Tareas:
- construir interfaz en Streamlit
- visualizar:
  - estado del tráfico
  - clima
  - recomendaciones
- integrar flujo completo
- agregar logs e historial
- realizar pruebas completas
- documentar sistema
- preparar demo final
- contenerizar con Docker

Entregables:
- sistema multiagente completo
- dashboard funcional
- documentación técnica
- demo final

Criterios de aceptación:
- flujo completo funcional
- agentes coordinados
- respuestas útiles y coherentes
- interfaz funcional

Resultado visible:
Sistema completo de asistencia inteligente para movilidad urbana.

------------------------------------------------------------
6. DISTRIBUCIÓN DEL EQUIPO (4 INTEGRANTES)
------------------------------------------------------------

Estudiante 1:
- APIs
- tools
- backend

Estudiante 2:
- agente conversacional
- prompts
- NLP básico

Estudiante 3:
- agente analista
- recomendaciones
- memoria

Estudiante 4:
- frontend
- pruebas
- documentación
- integración final

------------------------------------------------------------
7. VALOR DIFERENCIAL
------------------------------------------------------------

El sistema no solo consulta tráfico, sino que:
- interpreta condiciones de movilidad,
- correlaciona clima y congestión,
- genera recomendaciones,
- y mejora la experiencia del usuario mediante agentes especializados.

------------------------------------------------------------
8. RECOMENDACIONES CLAVE
------------------------------------------------------------

- No construir solo un chatbot
- Separar responsabilidades entre agentes
- Validar APIs desde etapas tempranas
- Implementar tools antes de prompts complejos
- Usar LangGraph para orquestación
- Priorizar funcionamiento real antes de optimización visual

------------------------------------------------------------
9. CONCLUSIÓN
------------------------------------------------------------

El proyecto representa una solución basada en agentes de IA orientada a movilidad urbana inteligente, donde múltiples agentes colaboran para consultar, analizar e interpretar información en tiempo real sobre tránsito y clima.
```
