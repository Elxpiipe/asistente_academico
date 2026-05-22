"""
app.py
Interfaz web del Asistente Académico IA.
Ejecutar con: streamlit run app.py
"""

import streamlit as st
from rag_chain import consultar

# ── Configuración ────────────────────────────────────────────
st.set_page_config(
    page_title="Asistente Académico IA",
    page_icon="🎓",
    layout="centered",
)

st.markdown("""
<style>
.fuente-box {
    background: #eef2ff;
    border-left: 4px solid #4f46e5;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 0.82em;
    color: #374151;
    margin-top: 6px;
}
</style>
""", unsafe_allow_html=True)

# ── Encabezado ───────────────────────────────────────────────
st.title("🎓 Asistente Académico IA")
st.caption("Consulta sobre reglamentos, evaluaciones, asistencia y más — basado en documentos oficiales.")

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuración")

    tipo_prompt = st.selectbox(
        "Tipo de prompt",
        options=["academico", "base", "validado"],
        format_func=lambda x: {
            "academico": "🎓 Académico (recomendado)",
            "base":      "📄 Base controlado",
            "validado":  "✅ Con validación",
        }[x],
    )

    mostrar_fuentes = st.toggle("Mostrar fuentes", value=True)

    st.divider()
    st.markdown("**Ejemplos de consultas:**")
    st.markdown("""
- ¿Cuál es el mínimo de asistencia?
- ¿Cómo se calcula la nota final?
- ¿Qué pasa si repruebo una asignatura?
- ¿Cuáles son los requisitos para aprobar?
    """)

# ── Historial de conversación ────────────────────────────────
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

for msg in st.session_state.mensajes:
    with st.chat_message(msg["rol"]):
        st.markdown(msg["contenido"])
        if msg["rol"] == "assistant" and mostrar_fuentes and msg.get("fuentes"):
            with st.expander("📄 Ver fuentes consultadas"):
                for f in msg["fuentes"]:
                    st.markdown(
                        f'<div class="fuente-box">'
                        f'<b>📁 {f["fuente"]}</b> — pág. {f["pagina"]}<br>'
                        f'{f["contenido"][:200]}...'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

# ── Input ─────────────────────────────────────────────────────
if pregunta := st.chat_input("Escribe tu consulta académica..."):

    st.session_state.mensajes.append({"rol": "user", "contenido": pregunta})
    with st.chat_message("user"):
        st.markdown(pregunta)

    with st.chat_message("assistant"):
        with st.spinner("Consultando documentos oficiales..."):
            try:
                resultado  = consultar(pregunta, tipo_prompt)
                respuesta  = resultado["respuesta"]
                fuentes    = resultado["fuentes"]
            except FileNotFoundError as e:
                respuesta = f"⚠️ **Error:** {e}"
                fuentes   = []
            except Exception as e:
                respuesta = f"⚠️ Error inesperado: {e}"
                fuentes   = []

        st.markdown(respuesta)

        if mostrar_fuentes and fuentes:
            with st.expander("📄 Ver fuentes consultadas"):
                for f in fuentes:
                    st.markdown(
                        f'<div class="fuente-box">'
                        f'<b>📁 {f["fuente"]}</b> — pág. {f["pagina"]}<br>'
                        f'{f["contenido"][:200]}...'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

    st.session_state.mensajes.append({
        "rol":      "assistant",
        "contenido": respuesta,
        "fuentes":   fuentes,
    })
