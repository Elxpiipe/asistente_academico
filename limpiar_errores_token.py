"""
Limpia los registros de error generados por token inválido (401 Unauthorized)
de la base de datos de observabilidad.
"""

import sqlite3

DB_FILE = "agent_memory.db"

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# Contar antes
cursor.execute("SELECT COUNT(*) FROM metricas_ejecucion WHERE exitoso=0")
total_errores = cursor.fetchone()[0]
print(f"Errores encontrados: {total_errores}")

# Eliminar ejecuciones fallidas por token (tipo_error = ERROR_GENERAL con latencia 0)
cursor.execute("""
    DELETE FROM metricas_ejecucion
    WHERE exitoso=0 AND latencia_total_ms = 0
""")
eliminados_exec = cursor.rowcount

# Eliminar errores de tipo token/unauthorized
cursor.execute("""
    DELETE FROM registro_errores
    WHERE mensaje LIKE '%401%'
    OR mensaje LIKE '%unauthorized%'
    OR mensaje LIKE '%Bad credentials%'
""")
eliminados_err = cursor.rowcount

# Eliminar trazas huérfanas
cursor.execute("""
    DELETE FROM trazabilidad
    WHERE ejecucion_id NOT IN (SELECT id FROM metricas_ejecucion)
""")
eliminados_trazas = cursor.rowcount

conn.commit()
conn.close()

print(f"✅ Ejecuciones eliminadas: {eliminados_exec}")
print(f"✅ Errores eliminados: {eliminados_err}")
print(f"✅ Trazas huérfanas eliminadas: {eliminados_trazas}")
print("Base de datos limpia.")