"""
Interfaz web del Asistente Académico IA — con Agente ReAct.
Ejecutar con: streamlit run app.py
"""

import streamlit as st
from agent import AgenteAcademico
from security import aplicar_protocolos_seguridad

st.set_page_config(
    page_title="Asistente Académico IA",
    page_icon="🎓",
    layout="centered",
)

st.markdown("""
<style>
.iteracion-box {
    background: #f0fdf4;
    border-left: 4px solid #16a34a;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 0.80em;
    color: #14532d !important;
    margin-top: 4px;
}
.riesgo-alto {
    background: #fef2f2;
    border-left: 4px solid #dc2626;
    padding: 10px 14px;
    border-radius: 6px;
    font-size: 0.88em;
    color: #7f1d1d !important;
    margin-top: 8px;
    font-weight: 600;
}
.riesgo-medio {
    background: #fffbeb;
    border-left: 4px solid #d97706;
    padding: 10px 14px;
    border-radius: 6px;
    font-size: 0.88em;
    color: #78350f !important;
    margin-top: 8px;
    font-weight: 600;
}
.riesgo-bajo {
    background: #f0fdf4;
    border-left: 4px solid #16a34a;
    padding: 10px 14px;
    border-radius: 6px;
    font-size: 0.88em;
    color: #14532d !important;
    margin-top: 8px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# ── Encabezado ───────────────────────────────────────────────
try:
    st.image("OR_Logotipo_DuocUC.jpg", width=400)
except Exception:
    pass
st.title("🎓 Asistente Académico IA")
st.caption("Agente inteligente que consulta, analiza y genera documentos — basado en documentos oficiales.")

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuración")
    student_id = st.text_input(
        "ID Estudiante",
        value="EST001",
        help="Ingresa tu RUT o código para que el agente recuerde tus consultas anteriores.",
    )
    mostrar_razonamiento = st.toggle("Mostrar razonamiento del agente", value=False)

    st.divider()

    # ── Historial del estudiante (desde SQLite) ───────────────
    st.markdown("**📋 Historial del estudiante:**")
    try:
        import sqlite3
        conn = sqlite3.connect("agent_memory.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, consulta, riesgo_academico
            FROM estudiante_historico
            WHERE student_id = ?
            ORDER BY timestamp DESC
            LIMIT 10
        """, (student_id,))
        filas = cursor.fetchall()
        conn.close()

        if filas:
            # Traer también la respuesta
            conn2 = sqlite3.connect("agent_memory.db")
            cursor2 = conn2.cursor()
            cursor2.execute("""
                SELECT timestamp, consulta, respuesta, riesgo_academico
                FROM estudiante_historico
                WHERE student_id = ?
                ORDER BY timestamp DESC
                LIMIT 10
            """, (student_id,))
            filas_full = cursor2.fetchall()
            conn2.close()

            for i, (ts, consulta, respuesta, riesgo) in enumerate(filas_full):
                fecha = ts[:10]
                icono = {"ALTO": "🔴", "MEDIO": "🟡", "BAJO": "🟢"}.get(
                    riesgo.upper() if riesgo else "", "⚪"
                )
                with st.expander(f"{icono} {fecha} — {consulta[:30]}..."):
                    st.markdown(f"**Consulta:** {consulta}")
                    st.markdown(f"**Riesgo:** {riesgo or 'N/A'}")
                    st.markdown("**Respuesta:**")
                    st.markdown(respuesta[:400] + ("..." if len(respuesta) > 400 else ""))
                    if st.button("💬 Cargar en chat", key=f"cargar_{i}"):
                        st.session_state.mensajes = [
                            {"tipo": "mensaje", "rol": "user",      "contenido": consulta,  "iteraciones": [], "riesgo": None},
                            {"tipo": "mensaje", "rol": "assistant", "contenido": respuesta, "iteraciones": [], "riesgo": riesgo},
                        ]
                        st.rerun()
        else:
            st.caption("Sin historial aún para este estudiante.")
    except Exception:
        st.caption("No se pudo cargar el historial.")

    st.divider()
    st.markdown("**Ejemplos de consultas:**")
    st.markdown("""
- ¿Cuál es el mínimo de asistencia?
- ¿Cómo se calcula la nota final?
- ¿Qué pasa si repruebo una asignatura?
- Reprobé dos asignaturas, ¿qué hago?
- ¿Cuáles son las fechas importantes del semestre?
    """)
    st.divider()
    if st.button("🗑️ Limpiar conversación"):
        st.session_state.mensajes = []
        st.rerun()

    if st.button("🧹 Limpiar duplicados del historial"):
        try:
            import sqlite3 as _sq
            conn = _sq.connect("agent_memory.db")
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM estudiante_historico
                WHERE id NOT IN (
                    SELECT MIN(id)
                    FROM estudiante_historico
                    GROUP BY student_id, consulta
                )
            """)
            conn.commit()
            conn.close()
            st.success("Duplicados eliminados.")
        except Exception as e:
            st.error(f"Error: {e}")

# ── Inicializar agente ────────────────────────────────────────
if "agente" not in st.session_state or st.session_state.get("student_id_actual") != student_id:
    st.session_state.agente = AgenteAcademico(student_id=student_id)
    st.session_state.student_id_actual = student_id

agente: AgenteAcademico = st.session_state.agente

if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

# ── Labels de documentos ──────────────────────────────────────
labels_doc = {
    "solicitud_entrevista":      "📄 Solicitud de entrevista",
    "constancia_alumno_regular": "📄 Constancia alumno regular",
    "apelacion_nota":            "📄 Apelación de nota",
}

# ── Historial de conversación ────────────────────────────────
for idx, msg in enumerate(st.session_state.mensajes):

    # Mensaje normal (usuario o asistente)
    if msg["tipo"] == "mensaje":
        with st.chat_message(msg["rol"]):
            st.markdown(msg["contenido"])

            if msg["rol"] == "assistant" and mostrar_razonamiento and msg.get("iteraciones"):
                with st.expander("🧠 Ver razonamiento del agente"):
                    for it in msg["iteraciones"]:
                        st.markdown(
                            f'<div class="iteracion-box"><b>{it}</b></div>',
                            unsafe_allow_html=True,
                        )

            if msg["rol"] == "assistant" and msg.get("riesgo"):
                _r     = msg["riesgo"].upper()
                _clase = {"ALTO": "riesgo-alto", "MEDIO": "riesgo-medio", "BAJO": "riesgo-bajo"}.get(_r, "riesgo-bajo")
                _icono = {"ALTO": "🔴", "MEDIO": "🟡", "BAJO": "🟢"}.get(_r, "⚪")
                st.markdown(
                    f'<div class="{_clase}">{_icono} <b>Nivel de riesgo académico: {_r}</b></div>',
                    unsafe_allow_html=True,
                )

    # Mensaje especial: botones de documento
    elif msg["tipo"] == "ofrecer_doc":
        with st.chat_message("assistant"):
            st.markdown("**¿Deseas que genere un documento formal?**")
            cols = st.columns(len(msg["docs"]) + 1)
            for i, doc_tipo in enumerate(msg["docs"]):
                if cols[i].button(labels_doc.get(doc_tipo, doc_tipo), key=f"btn_{idx}_{doc_tipo}"):
                    with st.spinner("📝 Generando documento..."):
                        documento = agente.generar_documento_solicitado(doc_tipo)
                    # Reemplazar este mensaje por el documento generado
                    st.session_state.mensajes[idx] = {
                        "tipo":    "mensaje",
                        "rol":     "assistant",
                        "contenido": f"📄 **{labels_doc.get(doc_tipo, doc_tipo)}**\n\n```\n{documento}\n```",
                        "iteraciones": [],
                        "riesgo":  None,
                    }
                    st.rerun()
            if cols[-1].button("❌ No, gracias", key=f"btn_{idx}_no"):
                st.session_state.mensajes.pop(idx)
                st.rerun()

# ── Input de usuario ──────────────────────────────────────────
if pregunta := st.chat_input("Escribe tu consulta académica..."):

    st.session_state.mensajes.append({
        "tipo": "mensaje", "rol": "user", "contenido": pregunta
    })
    with st.chat_message("user"):
        st.markdown(pregunta)

    with st.chat_message("assistant"):
        with st.spinner("🤖 El agente está analizando tu consulta..."):
            try:
                # ── Protocolos de seguridad (IE6) ────────────────
                es_valido, consulta_segura, error_seg = aplicar_protocolos_seguridad(student_id, pregunta)
                if not es_valido:
                    respuesta_str    = f"🔒 **Consulta bloqueada por seguridad:**\n\n{error_seg}"
                    riesgo           = None
                    ofrece_doc       = False
                    docs_disponibles = []
                    iteraciones      = []
                    st.markdown(respuesta_str)
                else:
                    respuesta_str = agente.procesar_consulta(consulta_segura)

                    riesgo = None
                    for nivel in ["ALTO", "MEDIO", "BAJO"]:
                        if f"Riesgo: {nivel}" in respuesta_str:
                            riesgo = nivel
                            break

                    ofrece_doc = "¿Deseas que genere un documento formal?" in respuesta_str
                    docs_disponibles = [
                        doc for doc in ["solicitud_entrevista", "constancia_alumno_regular", "apelacion_nota"]
                        if doc in respuesta_str
                    ]

                    if analisis_presente := ("ANÁLISIS DE TU SITUACIÓN" in respuesta_str):
                        cat_label = "crítica" if "SITUACIÓN CRÍTICA" in respuesta_str else "situacional"
                        plan_label = f"2 iteraciones — categoría: {cat_label}"
                    else:
                        plan_label = "1 iteración — categoría: informativa"

                    iteraciones = [
                        "Seguridad — Validación y sanitización de input (IE6)",
                        "Memoria — Cargando historial SQLite del estudiante (IE3)",
                        "Memoria — Recuperación semántica con embeddings (IE4)",
                        f"Planificación — {plan_label} (IE5)",
                        "Iteración 1 — Consultando reglamento académico (RAG)",
                        *(["Iteración 2 — Analizando riesgo académico"] if analisis_presente else []),
                        f"Decisión — Riesgo {riesgo or 'BAJO'} → {'Ofrecer documento' if ofrece_doc else 'Respuesta directa'} (IE6)",
                    ]

            except Exception as e:
                respuesta_str    = f"⚠️ Error inesperado: {e}"
                riesgo           = None
                ofrece_doc       = False
                docs_disponibles = []
                iteraciones      = []

        st.markdown(respuesta_str)

        if mostrar_razonamiento:
            with st.expander("🧠 Ver razonamiento del agente"):
                for it in iteraciones:
                    st.markdown(
                        f'<div class="iteracion-box"><b>{it}</b></div>',
                        unsafe_allow_html=True,
                    )

        if riesgo:
            _r     = riesgo.upper()
            _clase = {"ALTO": "riesgo-alto", "MEDIO": "riesgo-medio", "BAJO": "riesgo-bajo"}.get(_r, "riesgo-bajo")
            _icono = {"ALTO": "🔴", "MEDIO": "🟡", "BAJO": "🟢"}.get(_r, "⚪")
            st.markdown(
                f'<div class="{_clase}">{_icono} <b>Nivel de riesgo académico: {_r}</b></div>',
                unsafe_allow_html=True,
            )

    # Guardar respuesta
    st.session_state.mensajes.append({
        "tipo":        "mensaje",
        "rol":         "assistant",
        "contenido":   respuesta_str,
        "iteraciones": iteraciones,
        "riesgo":      riesgo,
    })

    # Si el agente ofrece documento, agregar mensaje especial al historial
    if ofrece_doc and docs_disponibles:
        st.session_state.mensajes.append({
            "tipo": "ofrecer_doc",
            "docs": docs_disponibles,
        })
    
    st.rerun()