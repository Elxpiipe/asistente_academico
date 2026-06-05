# 🎓 Asistente Académico IA — Agente ReAct

**Asignatura:** ISY0101 — Optativo Ingeniería de Soluciones con IA  
**Institución:** DuocUC  
**Integrantes:** Patricio Azolas · Felipe Véliz  
**Evaluación:** Parcial N°2 — Desarrollo de un Agente Funcional

---

## Descripción

Sistema de asesoría académica basado en un agente inteligente que integra herramientas de consulta, análisis y generación de documentos sobre el Reglamento Académico y el Calendario de DuocUC. El agente implementa el patrón **ReAct (Reasoning + Acting)**, combinando razonamiento iterativo con acciones concretas para responder consultas estudiantiles de forma adaptativa.

El sistema es capaz de:
- Consultar información del reglamento académico mediante RAG (Retrieval-Augmented Generation)
- Analizar el riesgo académico del estudiante según su situación
- Generar documentos formales (cartas, solicitudes, apelaciones)
- Mantener memoria persistente por estudiante entre sesiones
- Recuperar contexto semántico de consultas previas similares
- Clasificar consultas y planificar iteraciones según su prioridad

---

## Arquitectura del agente

![Diagrama de orquestación](docs/diagrama_orquestacion.png)

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
Respuesta final + oferta de documento si aplica
```

---

## Justificación de componentes

### LangChain como framework (IE2)
Se eligió **LangChain** por su compatibilidad nativa con FAISS, OpenAI y el patrón LCEL (LangChain Expression Language), permitiendo construir cadenas RAG reutilizables. Su ecosistema de `@tool` decorators facilita la integración de herramientas con tipado explícito, garantizando escalabilidad y compatibilidad técnica con el resto del sistema.

### FAISS para recuperación semántica (IE4)
**FAISS** (Facebook AI Similarity Search) fue seleccionado por su eficiencia en búsqueda de vectores de alta dimensión. Se usa en dos capas: el vectorstore de documentos académicos (RAG) y la recuperación semántica del historial de conversaciones del estudiante, permitiendo recuperar consultas previas similares en lugar de solo las más recientes.

### SQLite para memoria persistente (IE3)
**SQLite** ofrece persistencia local sin dependencias externas, ideal para un sistema académico donde cada estudiante tiene un identificador único. La tabla `estudiante_historico` almacena consultas, respuestas y nivel de riesgo, permitiendo continuidad entre sesiones sin infraestructura de servidor.

### GPT-4o-mini como modelo base
Se eligió **GPT-4o-mini** por su balance entre capacidad de razonamiento y costo por token. Es suficientemente capaz para clasificar consultas, analizar riesgo académico y generar documentos formales, sin requerir un modelo de mayor escala para este dominio acotado.

### Streamlit como interfaz (IE1)
**Streamlit** permite construir interfaces web interactivas en Python puro, eliminando la necesidad de un frontend separado. Su modelo de re-renderizado por estado facilita el manejo del historial de conversación y los botones de acción dinámica.

---

## Estructura del repositorio

```
asistente_academico/
├── docs/
│   └── diagrama_orquestacion.png   # Diagrama de arquitectura
├── documentos/
│   ├── RES-VRA-03-2024-NUEVO-REGLAMENTO-ACADÉMICO63-1.pdf
│   └── Calendario_Académico_2026.pdf
├── vectorstore/                     # Índice FAISS (generado por ingest.py)
├── .streamlit/
│   └── config.toml                  # Configuración de tema
├── agent.py                         # Núcleo del agente ReAct
├── app.py                           # Interfaz Streamlit
├── rag_chain.py                     # Cadena RAG con LangChain
├── prompts.py                       # Templates de prompts
├── ingest.py                        # Ingesta y vectorización de documentos
├── agent_memory.db                  # Base de datos SQLite (generada al ejecutar)
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

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

**3. Instalar dependencias**
```bash
pip install -r requirements.txt
```

**4. Configurar variables de entorno**

Copia `.env.example` a `.env` y completa los valores:
```bash
cp .env.example .env
```

Contenido del `.env`:
```
GITHUB_TOKEN=tu_token_aqui
OPENAI_BASE_URL=https://models.inference.ai.azure.com
OPENAI_EMBEDDINGS_URL=https://models.inference.ai.azure.com
```

**5. Vectorizar los documentos**
```bash
python ingest.py
```

Este paso procesa los PDFs de la carpeta `documentos/` y genera el índice FAISS en `vectorstore/`.

---

## Ejecución

```bash
streamlit run app.py
```

La aplicación quedará disponible en `http://localhost:8501`.

---

## Uso del sistema

### Configuración inicial
1. Ingresar un **ID de estudiante** en el sidebar (ej: `EST001`)
2. Activar **"Mostrar razonamiento del agente"** para ver las iteraciones ReAct

### Ejemplos de consultas

| Tipo | Consulta | Comportamiento esperado |
|------|---------|------------------------|
| Informativa | `¿Cuál es el porcentaje mínimo de asistencia?` | 1 iteración, riesgo BAJO |
| Situacional | `Reprobé una asignatura, ¿qué hago?` | 2 iteraciones, riesgo MEDIO, ofrece documento |
| Crítica | `Me van a eliminar, reprobé 3 asignaturas` | 2 iteraciones prioritarias, riesgo ALTO, ofrece documento urgente |

### Generación de documentos
Cuando el agente detecta riesgo MEDIO o ALTO, ofrece generar documentos formales:
- 📄 Solicitud de entrevista con coordinador académico
- 📄 Constancia de alumno regular
- 📄 Apelación formal de calificación

### Memoria entre sesiones
El agente recuerda consultas previas del estudiante. Al usar el mismo ID en sesiones distintas, recupera contexto relevante y lo incluye en la respuesta.

---

## Pruebas realizadas

| Caso | Estudiante | Consulta | Resultado |
|------|-----------|---------|-----------|
| 1 | EST001 | Asistencia mínima | Riesgo BAJO, 1 iteración |
| 2 | EST002 | Reprobó 2 asignaturas | Riesgo ALTO, ofrece documento |
| 3 | EST001 | Segunda consulta | Recupera historial previo (IE3/IE4) |
| 4 | EST002 | Genera solicitud | Carta formal generada correctamente |

---

## Referencias bibliográficas

Chase, H. (2022). *LangChain* (versión 0.3) [Software]. LangChain Inc. https://www.langchain.com

Johnson, J., Douze, M., & Jégou, H. (2019). Billion-scale similarity search with GPUs. *IEEE Transactions on Big Data, 7*(3), 535–547. https://doi.org/10.1109/TBDATA.2019.2921572

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. *Advances in Neural Information Processing Systems, 33*, 9459–9474. https://arxiv.org/abs/2005.11401

Microsoft. (2024). *GitHub Models* [Plataforma de inferencia]. Microsoft Azure. https://github.com/marketplace/models

OpenAI. (2024). *GPT-4o mini: Advancing cost-efficient intelligence*. OpenAI. https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence/

Streamlit Inc. (2024). *Streamlit documentation* (versión 1.x) [Software]. https://docs.streamlit.io

Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2022). ReAct: Synergizing reasoning and acting in language models. *arXiv preprint*. https://arxiv.org/abs/2210.03629