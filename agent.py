"""
Agente ReAct para consultas académicas.
Incluye memoria de contenido (IE3), recuperación semántica (IE4),
planificación con prioridades (IE5), toma de decisiones adaptativas (IE6)
y observabilidad completa (EP3: IE1, IE2, IE3).
"""

import os
import time
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.tools import tool
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from rag_chain import consultar as rag_consultar
from observability import AgentObserver

load_dotenv()

DB_FILE = "agent_memory.db"

# ── BASE DE DATOS ────────────────────────────────────────────────

def init_database():
    """Crea tabla de historiales."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS estudiante_historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            timestamp TEXT,
            consulta TEXT,
            respuesta TEXT,
            riesgo_academico TEXT
        )
    """)
    conn.commit()
    conn.close()

def guardar_interaccion(student_id: str, consulta: str, respuesta: str, riesgo: str = "evaluado"):
    """Guarda una interacción en el histórico, evitando duplicados."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM estudiante_historico
        WHERE student_id = ? AND consulta = ?
        AND timestamp > datetime('now', '-10 seconds')
    """, (student_id, consulta))
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO estudiante_historico 
            (student_id, timestamp, consulta, respuesta, riesgo_academico)
            VALUES (?, ?, ?, ?, ?)
        """, (student_id, datetime.now().isoformat(), consulta, respuesta, riesgo))
        conn.commit()
    conn.close()

def obtener_historial(student_id: str, limite: int = 5) -> list[dict]:
    """Recupera las últimas interacciones del estudiante desde SQLite (IE3)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, consulta, respuesta, riesgo_academico
        FROM estudiante_historico
        WHERE student_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (student_id, limite))
    filas = cursor.fetchall()
    conn.close()
    return [
        {"timestamp": f[0], "consulta": f[1], "respuesta": f[2], "riesgo": f[3]}
        for f in filas
    ]

# ── HERRAMIENTAS ────────────────────────────────────────────────

@tool
def consultar_reglamento(pregunta: str) -> str:
    """Busca información en el reglamento académico y calendario."""
    resultado = rag_consultar(pregunta, tipo_prompt="academico")
    respuesta = resultado["respuesta"]
    fuentes = resultado.get("fuentes", [])
    if fuentes:
        respuesta += "\n\n[Fuentes: " + ", ".join(
            [f"{f['fuente']} pág {f['pagina']}" for f in fuentes[:2]]
        ) + "]"
    return respuesta

@tool
def analizar_riesgo(situacion: str) -> str:
    """Analiza el riesgo académico del estudiante."""
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=os.getenv("GITHUB_TOKEN"),
        openai_api_base=os.getenv("OPENAI_BASE_URL"),
    )
    prompt = f"""
    Eres un asesor académico. Analiza la siguiente situación de un estudiante
    y evalúa su riesgo académico REAL basándote en lo que el estudiante está
    viviendo, NO en el contenido general del reglamento.

    Situación:
    {situacion}

    REGLAS para clasificar el riesgo:
    - BAJO: El estudiante solo está consultando información general, no reporta ningún problema.
    - MEDIO: El estudiante menciona dificultades concretas pero manejables (ej: una asignatura reprobada, asistencia justa).
    - ALTO: El estudiante está en riesgo de eliminación, reprobó múltiples asignaturas, o enfrenta una situación crítica.

    Comienza tu respuesta con: Riesgo: BAJO, Riesgo: MEDIO o Riesgo: ALTO.
    Luego da recomendaciones breves y directas acordes al nivel de riesgo.
    """
    resultado = llm.invoke(prompt)
    return resultado.content

@tool
def generar_documento(tipo: str, contexto: str) -> str:
    """Genera una carta o documento formal para el estudiante usando el LLM."""
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=os.getenv("GITHUB_TOKEN"),
        openai_api_base=os.getenv("OPENAI_BASE_URL"),
    )
    tipos_desc = {
        "solicitud_entrevista": "Solicitud de entrevista con el coordinador académico",
        "constancia_alumno_regular": "Constancia de alumno regular",
        "apelacion_nota": "Apelación formal de calificación",
    }
    descripcion = tipos_desc.get(tipo, tipo)
    prompt = f"""
    Redacta un documento formal académico del tipo: {descripcion}.
    
    Contexto de la situación del estudiante:
    {contexto}
    
    El documento debe incluir: fecha actual, saludo formal, cuerpo con la solicitud fundamentada,
    cierre formal y espacio para firma. Usa formato de carta oficial.
    Fecha actual: {datetime.now().strftime('%d de %B de %Y')}.
    """
    resultado = llm.invoke(prompt)
    return resultado.content


# ── RECUPERACIÓN SEMÁNTICA (IE4) ─────────────────────────────────

def recuperar_contexto_semantico(pregunta: str, historial: list[dict]) -> str:
    """
    Busca en el historial del estudiante las consultas semánticamente
    más similares a la pregunta actual usando embeddings + FAISS (IE4).
    Con fallback robusto si hay pocos registros o falla la API.
    """
    if not historial:
        return ""

    if len(historial) == 1:
        item = historial[0]
        riesgo = item.get("riesgo") or "N/A"
        return (
            f"📋 CONSULTA PREVIA DEL ESTUDIANTE:\n"
            f"- [{item['timestamp'][:10]}] {item['consulta']} → Riesgo: {riesgo}\n"
        )

    try:
        embeddings = OpenAIEmbeddings(
            openai_api_key=os.getenv("GITHUB_TOKEN"),
            openai_api_base=os.getenv("OPENAI_EMBEDDINGS_URL"),
        )
        documentos = [
            Document(
                page_content=item["consulta"],
                metadata={
                    "respuesta": item["respuesta"][:300],
                    "timestamp": item["timestamp"],
                    "riesgo": item.get("riesgo") or "BAJO"
                }
            )
            for item in historial
        ]
        vectorstore = FAISS.from_documents(documentos, embeddings)
        k = min(2, len(documentos))
        resultados = vectorstore.similarity_search(pregunta, k=k)
        if not resultados:
            return ""
        contexto = "📋 CONTEXTO DE CONSULTAS PREVIAS SIMILARES:\n"
        for r in resultados:
            riesgo = r.metadata.get("riesgo") or "N/A"
            contexto += f"- [{r.metadata['timestamp'][:10]}] Preguntaste: \"{r.page_content}\" → Riesgo: {riesgo}\n"
        return contexto

    except Exception as e:
        print(f"[IE4] Fallback a recuperación por texto: {e}")
        contexto = "📋 CONSULTAS PREVIAS DEL ESTUDIANTE:\n"
        for item in historial[:2]:
            riesgo = item.get("riesgo") or "N/A"
            contexto += f"- [{item['timestamp'][:10]}] {item['consulta']} → Riesgo: {riesgo}\n"
        return contexto


# ── CLASIFICACIÓN DE CONSULTA (IE5) ──────────────────────────────

def clasificar_consulta(pregunta: str, llm) -> str:
    """
    Clasifica la consulta para determinar cuántas iteraciones necesita (IE5).
    Retorna: 'informativa', 'situacional' o 'critica'
    """
    prompt = f"""Clasifica esta consulta académica en una de estas 3 categorías:

- informativa: el estudiante solo quiere saber algo general (normas, fechas, porcentajes)
- situacional: el estudiante describe un problema concreto que necesita análisis
- critica: el estudiante enfrenta una situación grave (eliminación, múltiples reprobaciones, urgencia)

Consulta: "{pregunta}"

Responde SOLO con una palabra: informativa, situacional o critica."""

    resultado = llm.invoke(prompt)
    categoria = resultado.content.strip().lower()
    if categoria not in ["informativa", "situacional", "critica"]:
        return "situacional"
    return categoria


# ── DECISIÓN ADAPTATIVA (IE6) ────────────────────────────────────

def decidir_accion(riesgo: str, respuesta_consulta: str, analisis: str) -> dict:
    """Toma de decisiones adaptativa según el nivel de riesgo detectado (IE6)."""
    riesgo_upper = riesgo.upper()

    if riesgo_upper == "ALTO":
        mensaje_adicional = (
            "\n\n⚠️ **Tu situación requiere atención inmediata.**\n"
            "Te recomiendo comunicarte con tu coordinador académico a la brevedad."
        )
        ofrecer_documento = True
        documentos_disponibles = ["solicitud_entrevista", "apelacion_nota"]

    elif riesgo_upper == "MEDIO":
        mensaje_adicional = (
            "\n\n📌 **Tu situación es manejable pero requiere atención.**\n"
            "Sigue las recomendaciones indicadas para evitar que escale."
        )
        ofrecer_documento = True
        documentos_disponibles = ["solicitud_entrevista", "constancia_alumno_regular"]

    else:
        mensaje_adicional = "\n\n✅ **Tu situación académica está bien encaminada.** Sigue así."
        ofrecer_documento = False
        documentos_disponibles = []

    return {
        "mensaje_adicional": mensaje_adicional,
        "ofrecer_documento": ofrecer_documento,
        "documentos_disponibles": documentos_disponibles,
    }


# ── AGENTE PRINCIPAL ─────────────────────────────────────────────

class AgenteAcademico:
    def __init__(self, student_id: str = "anonimo"):
        self.student_id = student_id
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            openai_api_key=os.getenv("GITHUB_TOKEN"),
            openai_api_base=os.getenv("OPENAI_BASE_URL"),
        )
        self.tools = {
            "consultar": consultar_reglamento,
            "analizar":  analizar_riesgo,
            "generar":   generar_documento,
        }
        init_database()

    def procesar_consulta(self, pregunta: str, max_iteraciones: int = 5) -> str:
        """
        Procesa una consulta con lógica ReAct + memoria + planificación +
        decisión adaptativa + observabilidad completa (EP3).
        """

        print(f"\n{'='*60}")
        print(f"📌 Estudiante: {self.student_id}")
        print(f"❓ Pregunta: {pregunta}")
        print(f"{'='*60}\n")

        # ── OBSERVABILIDAD: Iniciar observer ─────────────────────
        observer = AgentObserver(student_id=self.student_id)

        try:
            # ── IE3: Cargar memoria de contenido ──────────────────
            print("[Memoria] Cargando historial del estudiante...")
            t0 = time.time()
            historial = obtener_historial(self.student_id)
            observer.registrar_paso(
                "CARGAR_HISTORIAL",
                duracion_ms=(time.time() - t0) * 1000,
                detalle=f"{len(historial)} registros cargados"
            )

            # ── IE4: Recuperación semántica ───────────────────────
            print("[Memoria] Recuperando contexto semántico...")
            t0 = time.time()
            contexto_previo = recuperar_contexto_semantico(pregunta, historial)
            observer.registrar_paso(
                "RECUPERACION_SEMANTICA",
                duracion_ms=(time.time() - t0) * 1000,
                detalle="Con FAISS" if "SIMILARES" in contexto_previo else "Fallback texto"
            )

            # ── IE5: Clasificar consulta ──────────────────────────
            print("[Planificación] Clasificando consulta...")
            t0 = time.time()
            categoria = clasificar_consulta(pregunta, self.llm)
            dur_clasificacion = (time.time() - t0) * 1000
            observer.registrar_latencia("clasificacion", dur_clasificacion)
            observer.registrar_paso(
                "CLASIFICACION",
                herramienta="clasificar_consulta",
                duracion_ms=dur_clasificacion,
                detalle=f"Categoría: {categoria}"
            )
            print(f"[Planificación] Categoría: {categoria}")

            # ── Iniciar ejecución en observer ─────────────────────
            observer.iniciar_ejecucion(pregunta, categoria)

            # Definir plan según categoría
            if categoria == "informativa":
                iteraciones_plan = ["consultar"]
                print("[Planificación] Plan: 1 iteración (solo consulta)\n")
            elif categoria == "situacional":
                iteraciones_plan = ["consultar", "analizar"]
                print("[Planificación] Plan: 2 iteraciones (consulta + análisis)\n")
            else:
                iteraciones_plan = ["consultar", "analizar"]
                print("[Planificación] Plan: 2 iteraciones PRIORITARIAS (urgente)\n")

            pregunta_con_contexto = pregunta
            if contexto_previo:
                pregunta_con_contexto = f"{contexto_previo}\n\nConsulta actual: {pregunta}"

            respuesta_consulta = ""
            analisis = ""
            riesgo_detectado = "BAJO"

            # ── Ejecutar herramientas según el plan ───────────────
            for i, paso in enumerate(iteraciones_plan, 1):

                if paso == "consultar":
                    print(f"[Iteración {i}] Consultando reglamento...")
                    t0 = time.time()
                    try:
                        respuesta_consulta = consultar_reglamento.invoke(pregunta_con_contexto)
                        dur = (time.time() - t0) * 1000
                        observer.registrar_latencia("consulta", dur)
                        observer.registrar_herramienta("consultar_reglamento")
                        observer.registrar_paso(
                            f"ITERACION_{i}_CONSULTA",
                            herramienta="consultar_reglamento",
                            duracion_ms=dur,
                            estado="OK",
                            detalle=f"Respuesta: {respuesta_consulta[:80]}"
                        )
                        print("✓ Información encontrada\n")
                    except Exception as e:
                        observer.registrar_error("ERROR_CONSULTA", str(e), "consultar_reglamento")
                        raise

                elif paso == "analizar":
                    print(f"[Iteración {i}] Analizando situación...")
                    t0 = time.time()
                    try:
                        prefijo = "⚠️ SITUACIÓN CRÍTICA - " if categoria == "critica" else ""
                        contexto_analisis = f"{prefijo}Pregunta del estudiante: {pregunta}\n\nInformación del reglamento: {respuesta_consulta[:400]}"
                        analisis = analizar_riesgo.invoke(contexto_analisis)
                        dur = (time.time() - t0) * 1000
                        observer.registrar_latencia("analisis", dur)
                        observer.registrar_herramienta("analizar_riesgo")

                        for nivel in ["ALTO", "MEDIO", "BAJO"]:
                            if nivel in analisis.upper():
                                riesgo_detectado = nivel
                                break

                        observer.registrar_paso(
                            f"ITERACION_{i}_ANALISIS",
                            herramienta="analizar_riesgo",
                            duracion_ms=dur,
                            estado="OK",
                            detalle=f"Riesgo detectado: {riesgo_detectado}"
                        )
                        print(f"✓ Análisis completado — Riesgo: {riesgo_detectado}\n")
                    except Exception as e:
                        observer.registrar_error("ERROR_ANALISIS", str(e), "analizar_riesgo")
                        raise

            # ── IE6: Decisión adaptativa ──────────────────────────
            print(f"[Decisión] Riesgo detectado: {riesgo_detectado}")
            decision = decidir_accion(riesgo_detectado, respuesta_consulta, analisis)
            observer.registrar_paso(
                "DECISION_ADAPTATIVA",
                detalle=f"Riesgo={riesgo_detectado} | Documento={decision['ofrecer_documento']}"
            )

            # ── Construcción de respuesta final ───────────────────
            bloque_contexto = ""
            if contexto_previo:
                bloque_contexto = f"\n{contexto_previo}\n\n---\n"

            if categoria == "informativa":
                respuesta_final = f"""{bloque_contexto}RESPUESTA DEL ASESOR ACADÉMICO:

{respuesta_consulta}

{decision['mensaje_adicional'].strip()}"""
            else:
                respuesta_final = f"""{bloque_contexto}RESPUESTA DEL ASESOR ACADÉMICO:

{respuesta_consulta}

---

ANÁLISIS DE TU SITUACIÓN:
{analisis}{decision['mensaje_adicional']}"""

            if decision["ofrecer_documento"]:
                opciones = " | ".join([f"`{d}`" for d in decision["documentos_disponibles"]])
                respuesta_final += f"\n\n---\n📄 **¿Deseas que genere un documento formal?**\nOpciones disponibles: {opciones}"

            # ── Guardar en histórico ──────────────────────────────
            guardar_interaccion(self.student_id, pregunta, respuesta_final, riesgo=riesgo_detectado)

            # ── OBSERVABILIDAD: Finalizar ejecución ───────────────
            observer.finalizar_ejecucion(riesgo=riesgo_detectado)

            return respuesta_final

        except Exception as e:
            observer.registrar_error("ERROR_GENERAL", str(e))
            observer.finalizar_ejecucion(riesgo="ERROR")
            raise

    def generar_documento_solicitado(self, tipo: str) -> str:
        """Genera un documento formal usando el historial reciente como contexto."""
        observer = AgentObserver(student_id=self.student_id)
        t0 = time.time()
        try:
            historial = obtener_historial(self.student_id, limite=1)
            contexto = historial[0]["respuesta"][:500] if historial else "Sin contexto previo."
            resultado = generar_documento.invoke({"tipo": tipo, "contexto": contexto})
            dur = (time.time() - t0) * 1000
            observer.registrar_latencia("generacion", dur)
            observer.registrar_herramienta("generar_documento")
            observer.registrar_paso("GENERACION_DOCUMENTO", herramienta="generar_documento",
                                    duracion_ms=dur, detalle=f"Tipo: {tipo}")
            observer.finalizar_ejecucion(riesgo="N/A")
            return resultado
        except Exception as e:
            observer.registrar_error("ERROR_GENERACION", str(e), "generar_documento")
            observer.finalizar_ejecucion(riesgo="ERROR")
            raise


# ── FUNCIÓN PRINCIPAL ────────────────────────────────────────────

def consultar_agente(pregunta: str, student_id: str = "anonimo") -> dict:
    agente = AgenteAcademico(student_id)
    respuesta = agente.procesar_consulta(pregunta)
    return {"respuesta": respuesta}


# ── PRUEBAS ──────────────────────────────────────────────────────

if __name__ == "__main__":

    print("\n\n🔷 CASO 1: Consulta informativa")
    resultado1 = consultar_agente(
        "¿Cuál es el porcentaje mínimo de asistencia?",
        student_id="EST001"
    )
    print(f"\nRESPUESTA:\n{resultado1['respuesta']}\n")

    print("\n\n🔷 CASO 2: Situación crítica")
    resultado2 = consultar_agente(
        "Reprobé dos asignaturas. ¿Qué pasa conmigo?",
        student_id="EST002"
    )
    print(f"\nRESPUESTA:\n{resultado2['respuesta']}\n")

    print("\n\n🔷 CASO 3: Segunda consulta de EST001 (prueba memoria)")
    resultado3 = consultar_agente(
        "¿Qué pasa si falto más de lo permitido?",
        student_id="EST001"
    )
    print(f"\nRESPUESTA:\n{resultado3['respuesta']}\n")