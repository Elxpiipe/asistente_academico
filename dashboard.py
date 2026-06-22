"""
Dashboard de monitoreo y observabilidad del Agente Académico IA.

Ejecutar con: streamlit run dashboard.py

Visualiza:
- IE1: Precisión, consistencia y frecuencia de errores
- IE2: Latencia y uso de recursos
- IE3: Logs y trazabilidad
- IE4: Patrones y anomalías
- IE5: Dashboard visual interactivo
"""

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from observability import obtener_metricas_resumen, obtener_logs_recientes, detectar_anomalias
from security import generar_reporte_seguridad

# ── Configuración ─────────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard Observabilidad — Agente Académico IA",
    page_icon="📊",
    layout="wide",
)

st.markdown("""
<style>
.metric-card {
    background: #f8fafc;
    border-left: 4px solid #4f46e5;
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 8px;
}
.anomalia-box {
    background: #fef2f2;
    border-left: 4px solid #dc2626;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 0.85em;
    margin-top: 4px;
}
.ok-box {
    background: #f0fdf4;
    border-left: 4px solid #16a34a;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 0.85em;
    margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)

# ── Encabezado ────────────────────────────────────────────────────
try:
    st.image("OR_Logotipo_DuocUC.jpg", width=200)
except Exception:
    pass

st.title("📊 Dashboard de Observabilidad")
st.caption("Monitoreo en tiempo real del Agente Asesor Académico IA — ISY0101 DuocUC")

# ── Botón de refresco ─────────────────────────────────────────────
col_ref, _ = st.columns([1, 5])
with col_ref:
    if st.button("🔄 Actualizar datos"):
        st.rerun()

st.divider()

# ── Cargar métricas ───────────────────────────────────────────────
metricas = obtener_metricas_resumen()

if metricas["total_ejecuciones"] == 0:
    st.warning("⚠️ No hay datos de observabilidad aún. Realiza algunas consultas al agente primero.")
    st.stop()

# ══════════════════════════════════════════════════════════════════
# SECCIÓN 1: KPIs principales
# ══════════════════════════════════════════════════════════════════
st.subheader("📈 Métricas Generales")

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.metric("Total Ejecuciones", metricas["total_ejecuciones"])

with c2:
    color = "normal" if metricas["tasa_exito"] >= 80 else "inverse"
    st.metric("Tasa de Éxito", f"{metricas['tasa_exito']}%",
              delta=f"{metricas['tasa_exito']-100:.1f}%" if metricas["tasa_exito"] < 100 else "✓ Sin errores")

with c3:
    st.metric("Latencia Promedio", f"{metricas['latencia_promedio_ms']:.0f} ms",
              delta=f"Max: {metricas['latencia_max_ms']:.0f}ms", delta_color="inverse")

with c4:
    st.metric("CPU Promedio", f"{metricas['cpu_promedio']}%")

with c5:
    st.metric("Memoria Promedio", f"{metricas['memoria_promedio_mb']:.0f} MB",
              delta=f"Max: {metricas['memoria_max_mb']:.0f}MB", delta_color="inverse")

st.divider()

# ══════════════════════════════════════════════════════════════════
# SECCIÓN 2: Latencia y Recursos (IE2)
# ══════════════════════════════════════════════════════════════════
st.subheader("⏱️ Latencia y Uso de Recursos (IE2)")

col_lat, col_rec = st.columns(2)

with col_lat:
    # Gráfico de latencia por herramienta
    herramientas = ["Clasificación", "Consulta RAG", "Análisis Riesgo", "Generación Doc"]
    latencias = [
        metricas["latencia_clasificacion_ms"],
        metricas["latencia_consulta_ms"],
        metricas["latencia_analisis_ms"],
        metricas["latencia_generacion_ms"],
    ]
    colores = ["#6366f1", "#0ea5e9", "#f59e0b", "#10b981"]

    fig_lat = go.Figure(go.Bar(
        x=herramientas,
        y=latencias,
        marker_color=colores,
        text=[f"{v:.0f}ms" for v in latencias],
        textposition="outside",
    ))
    fig_lat.update_layout(
        title="Latencia promedio por herramienta (ms)",
        yaxis_title="Milisegundos",
        plot_bgcolor="white",
        height=320,
        margin=dict(t=40, b=20),
    )
    st.plotly_chart(fig_lat, use_container_width=True)

with col_rec:
    # Gráfico de tendencia de latencia en últimas ejecuciones
    ultimas = metricas["ultimas_ejecuciones"]
    if ultimas:
        df_trend = pd.DataFrame(ultimas, columns=["timestamp", "latencia_ms", "exitoso", "riesgo", "categoria"])
        df_trend["timestamp"] = pd.to_datetime(df_trend["timestamp"])
        df_trend = df_trend.sort_values("timestamp")
        df_trend["color"] = df_trend["exitoso"].map({1: "Exitoso", 0: "Error"})

        fig_trend = px.line(
            df_trend, x="timestamp", y="latencia_ms",
            color="color",
            color_discrete_map={"Exitoso": "#4f46e5", "Error": "#dc2626"},
            markers=True,
            title="Tendencia de latencia (últimas ejecuciones)",
            labels={"latencia_ms": "Latencia (ms)", "timestamp": "Tiempo"},
        )
        fig_trend.update_layout(
            plot_bgcolor="white", height=320,
            margin=dict(t=40, b=20), legend_title="Estado"
        )
        st.plotly_chart(fig_trend, use_container_width=True)

st.divider()

# ══════════════════════════════════════════════════════════════════
# SECCIÓN 3: Precisión y Consistencia (IE1)
# ══════════════════════════════════════════════════════════════════
st.subheader("🎯 Precisión, Consistencia y Errores (IE1)")

col_riesgo, col_cat, col_err = st.columns(3)

with col_riesgo:
    # Distribución de riesgo detectado
    dist_riesgo = metricas["dist_riesgo"]
    if dist_riesgo:
        colores_riesgo = {
            "BAJO": "#16a34a", "MEDIO": "#d97706",
            "ALTO": "#dc2626", "ERROR": "#6b7280", "N/A": "#94a3b8"
        }
        fig_riesgo = go.Figure(go.Pie(
            labels=list(dist_riesgo.keys()),
            values=list(dist_riesgo.values()),
            marker_colors=[colores_riesgo.get(k, "#94a3b8") for k in dist_riesgo.keys()],
            hole=0.4,
        ))
        fig_riesgo.update_layout(
            title="Distribución de Riesgo Detectado",
            height=280, margin=dict(t=40, b=0)
        )
        st.plotly_chart(fig_riesgo, use_container_width=True)

with col_cat:
    # Distribución de categorías
    dist_cat = metricas["dist_categoria"]
    if dist_cat:
        colores_cat = {
            "informativa": "#6366f1", "situacional": "#f59e0b",
            "critica": "#dc2626", "desconocida": "#94a3b8"
        }
        fig_cat = go.Figure(go.Pie(
            labels=list(dist_cat.keys()),
            values=list(dist_cat.values()),
            marker_colors=[colores_cat.get(k, "#94a3b8") for k in dist_cat.keys()],
            hole=0.4,
        ))
        fig_cat.update_layout(
            title="Distribución de Categorías",
            height=280, margin=dict(t=40, b=0)
        )
        st.plotly_chart(fig_cat, use_container_width=True)

with col_err:
    # Tasa de éxito vs error
    fig_exito = go.Figure(go.Pie(
        labels=["Exitosas", "Con Error"],
        values=[metricas["total_ejecuciones"] - metricas["total_errores"],
                metricas["total_errores"]],
        marker_colors=["#16a34a", "#dc2626"],
        hole=0.4,
    ))
    fig_exito.update_layout(
        title="Tasa de Éxito vs Error",
        height=280, margin=dict(t=40, b=0)
    )
    st.plotly_chart(fig_exito, use_container_width=True)

    # Errores por tipo
    if metricas["errores_por_tipo"]:
        st.markdown("**Errores por tipo:**")
        for tipo, cnt in metricas["errores_por_tipo"]:
            st.markdown(
                f'<div class="anomalia-box">🔴 <b>{tipo}</b>: {cnt} ocurrencia(s)</div>',
                unsafe_allow_html=True
            )

st.divider()

# ══════════════════════════════════════════════════════════════════
# SECCIÓN 4: Patrones y Anomalías (IE4)
# ══════════════════════════════════════════════════════════════════
st.subheader("🔍 Patrones y Anomalías Detectadas (IE4)")

col_anom, col_tools = st.columns(2)

with col_anom:
    anomalias = detectar_anomalias()
    if anomalias:
        st.markdown(f"**{len(anomalias)} anomalía(s) detectada(s):**")
        for a in anomalias:
            st.markdown(
                f'<div class="anomalia-box">'
                f'<b>{a["tipo"]}</b> — {a["timestamp"]}<br>'
                f'Estudiante: {a["student_id"]} | {a["detalle"]}'
                f'</div>',
                unsafe_allow_html=True
            )
    else:
        st.markdown(
            '<div class="ok-box">✅ No se detectaron anomalías en los registros.</div>',
            unsafe_allow_html=True
        )

    # Anomalías de latencia desde métricas
    if metricas["anomalias_latencia"]:
        st.markdown("**Ejecuciones con latencia anómala (>2x promedio):**")
        for a in metricas["anomalias_latencia"]:
            st.markdown(
                f'<div class="anomalia-box">'
                f'⚠️ {a["timestamp"]} — {a["latencia"]}ms | Categoría: {a["categoria"]}'
                f'</div>',
                unsafe_allow_html=True
            )

with col_tools:
    # Herramientas más usadas
    if metricas["herramientas_uso"]:
        df_tools = pd.DataFrame(metricas["herramientas_uso"], columns=["Combinación", "Usos"])
        fig_tools = px.bar(
            df_tools, x="Usos", y="Combinación",
            orientation="h",
            color="Usos",
            color_continuous_scale="Blues",
            title="Patrones de uso de herramientas",
        )
        fig_tools.update_layout(
            plot_bgcolor="white", height=280,
            margin=dict(t=40, b=20), showlegend=False
        )
        st.plotly_chart(fig_tools, use_container_width=True)

st.divider()

# ══════════════════════════════════════════════════════════════════
# SECCIÓN 5: Trazabilidad y Logs (IE3)
# ══════════════════════════════════════════════════════════════════
st.subheader("📋 Trazabilidad y Logs de Ejecución (IE3)")

logs = obtener_logs_recientes(limite=50)

if logs:
    df_logs = pd.DataFrame(logs, columns=[
        "Timestamp", "Paso", "Herramienta", "Duración (ms)",
        "Estado", "Detalle", "Estudiante", "Consulta"
    ])
    df_logs["Timestamp"] = pd.to_datetime(df_logs["Timestamp"]).dt.strftime("%H:%M:%S")
    df_logs["Duración (ms)"] = df_logs["Duración (ms)"].round(0)

    # Filtros
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        estados = ["Todos"] + list(df_logs["Estado"].unique())
        estado_sel = st.selectbox("Filtrar por estado", estados)
    with col_f2:
        herramientas = ["Todas"] + [h for h in df_logs["Herramienta"].unique() if h]
        herr_sel = st.selectbox("Filtrar por herramienta", herramientas)
    with col_f3:
        estudiantes = ["Todos"] + [e for e in df_logs["Estudiante"].unique() if e]
        est_sel = st.selectbox("Filtrar por estudiante", estudiantes)

    # Aplicar filtros
    df_filtrado = df_logs.copy()
    if estado_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Estado"] == estado_sel]
    if herr_sel != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Herramienta"] == herr_sel]
    if est_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Estudiante"] == est_sel]

    # Colorear filas por estado
    def color_estado(val):
        if val == "ERROR":
            return "background-color: #fef2f2; color: #991b1b"
        elif val == "OK":
            return "background-color: #f0fdf4; color: #166534"
        return ""

    st.dataframe(
        df_filtrado[["Timestamp", "Paso", "Herramienta", "Duración (ms)", "Estado", "Detalle", "Estudiante"]],
        use_container_width=True,
        height=350,
    )
    st.caption(f"Mostrando {len(df_filtrado)} de {len(df_logs)} registros")
else:
    st.info("No hay logs de trazabilidad disponibles aún.")

st.divider()

# ══════════════════════════════════════════════════════════════════
# SECCIÓN 6: Últimas ejecuciones
# ══════════════════════════════════════════════════════════════════
st.subheader("🕐 Últimas Ejecuciones")

try:
    conn = sqlite3.connect("agent_memory.db")
    df_exec = pd.read_sql_query("""
        SELECT timestamp, student_id, consulta, categoria,
               latencia_total_ms, riesgo_detectado, herramientas_usadas,
               num_iteraciones, exitoso
        FROM metricas_ejecucion
        ORDER BY timestamp DESC
        LIMIT 15
    """, conn)
    conn.close()

    if not df_exec.empty:
        df_exec["timestamp"] = pd.to_datetime(df_exec["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
        df_exec["latencia_total_ms"] = df_exec["latencia_total_ms"].round(0)
        df_exec["exitoso"] = df_exec["exitoso"].map({1: "✅", 0: "❌"})
        df_exec.columns = ["Timestamp", "Estudiante", "Consulta", "Categoría",
                           "Latencia (ms)", "Riesgo", "Herramientas", "Iteraciones", "Estado"]
        df_exec["Consulta"] = df_exec["Consulta"].str[:50] + "..."
        st.dataframe(df_exec, use_container_width=True, height=300)
except Exception as e:
    st.error(f"Error cargando ejecuciones: {e}")

# ══════════════════════════════════════════════════════════════════
# SECCIÓN 7: Seguridad y Uso Responsable (IE6)
# ══════════════════════════════════════════════════════════════════
st.subheader("🔒 Seguridad y Uso Responsable (IE6)")

reporte_seg = generar_reporte_seguridad()

col_s1, col_s2 = st.columns(2)

with col_s1:
    st.markdown("**Protocolos implementados:**")
    protocolos = [
        ("✅", "Sanitización de inputs", "Detección de prompt injection y caracteres peligrosos"),
        ("✅", "Anonimización en logs", "RUT, email y tokens se enmascaran automáticamente"),
        ("✅", "Validación de ID estudiante", "Solo caracteres alfanuméricos permitidos (máx. 20 chars)"),
        ("✅", "Límite de uso diario", f"Máximo {reporte_seg.get('limite_diario', 50)} consultas por estudiante/día"),
        ("✅", "Truncado de consultas", f"Máximo {reporte_seg.get('max_chars', 500)} caracteres por consulta"),
        ("✅", "Contexto académico", "Bloqueo de temas fuera del dominio académico"),
    ]
    for icono, nombre, desc in protocolos:
        st.markdown(
            f'<div class="ok-box">{icono} <b>{nombre}</b><br><small>{desc}</small></div>',
            unsafe_allow_html=True
        )

with col_s2:
    st.markdown("**Actividad de uso (últimas 24h):**")
    st.metric("Consultas hoy", reporte_seg.get("total_hoy", 0))
    if reporte_seg.get("top_estudiantes"):
        st.markdown("**Top estudiantes por consultas:**")
        for student, cnt in reporte_seg["top_estudiantes"]:
            porcentaje = round(cnt / reporte_seg.get("limite_diario", 50) * 100, 1)
            st.progress(min(porcentaje / 100, 1.0), text=f"{student}: {cnt} consultas ({porcentaje}% del límite)")

st.divider()

# ── Footer ────────────────────────────────────────────────────────
st.divider()
st.caption("📊 Dashboard de Observabilidad — Agente Académico IA | ISY0101 DuocUC 2026 | Felipe Véliz · Patricio Azolas")