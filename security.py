"""
Protocolos de seguridad y uso responsable del Agente Académico IA.

Implementa:
- Sanitización de inputs (prevención de prompt injection)
- Anonimización de datos sensibles en logs
- Validación de consultas
- Límites de uso por estudiante
- Criterios éticos y de privacidad
"""

import re
import sqlite3
import logging
from datetime import datetime, timedelta

DB_FILE = "agent_memory.db"
logger  = logging.getLogger("AgentSecurity")

# ── CONFIGURACIÓN DE LÍMITES ──────────────────────────────────────

MAX_CHARS_CONSULTA    = 500    # Máximo caracteres por consulta
MAX_CONSULTAS_POR_DIA = 50     # Límite diario por estudiante
MIN_CHARS_CONSULTA    = 3      # Mínimo caracteres


# ── PATRONES DE PROMPT INJECTION ─────────────────────────────────

PATRONES_INJECTION = [
    r"ignore\s+(previous|all|above)\s+instructions?",
    r"forget\s+(everything|all|previous)",
    r"you\s+are\s+now\s+a",
    r"act\s+as\s+(if\s+you\s+are|a)",
    r"jailbreak",
    r"bypass\s+(safety|filter|restriction)",
    r"pretend\s+(you\s+are|to\s+be)",
    r"system\s*prompt",
    r"<\s*script\s*>",
    r"exec\s*\(",
    r"eval\s*\(",
    r"__import__",
    r"ignore las instrucciones",
    r"olvida todo",
    r"ahora eres",
    r"actúa como si fueras",
]

# ── PALABRAS CLAVE FUERA DE CONTEXTO ACADÉMICO ───────────────────

TEMAS_NO_PERMITIDOS = [
    r"\b(hack|crack|exploit|malware|virus)\b",
    r"\b(contraseña|password|credencial)\b",
    r"\b(arma|weapon|bomb|bomba)\b",
]

# ── DATOS SENSIBLES A ANONIMIZAR EN LOGS ─────────────────────────

PATRONES_DATOS_SENSIBLES = {
    "RUT":    r"\b\d{7,8}-[\dkK]\b",
    "EMAIL":  r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "PHONE":  r"\b(\+?56)?[\s-]?[2-9]\d{7,8}\b",
    "TOKEN":  r"\bghp_[A-Za-z0-9]{36}\b",
}


# ── FUNCIONES DE SEGURIDAD ────────────────────────────────────────

def sanitizar_input(texto: str) -> tuple[bool, str, str]:
    """
    Sanitiza el input del usuario.
    Retorna: (es_valido, texto_limpio, mensaje_error)
    """
    if not texto or not texto.strip():
        return False, "", "La consulta no puede estar vacía."

    texto = texto.strip()

    # Validar longitud mínima
    if len(texto) < MIN_CHARS_CONSULTA:
        return False, "", f"La consulta es demasiado corta (mínimo {MIN_CHARS_CONSULTA} caracteres)."

    # Validar longitud máxima
    if len(texto) > MAX_CHARS_CONSULTA:
        logger.warning(f"[SEGURIDAD] Consulta truncada: {len(texto)} chars → {MAX_CHARS_CONSULTA}")
        texto = texto[:MAX_CHARS_CONSULTA] + "..."

    # Detectar prompt injection
    texto_lower = texto.lower()
    for patron in PATRONES_INJECTION:
        if re.search(patron, texto_lower, re.IGNORECASE):
            logger.warning(f"[SEGURIDAD] Prompt injection detectado: '{patron}'")
            return False, "", "⚠️ Consulta no permitida. Por favor realiza preguntas académicas válidas."

    # Detectar temas fuera de contexto
    for patron in TEMAS_NO_PERMITIDOS:
        if re.search(patron, texto_lower, re.IGNORECASE):
            logger.warning(f"[SEGURIDAD] Tema no permitido detectado: '{patron}'")
            return False, "", "⚠️ Esta consulta está fuera del contexto académico del asistente."

    # Eliminar caracteres potencialmente peligrosos
    texto_limpio = re.sub(r"[<>{}|\\^`]", "", texto)

    return True, texto_limpio, ""


def anonimizar_para_log(texto: str) -> str:
    """
    Anonimiza datos sensibles antes de escribirlos en logs (IE6 - privacidad).
    Reemplaza RUT, email, teléfono y tokens con marcadores.
    """
    resultado = texto
    for tipo, patron in PATRONES_DATOS_SENSIBLES.items():
        resultado = re.sub(patron, f"[{tipo}_ANONIMIZADO]", resultado, flags=re.IGNORECASE)
    return resultado


def validar_student_id(student_id: str) -> tuple[bool, str]:
    """
    Valida que el ID de estudiante tenga un formato aceptable.
    Previene inyección SQL y formatos inválidos.
    """
    if not student_id or not student_id.strip():
        return False, "El ID de estudiante no puede estar vacío."

    # Solo permite alfanuméricos, guiones y guiones bajos
    if not re.match(r"^[A-Za-z0-9_\-]{1,20}$", student_id.strip()):
        return False, "ID de estudiante inválido. Use solo letras, números, guiones o guiones bajos (máx. 20 caracteres)."

    return True, ""


def verificar_limite_uso(student_id: str) -> tuple[bool, str]:
    """
    Verifica que el estudiante no haya superado el límite diario de consultas.
    Criterio ético: uso equitativo del sistema (IE6).
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Verificar que la tabla existe
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='estudiante_historico'
        """)
        if not cursor.fetchone():
            conn.close()
            return True, ""

        hace_24h = (datetime.now() - timedelta(hours=24)).isoformat()
        cursor.execute("""
            SELECT COUNT(*) FROM estudiante_historico
            WHERE student_id = ? AND timestamp > ?
        """, (student_id, hace_24h))
        total = cursor.fetchone()[0]
        conn.close()

        if total >= MAX_CONSULTAS_POR_DIA:
            logger.warning(f"[SEGURIDAD] Límite diario alcanzado para: {student_id}")
            return False, f"⚠️ Has alcanzado el límite de {MAX_CONSULTAS_POR_DIA} consultas diarias. Intenta mañana."

        return True, ""

    except Exception as e:
        logger.error(f"[SEGURIDAD] Error verificando límite: {e}")
        return True, ""  # En caso de error, permitir el acceso


def aplicar_protocolos_seguridad(student_id: str, consulta: str) -> tuple[bool, str, str]:
    """
    Punto de entrada único para todos los protocolos de seguridad.
    Retorna: (es_valido, consulta_sanitizada, mensaje_error)

    Orden de verificación:
    1. Validar student_id
    2. Verificar límite de uso
    3. Sanitizar input
    """
    # 1. Validar student_id
    valido, error = validar_student_id(student_id)
    if not valido:
        logger.warning(f"[SEGURIDAD] Student ID inválido: '{student_id}'")
        return False, "", error

    # 2. Verificar límite de uso
    valido, error = verificar_limite_uso(student_id)
    if not valido:
        return False, "", error

    # 3. Sanitizar input
    valido, consulta_limpia, error = sanitizar_input(consulta)
    if not valido:
        return False, "", error

    # Log seguro (anonimizado)
    consulta_log = anonimizar_para_log(consulta_limpia)
    logger.info(f"[SEGURIDAD] Consulta validada | student={student_id} | consulta='{consulta_log[:60]}'")

    return True, consulta_limpia, ""


def generar_reporte_seguridad() -> dict:
    """
    Genera un reporte de eventos de seguridad para el dashboard.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Estudiantes con más consultas hoy
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='estudiante_historico'
        """)
        if not cursor.fetchone():
            conn.close()
            return {"top_estudiantes": [], "total_hoy": 0}

        hace_24h = (datetime.now() - timedelta(hours=24)).isoformat()
        cursor.execute("""
            SELECT student_id, COUNT(*) as cnt
            FROM estudiante_historico
            WHERE timestamp > ?
            GROUP BY student_id
            ORDER BY cnt DESC
            LIMIT 5
        """, (hace_24h,))
        top_estudiantes = cursor.fetchall()

        cursor.execute("""
            SELECT COUNT(*) FROM estudiante_historico
            WHERE timestamp > ?
        """, (hace_24h,))
        total_hoy = cursor.fetchone()[0]

        conn.close()
        return {
            "top_estudiantes": top_estudiantes,
            "total_hoy":       total_hoy,
            "limite_diario":   MAX_CONSULTAS_POR_DIA,
            "max_chars":       MAX_CHARS_CONSULTA,
        }

    except Exception as e:
        logger.error(f"[SEGURIDAD] Error generando reporte: {e}")
        return {"top_estudiantes": [], "total_hoy": 0}