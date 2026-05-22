# 🎓 Asistente Académico IA — LLM + RAG

Asistente inteligente para soporte académico estudiantil basado en **LangChain**, **FAISS** y **GitHub Models (GPT-4o-mini)**.

Desarrollado para ISY0101 – Ingeniería de Soluciones con IA (Duoc UC, 2025).

---

## 📁 Estructura del proyecto

```
asistente_academico/
├── documentos/       ← PDFs institucionales (reglamento, calendario, etc.)
├── vectorstore/      ← Índice FAISS (se genera automáticamente)
├── app.py            ← Interfaz Streamlit
├── rag_chain.py      ← Pipeline RAG principal
├── prompts.py        ← Prompts optimizados (3 variantes)
├── ingest.py         ← Carga y procesamiento de documentos
├── requirements.txt
├── .env.example      ← Plantilla de variables de entorno
├── .gitignore
└── README.md
```

---

## ⚙️ Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/Elxpiipe/asistente_academico.git
cd asistente_academico
```

### 2. Crear entorno virtual
```bash
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Mac/Linux
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
Copia `.env.example` a `.env` y completa tu `GITHUB_TOKEN`:
```
OPENAI_BASE_URL="https://models.inference.ai.azure.com"
OPENAI_EMBEDDINGS_URL="https://models.github.ai/inference"
GITHUB_TOKEN="tu_token_aqui"
```

---

## 🚀 Ejecución

### Paso 1 — Agregar documentos
Coloca los PDFs institucionales en la carpeta `documentos/`.

### Paso 2 — Procesar documentos (solo una vez)
```bash
python ingest.py
```

### Paso 3 — Lanzar la aplicación
```bash
streamlit run app.py
```

La app abrirá en `http://localhost:8501`

---

## 💬 Prompts disponibles

| Tipo | Descripción |
|------|-------------|
| `academico` | Rol de asistente académico oficial  |
| `base` | Control estricto sin rol definido |
| `validado` | Con checklist de coherencia interna |

---

## 🛠️ Tecnologías

| Componente | Tecnología |
|------------|-----------|
| Lenguaje | Python 3.12 |
| Framework RAG | LangChain |
| Base vectorial | FAISS |
| Embeddings | GitHub Models — text-embedding-3-small |
| LLM | GitHub Models — GPT-4o-mini |
| Interfaz | Streamlit |

---

## 👥 Equipo
[Patricio Azolas] y [Felipe Véliz] — ISY0101, Duoc UC 2025
