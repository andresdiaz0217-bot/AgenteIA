# Agente de IA para Información de Tránsito en Tiempo Real

## Descripción del Proyecto
Este proyecto consiste en el desarrollo de un agente de inteligencia artificial capaz de responder preguntas relacionadas con el estado del tránsito en tiempo real. El agente integrará datos provenientes de APIs externas de tráfico (como SIATA o Google Maps) y, como valor agregado, incorporará información climática para mejorar la precisión de sus respuestas, considerando que el clima influye directamente en la movilidad.

## Objetivos

### Objetivo General
Desarrollar un agente de IA que proporcione información útil, precisa y en tiempo real sobre el estado del tránsito.

### Objetivos Específicos
- Consumir datos en tiempo real desde APIs de tránsito.
- Integrar datos climáticos para enriquecer el análisis.
- Permitir consultas en lenguaje natural por parte del usuario.
- Generar respuestas claras y contextualizadas.
- (Opcional) Implementar predicciones simples basadas en patrones históricos.

## Funcionalidades del Agente

- Consulta del estado del tráfico en ubicaciones específicas.
- Estimación de congestión en diferentes horarios.
- Recomendación de rutas alternativas.
- Análisis del impacto del clima en el tráfico.
- Respuestas en lenguaje natural (tipo chatbot).

## Fuentes de Datos (APIs)

### Tránsito
- SIATA (Sistema de Alerta Temprana de Medellín)
- Google Maps API (Directions, Traffic Layer)

### Clima
- OpenWeather API
- WeatherAPI

## Arquitectura del Sistema

1. **Entrada del usuario**
   - Preguntas en lenguaje natural (ej: "¿Cómo está el tráfico hacia El Poblado?")

2. **Procesamiento**
   - NLP para interpretar la intención
   - Identificación de ubicación y contexto

3. **Consumo de APIs**
   - Solicitud de datos de tráfico
   - Solicitud de datos climáticos

4. **Análisis**
   - Correlación entre tráfico y clima
   - Generación de insights simples

5. **Respuesta**
   - Generación de respuesta en lenguaje natural

## Ejemplos de Consultas

- "¿Cómo está el tráfico ahora en Medellín?"
- "¿Hay congestión en la autopista sur?"
- "¿El clima está afectando el tráfico hoy?"
- "¿Cuál es la mejor ruta hacia el centro?"

## Posibles Mejoras Futuras

- Implementación de modelos de machine learning para predicción de tráfico
- Visualización en mapas interactivos
- Integración con datos históricos
- Sistema de alertas personalizadas

---

## Idea Clave
El valor diferencial del proyecto no es solo mostrar datos de tráfico, sino **interpretarlos inteligentemente combinándolos con factores externos como el clima**, ofreciendo así respuestas más útiles y cercanas a la realidad.

---