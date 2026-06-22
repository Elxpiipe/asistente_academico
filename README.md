# 🎓 Asistente Académico IA — Agente ReAct + Observabilidad

**Asignatura:** ISY0101 — Optativo Ingeniería de Soluciones con IA  
**Institución:** DuocUC  
**Integrantes:** Patricio Azolas · Felipe Véliz  
**Evaluaciones:** EP1 — Sistema RAG | EP2 — Agente ReAct | EP3 — Observabilidad

---

## Descripción

Sistema de asesoría académica basado en un agente inteligente que integra herramientas de consulta, análisis y generación de documentos sobre el Reglamento Académico y el Calendario de DuocUC. El agente implementa el patrón **ReAct (Reasoning + Acting)**, combinando razonamiento iterativo con acciones concretas para responder consultas estudiantiles de forma adaptativa.

A partir de EP3, el sistema incorpora **observabilidad completa**: métricas de latencia, precisión y recursos, trazabilidad de ejecución, dashboard visual interactivo y protocolos de seguridad y uso responsable.

El sistema es capaz de:
- Consultar información del reglamento académico mediante RAG (Retrieval-Augmented Generation)
- Analizar el riesgo académico del estudiante según su situación
- Generar documentos formales (cartas, solicitudes, apelaciones)
- Mantener memoria persistente por estudiante entre sesiones
- Recuperar contexto semántico de consultas previas similares
- Clasificar consultas y planificar iteraciones según su prioridad
- **Medir latencia, precisión y uso de recursos en tiempo real**
- **Detectar anomalías y patrones en los registros de ejecución**
- **Bloquear intentos de prompt injection y consultas fuera de dominio**

---

## Arquitectura del agente

![Diagrama de orquestación](https://raw.githubusercontent.com/Elxpiipe/asistente_academico/main/docs/diagrama_orquestacion.PNG)

El sistema se organiza en 5 capas:

| Capa | Componente | Descripción |
|------|-----------|-------------|
| Interfaz | `app.py` | Interfaz web Streamlit con chat, historial y botones de acción |
| Núcleo | `agent.py` | Agente ReAct con clasificador, planificador, razonador y LLM |
| Herramientas | `tools` | 3 herramientas: consultar, analizar, generar |
| Memoria | `memory` | Memoria de contenido (SQLite) y recuperación semántica (FAISS) |
| Almacenamiento | `storage` | SQLite, vectorstore FAISS y PDFs fuente |

### Flujo ReAct

```
Consulta del estudiante
        ↓
[SEG] Validación y sanitización de input (security.py)
        ↓
[OBS] Iniciar observador de métricas (observability.py)
        ↓
[IE3] Cargar historial SQLite
        ↓
[IE4] Recuperación semántica (FAISS + embeddings)
        ↓
[IE5] Clasificar consulta → informativa / situacional / crítica
        ↓
[IE5] Planificar iteraciones según prioridad
        ↓
[IE1] Iterar herramientas según plan:
      consultar_reglamento → analizar_riesgo → (generar_documento)
        ↓
[IE6] Decisión adaptativa según riesgo (BAJO / MEDIO / ALTO)
        ↓
[OBS] Registrar métricas, latencia y trazabilidad
        ↓
Respuesta final + oferta de documento si aplica
```

---

## Módulos de Observabilidad (EP3)

### observability.py
Registra métricas y trazabilidad en SQLite:
- **IE1:** Precisión, consistencia y frecuencia de errores
- **IE2:** Latencia por herramienta y uso de CPU/RAM (psutil)
- **IE3:** Trazabilidad paso a paso de cada ejecución
- **IE4:** Detección automática de anomalías

### dashboard.py
Dashboard visual interactivo (Streamlit + Plotly):
- Métricas generales en tiempo real
- Gráficos de latencia por herramienta
- Distribución de riesgo y categorías
- Trazabilidad filtrable por estado, herramienta y estudiante
- Panel de seguridad y uso responsable

### security.py
Protocolos de seguridad y uso responsable:
- Detección de prompt injection (14 patrones regex)
- Anonimización de datos sensibles en logs
- Validación de ID de estudiante
- Límite de 50 consultas por estudiante/día
- Truncado de inputs a 500 caracteres

---

## Justificación de componentes

### LangChain como framework
Se eligió **LangChain** por su compatibilidad nativa con FAISS, OpenAI y el patrón LCEL, permitiendo construir cadenas RAG reutilizables con `@tool` decorators escalables.

### FAISS para recuperación semántica
**FAISS** fue seleccionado por su eficiencia en búsqueda de vectores de alta dimensión, usado tanto en el vectorstore de documentos como en la recuperación semántica del historial.

### SQLite para memoria persistente
**SQLite** ofrece persistencia local sin dependencias externas. Almacena historial de consultas, métricas de ejecución, trazabilidad y registros de errores.

### GPT-4o-mini como modelo base
Balance óptimo entre capacidad de razonamiento y costo por token para clasificar consultas, analizar riesgo académico y generar documentos formales.

### Plotly para visualización (EP3)
Gráficos interactivos (barras, tortas, líneas de tendencia) integrados directamente en Streamlit sin infraestructura adicional.

### psutil para métricas de recursos (EP3)
Captura uso de CPU y memoria RAM en tiempo real durante cada ejecución del agente.

---

## Estructura del repositorio

```
asistente_academico/
├── docs/
│   └── diagrama_orquestacion.PNG   # Diagrama de arquitectura
├── documentos/
│   ├── RES-VRA-03-2024-NUEVO-REGLAMENTO-ACADÉMICO63-1.pdf
│   └── Calendario_Académico_2026.pdf
├── vectorstore/                     # Índice FAISS (generado por ingest.py)
├── .streamlit/
│   └── config.toml                  # Configuración de tema claro
├── agent.py                         # Núcleo del agente ReAct + observabilidad
├── app.py                           # Interfaz Streamlit del asistente
├── dashboard.py                     # Dashboard de observabilidad (EP3)
├── observability.py                 # Métricas, logs y trazabilidad (EP3)
├── security.py                      # Protocolos de seguridad (EP3)
├── rag_chain.py                     # Cadena RAG con LangChain
├── prompts.py                       # Templates de prompts
├── ingest.py                        # Ingesta y vectorización de documentos
├── limpiar_errores_token.py         # Utilidad: limpieza de registros de error
├── agent_memory.db                  # Base de datos SQLite (generada al ejecutar)
├── agent_observability.log          # Log estructurado (generado al ejecutar)
├── requirements.txt                 # Dependencias del proyecto
└── .env.example                     # Variables de entorno requeridas
```

---

## Requisitos

- Python 3.10 o superior
- Cuenta en GitHub Models (para acceso a GPT-4o-mini y embeddings)
- Las dependencias listadas en `requirements.txt`

---

## Instalación

**1. Clonar el repositorio**
```bash
git clone https://github.com/Elxpiipe/asistente_academico.git
cd asistente_academico
```

**2. Crear entorno virtual**
```bash
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # macOS / Linux
```

**3. Instalar dependencias**
```bash
pip install -r requirements.txt
```

**4. Configurar variables de entorno**
```bash
cp .env.example .env
```

Contenido del `.env`:
```
GITHUB_TOKEN=tu_token_aqui
OPENAI_BASE_URL=https://models.inference.ai.azure.com
OPENAI_EMBEDDINGS_URL=https://models.github.ai/inference
```

**5. Vectorizar los documentos**
```bash
python ingest.py
```

---

## Ejecución

### Asistente académico
```bash
streamlit run app.py
```
Disponible en `http://localhost:8501`

### Dashboard de observabilidad (EP3)
```bash
streamlit run dashboard.py
```
Disponible en `http://localhost:8502`

Ambos pueden ejecutarse simultáneamente en terminales separadas. El dashboard se actualiza en tiempo real con cada consulta procesada.

---

## Uso del sistema

### Asistente académico

1. Ingresar un **ID de estudiante** en el sidebar (ej: `EST001`)
2. Activar **"Mostrar razonamiento del agente"** para ver las iteraciones ReAct

| Tipo | Consulta | Comportamiento esperado |
|------|---------|------------------------|
| Informativa | `¿Cuál es el porcentaje mínimo de asistencia?` | 1 iteración, riesgo BAJO |
| Situacional | `Reprobé una asignatura, ¿qué hago?` | 2 iteraciones, riesgo MEDIO, ofrece documento |
| Crítica | `Me van a eliminar, reprobé 3 asignaturas` | 2 iteraciones prioritarias, riesgo ALTO |

### Dashboard de observabilidad

El dashboard muestra en tiempo real:
- **Métricas generales:** tasa de éxito, latencia promedio, CPU y RAM
- **Latencia por herramienta:** clasificación, consulta RAG, análisis, generación
- **Patrones y anomalías:** detección automática de comportamientos anómalos
- **Trazabilidad:** logs filtrables por estado, herramienta y estudiante
- **Seguridad:** protocolos activos y actividad de uso por estudiante

---

## Pruebas realizadas

| Caso | Estudiante | Consulta | Resultado |
|------|-----------|---------|-----------|
| 1 | EST001 | Asistencia mínima | Riesgo BAJO, 1 iteración, latencia 4.260ms |
| 2 | EST002 | Reprobó 2 asignaturas | Riesgo ALTO, ofrece documento, latencia 8.588ms |
| 3 | EST001 | Segunda consulta | Recupera historial previo (IE3/IE4) |
| 4 | EST002 | Genera solicitud | Carta formal generada correctamente |
| 5 | EST001 | Prompt injection | Bloqueado por security.py |
| 6 | EST003 | Situación crítica | Riesgo ALTO, 2 iteraciones prioritarias |

---

## Referencias bibliográficas

Chase, H. (2022). *LangChain* (versión 0.3) [Software]. LangChain Inc. https://www.langchain.com

Chen, C., Zaharia, M., & Zou, J. (2023). How is ChatGPT's behavior changing over time? *arXiv preprint*. https://arxiv.org/abs/2307.09009

Johnson, J., Douze, M., & Jégou, H. (2019). Billion-scale similarity search with GPUs. *IEEE Transactions on Big Data, 7*(3), 535–547. https://doi.org/10.1109/TBDATA.2019.2921572

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. *Advances in Neural Information Processing Systems, 33*, 9459–9474. https://arxiv.org/abs/2005.11401

Microsoft. (2024). *GitHub Models* [Plataforma de inferencia]. Microsoft Azure. https://github.com/marketplace/models

OpenAI. (2024). *GPT-4o mini: Advancing cost-efficient intelligence*. OpenAI. https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence/

OpenTelemetry Authors. (2024). *OpenTelemetry documentation*. https://opentelemetry.io/docs/

Plotly Technologies Inc. (2024). *Plotly Python graphing library*. https://plotly.com/python/

psutil developers. (2024). *psutil documentation*. https://psutil.readthedocs.io/

Streamlit Inc. (2024). *Streamlit documentation* (versión 1.x) [Software]. https://docs.streamlit.io

Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2022). ReAct: Synergizing reasoning and acting in language models. *arXiv preprint*. https://arxiv.org/abs/2210.03629