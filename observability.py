"""
Sistema de observabilidad, métricas y trazabilidad para el Agente Académico IA.

Métricas implementadas:
- IE1: Precisión, consistencia, frecuencia de errores
- IE2: Latencia por herramienta, uso de CPU y memoria RAM
- IE3: Logs estructurados y trazabilidad de ejecución
"""

import os
import time
import sqlite3
import logging
import traceback
import psutil
from datetime import datetime
from functools import wraps

# ── CONFIGURACIÓN DE LOGS ─────────────────────────────────────────

LOG_FILE = "agent_observability.log"
DB_FILE  = "agent_memory.db"

# Logger estructurado con formato JSON-like para fácil análisis
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AgentObservability")


# ── BASE DE DATOS DE MÉTRICAS ─────────────────────────────────────

def init_observability_db():
    """Crea las tablas de métricas y trazabilidad si no existen."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Tabla de métricas por ejecución
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metricas_ejecucion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            student_id TEXT,
            consulta TEXT,
            categoria TEXT,
            latencia_total_ms REAL,
            latencia_clasificacion_ms REAL,
            latencia_consulta_ms REAL,
            latencia_analisis_ms REAL,
            latencia_generacion_ms REAL,
            cpu_percent REAL,
            memoria_mb REAL,
            riesgo_detectado TEXT,
            herramientas_usadas TEXT,
            num_iteraciones INTEGER,
            exitoso INTEGER DEFAULT 1,
            tipo_error TEXT
        )
    """)

    # Tabla de trazabilidad por paso (IE3)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trazabilidad (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ejecucion_id INTEGER,
            timestamp TEXT NOT NULL,
            paso TEXT NOT NULL,
            herramienta TEXT,
            duracion_ms REAL,
            estado TEXT,
            detalle TEXT,
            FOREIGN KEY (ejecucion_id) REFERENCES metricas_ejecucion(id)
        )
    """)

    # Tabla de errores (IE1 - frecuencia de errores)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registro_errores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            ejecucion_id INTEGER,
            tipo_error TEXT,
            mensaje TEXT,
            traceback TEXT,
            herramienta TEXT,
            FOREIGN KEY (ejecucion_id) REFERENCES metricas_ejecucion(id)
        )
    """)

    # Tabla de consistencia (IE1 - mide si respuestas similares dan resultados similares)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consistencia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            consulta TEXT,
            riesgo_1 TEXT,
            riesgo_2 TEXT,
            es_consistente INTEGER,
            diferencia TEXT
        )
    """)

    conn.commit()
    conn.close()
    logger.info("Base de datos de observabilidad inicializada correctamente.")


# ── CLASE PRINCIPAL DE OBSERVABILIDAD ────────────────────────────

class AgentObserver:
    """
    Observador del agente académico.
    Registra métricas de latencia, recursos, errores y trazabilidad.
    """

    def __init__(self, student_id: str = "anonimo"):
        self.student_id   = student_id
        self.ejecucion_id = None
        self.inicio_total = None
        self.consulta     = ""
        self.categoria    = "desconocida"
        self.metricas     = {
            "latencia_total_ms":          0,
            "latencia_clasificacion_ms":  0,
            "latencia_consulta_ms":       0,
            "latencia_analisis_ms":       0,
            "latencia_generacion_ms":     0,
            "cpu_percent":                0,
            "memoria_mb":                 0,
            "herramientas_usadas":        [],
            "num_iteraciones":            0,
            "exitoso":                    1,
            "tipo_error":                 None,
        }
        self.trazas = []
        init_observability_db()

    def iniciar_ejecucion(self, consulta: str, categoria: str = "desconocida"):
        """Marca el inicio de una ejecución y captura recursos iniciales."""
        self.inicio_total = time.time()
        self.consulta     = consulta
        self.categoria    = categoria

        # Capturar uso de recursos al inicio (IE2)
        proceso = psutil.Process(os.getpid())
        self.metricas["memoria_mb"]  = proceso.memory_info().rss / 1024 / 1024
        self.metricas["cpu_percent"] = psutil.cpu_percent(interval=0.1)

        logger.info(f"[INICIO] student={self.student_id} | consulta='{consulta[:60]}' | "
                    f"memoria={self.metricas['memoria_mb']:.1f}MB | cpu={self.metricas['cpu_percent']}%")

        self._registrar_traza("INICIO_EJECUCION", detalle=f"Consulta recibida: {consulta[:80]}")

    def registrar_paso(self, paso: str, herramienta: str = None, duracion_ms: float = 0,
                       estado: str = "OK", detalle: str = ""):
        """Registra un paso individual en la traza de ejecución (IE3)."""
        self.trazas.append({
            "timestamp":   datetime.now().isoformat(),
            "paso":        paso,
            "herramienta": herramienta or "",
            "duracion_ms": round(duracion_ms, 2),
            "estado":      estado,
            "detalle":     detalle[:200],
        })
        logger.info(f"[PASO] {paso} | herramienta={herramienta} | "
                    f"duracion={duracion_ms:.0f}ms | estado={estado}")

    def registrar_latencia(self, tipo: str, ms: float):
        """Registra latencia de una herramienta específica (IE2)."""
        key = f"latencia_{tipo}_ms"
        if key in self.metricas:
            self.metricas[key] = round(ms, 2)
        logger.info(f"[LATENCIA] {tipo}={ms:.0f}ms")

    def registrar_herramienta(self, nombre: str):
        """Registra qué herramientas fueron usadas en esta ejecución."""
        if nombre not in self.metricas["herramientas_usadas"]:
            self.metricas["herramientas_usadas"].append(nombre)
        self.metricas["num_iteraciones"] += 1

    def registrar_error(self, tipo_error: str, mensaje: str, herramienta: str = None):
        """Registra un error ocurrido durante la ejecución (IE1 - frecuencia de errores)."""
        self.metricas["exitoso"]    = 0
        self.metricas["tipo_error"] = tipo_error
        tb = traceback.format_exc()

        logger.error(f"[ERROR] tipo={tipo_error} | herramienta={herramienta} | mensaje={mensaje}")

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO registro_errores
            (timestamp, ejecucion_id, tipo_error, mensaje, traceback, herramienta)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), self.ejecucion_id, tipo_error, mensaje, tb, herramienta or ""))
        conn.commit()
        conn.close()

        self._registrar_traza(f"ERROR_{tipo_error}", herramienta=herramienta,
                               estado="ERROR", detalle=mensaje[:200])

    def finalizar_ejecucion(self, riesgo: str = "BAJO"):
        """Calcula métricas finales y guarda todo en la base de datos."""
        if self.inicio_total:
            self.metricas["latencia_total_ms"] = round(
                (time.time() - self.inicio_total) * 1000, 2
            )

        # Capturar recursos al final (IE2)
        proceso = psutil.Process(os.getpid())
        self.metricas["memoria_mb"]  = proceso.memory_info().rss / 1024 / 1024
        self.metricas["cpu_percent"] = psutil.cpu_percent(interval=0.1)

        logger.info(f"[FIN] latencia_total={self.metricas['latencia_total_ms']}ms | "
                    f"riesgo={riesgo} | exitoso={self.metricas['exitoso']} | "
                    f"herramientas={self.metricas['herramientas_usadas']}")

        # Guardar métricas en DB
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO metricas_ejecucion (
                timestamp, student_id, consulta, categoria,
                latencia_total_ms, latencia_clasificacion_ms,
                latencia_consulta_ms, latencia_analisis_ms, latencia_generacion_ms,
                cpu_percent, memoria_mb, riesgo_detectado,
                herramientas_usadas, num_iteraciones, exitoso, tipo_error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            self.student_id,
            self.consulta[:300],
            self.categoria,
            self.metricas["latencia_total_ms"],
            self.metricas["latencia_clasificacion_ms"],
            self.metricas["latencia_consulta_ms"],
            self.metricas["latencia_analisis_ms"],
            self.metricas["latencia_generacion_ms"],
            self.metricas["cpu_percent"],
            self.metricas["memoria_mb"],
            riesgo,
            ",".join(self.metricas["herramientas_usadas"]),
            self.metricas["num_iteraciones"],
            self.metricas["exitoso"],
            self.metricas["tipo_error"],
        ))
        self.ejecucion_id = cursor.lastrowid

        # Guardar trazas (IE3)
        for traza in self.trazas:
            cursor.execute("""
                INSERT INTO trazabilidad
                (ejecucion_id, timestamp, paso, herramienta, duracion_ms, estado, detalle)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                self.ejecucion_id,
                traza["timestamp"],
                traza["paso"],
                traza["herramienta"],
                traza["duracion_ms"],
                traza["estado"],
                traza["detalle"],
            ))

        conn.commit()
        conn.close()
        self._registrar_traza("FIN_EJECUCION", detalle=f"Riesgo={riesgo} | "
                              f"Latencia={self.metricas['latencia_total_ms']}ms")

    def _registrar_traza(self, paso: str, herramienta: str = None,
                         estado: str = "OK", detalle: str = ""):
        self.trazas.append({
            "timestamp":   datetime.now().isoformat(),
            "paso":        paso,
            "herramienta": herramienta or "",
            "duracion_ms": 0,
            "estado":      estado,
            "detalle":     detalle,
        })


# ── MÉTRICAS AGREGADAS (para el dashboard) ────────────────────────

def obtener_metricas_resumen() -> dict:
    """
    Calcula métricas agregadas para el dashboard (IE1, IE2, IE4).
    Incluye promedios, tendencias y detección de anomalías.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Verificar que la tabla existe
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='metricas_ejecucion'
    """)
    if not cursor.fetchone():
        conn.close()
        return _metricas_vacias()

    # Total de ejecuciones
    cursor.execute("SELECT COUNT(*) FROM metricas_ejecucion")
    total = cursor.fetchone()[0]
    if total == 0:
        conn.close()
        return _metricas_vacias()

    # Latencia promedio total (IE2)
    cursor.execute("SELECT AVG(latencia_total_ms), MIN(latencia_total_ms), MAX(latencia_total_ms) FROM metricas_ejecucion WHERE exitoso=1")
    lat = cursor.fetchone()

    # Latencia por herramienta (IE2)
    cursor.execute("SELECT AVG(latencia_consulta_ms), AVG(latencia_analisis_ms), AVG(latencia_generacion_ms), AVG(latencia_clasificacion_ms) FROM metricas_ejecucion")
    lat_tools = cursor.fetchone()

    # Tasa de error (IE1)
    cursor.execute("SELECT COUNT(*) FROM metricas_ejecucion WHERE exitoso=0")
    errores = cursor.fetchone()[0]

    # Frecuencia de errores por tipo (IE1)
    cursor.execute("""
        SELECT tipo_error, COUNT(*) as cnt
        FROM registro_errores
        GROUP BY tipo_error
        ORDER BY cnt DESC LIMIT 5
    """)
    errores_por_tipo = cursor.fetchall()

    # Distribución de riesgo (IE1 - consistencia)
    cursor.execute("""
        SELECT riesgo_detectado, COUNT(*) as cnt
        FROM metricas_ejecucion
        GROUP BY riesgo_detectado
    """)
    dist_riesgo = dict(cursor.fetchall())

    # Distribución de categorías (IE4 - patrones)
    cursor.execute("""
        SELECT categoria, COUNT(*) as cnt
        FROM metricas_ejecucion
        GROUP BY categoria
        ORDER BY cnt DESC
    """)
    dist_categoria = dict(cursor.fetchall())

    # Uso de recursos promedio (IE2)
    cursor.execute("SELECT AVG(cpu_percent), AVG(memoria_mb), MAX(memoria_mb) FROM metricas_ejecucion")
    recursos = cursor.fetchone()

    # Últimas 10 ejecuciones para gráfico de tendencia (IE4)
    cursor.execute("""
        SELECT timestamp, latencia_total_ms, exitoso, riesgo_detectado, categoria
        FROM metricas_ejecucion
        ORDER BY timestamp DESC LIMIT 20
    """)
    ultimas = cursor.fetchall()

    # Herramientas más usadas (IE4 - patrones)
    cursor.execute("""
        SELECT herramientas_usadas, COUNT(*) as cnt
        FROM metricas_ejecucion
        GROUP BY herramientas_usadas
        ORDER BY cnt DESC
    """)
    herramientas_uso = cursor.fetchall()

    # Consistencia: consultas similares con mismo riesgo (IE1)
    cursor.execute("""
        SELECT COUNT(*) FROM metricas_ejecucion
        WHERE exitoso=1 AND riesgo_detectado IS NOT NULL
    """)
    total_con_riesgo = cursor.fetchone()[0]

    conn.close()

    tasa_error = round((errores / total) * 100, 1) if total > 0 else 0
    tasa_exito = round(100 - tasa_error, 1)

    # Detectar anomalías (IE4): latencia > 2x promedio
    lat_prom = lat[0] or 0
    anomalias = []
    for row in ultimas:
        if row[1] and row[1] > max(lat_prom * 2, 10000):
            anomalias.append({
                "timestamp": row[0][:16],
                "latencia":  round(row[1]),
                "categoria": row[4],
            })

    return {
        "total_ejecuciones":    total,
        "tasa_exito":           tasa_exito,
        "tasa_error":           tasa_error,
        "total_errores":        errores,
        "errores_por_tipo":     errores_por_tipo,
        "latencia_promedio_ms": round(lat[0] or 0, 1),
        "latencia_min_ms":      round(lat[1] or 0, 1),
        "latencia_max_ms":      round(lat[2] or 0, 1),
        "latencia_consulta_ms": round(lat_tools[0] or 0, 1),
        "latencia_analisis_ms": round(lat_tools[1] or 0, 1),
        "latencia_generacion_ms": round(lat_tools[2] or 0, 1),
        "latencia_clasificacion_ms": round(lat_tools[3] or 0, 1),
        "cpu_promedio":         round(recursos[0] or 0, 1),
        "memoria_promedio_mb":  round(recursos[1] or 0, 1),
        "memoria_max_mb":       round(recursos[2] or 0, 1),
        "dist_riesgo":          dist_riesgo,
        "dist_categoria":       dist_categoria,
        "herramientas_uso":     herramientas_uso,
        "ultimas_ejecuciones":  ultimas,
        "anomalias_latencia":   anomalias,
        "total_con_riesgo":     total_con_riesgo,
    }


def obtener_logs_recientes(limite: int = 50) -> list:
    """Retorna los logs más recientes para análisis de trazabilidad (IE3)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT t.timestamp, t.paso, t.herramienta, t.duracion_ms, t.estado, t.detalle,
                   m.student_id, m.consulta
            FROM trazabilidad t
            LEFT JOIN metricas_ejecucion m ON t.ejecucion_id = m.id
            ORDER BY t.timestamp DESC
            LIMIT ?
        """, (limite,))
        rows = cursor.fetchall()
    except Exception:
        rows = []
    conn.close()
    return rows


def detectar_anomalias() -> list:
    """
    Detecta anomalías en los registros del agente (IE4).
    Criterios: latencia alta, errores repetidos, inconsistencia de riesgo.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    anomalias = []

    try:
        # Latencia > umbral (2000ms)
        cursor.execute("""
            SELECT timestamp, student_id, consulta, latencia_total_ms
            FROM metricas_ejecucion
            WHERE latencia_total_ms > 10000
            ORDER BY timestamp DESC LIMIT 10
        """)
        for row in cursor.fetchall():
            anomalias.append({
                "tipo":       "⚠️ Latencia Alta (>10s)",
                "timestamp":  row[0][:16],
                "student_id": row[1],
                "detalle":    f"Latencia {row[3]:.0f}ms en: '{row[2][:40]}'"
            })

        # Errores consecutivos del mismo estudiante
        cursor.execute("""
            SELECT student_id, COUNT(*) as cnt
            FROM metricas_ejecucion
            WHERE exitoso=0
            GROUP BY student_id
            HAVING cnt >= 2
        """)
        for row in cursor.fetchall():
            anomalias.append({
                "tipo":       "🔴 Errores Repetidos",
                "timestamp":  datetime.now().isoformat()[:16],
                "student_id": row[0],
                "detalle":    f"{row[1]} errores consecutivos para estudiante {row[0]}"
            })

        # Tasa de error general > 20%
        cursor.execute("SELECT COUNT(*) FROM metricas_ejecucion")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM metricas_ejecucion WHERE exitoso=0")
        errores = cursor.fetchone()[0]
        if total > 0 and (errores / total) > 0.2:
            anomalias.append({
                "tipo":       "🔴 Tasa Error Crítica",
                "timestamp":  datetime.now().isoformat()[:16],
                "student_id": "sistema",
                "detalle":    f"Tasa de error: {errores/total*100:.1f}% (umbral: 20%)"
            })

    except Exception as e:
        logger.error(f"Error en detección de anomalías: {e}")
    finally:
        conn.close()

    return anomalias


def _metricas_vacias() -> dict:
    return {
        "total_ejecuciones": 0, "tasa_exito": 0, "tasa_error": 0,
        "total_errores": 0, "errores_por_tipo": [], "latencia_promedio_ms": 0,
        "latencia_min_ms": 0, "latencia_max_ms": 0, "latencia_consulta_ms": 0,
        "latencia_analisis_ms": 0, "latencia_generacion_ms": 0,
        "latencia_clasificacion_ms": 0, "cpu_promedio": 0,
        "memoria_promedio_mb": 0, "memoria_max_mb": 0,
        "dist_riesgo": {}, "dist_categoria": {}, "herramientas_uso": [],
        "ultimas_ejecuciones": [], "anomalias_latencia": [], "total_con_riesgo": 0,
    }