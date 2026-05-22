"""
rag_chain.py
Pipeline RAG principal usando LangChain moderno (LCEL).
RetrievalQA fue eliminado en versiones recientes, se usa RunnablePassthrough.
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from prompts import get_prompt

load_dotenv()

VECTORSTORE_DIR = "vectorstore"


def get_llm():
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=os.getenv("GITHUB_TOKEN"),
        base_url=os.getenv("OPENAI_BASE_URL"),
    )


def get_embeddings():
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=os.getenv("GITHUB_TOKEN"),
        base_url=os.getenv("OPENAI_EMBEDDINGS_URL"),
    )


def cargar_retriever(k: int = 4):
    if not os.path.exists(VECTORSTORE_DIR):
        raise FileNotFoundError(
            "No se encontró el vectorstore. Ejecuta primero: python ingest.py"
        )
    vectorstore = FAISS.load_local(
        VECTORSTORE_DIR,
        get_embeddings(),
        allow_dangerous_deserialization=True,
    )
    return vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )


def formatear_docs(docs):
    """Une los fragmentos recuperados en un solo texto de contexto."""
    return "\n\n".join(doc.page_content for doc in docs)


def consultar(pregunta: str, tipo_prompt: str = "academico") -> dict:
    retriever = cargar_retriever()
    prompt    = get_prompt(tipo_prompt)

    # Cadena LCEL: recuperar → formatear → prompt → LLM → parsear
    cadena = (
        {
            "context":  retriever | formatear_docs,
            "question": RunnablePassthrough(),
        }
        | prompt
        | get_llm()
        | StrOutputParser()
    )

    respuesta = cadena.invoke(pregunta)

    # Recuperar fuentes por separado para mostrarlas en la interfaz
    docs_recuperados = retriever.invoke(pregunta)
    fuentes = [
        {
            "contenido": doc.page_content[:300],
            "fuente":    doc.metadata.get("source", "desconocido"),
            "pagina":    doc.metadata.get("page", "?"),
        }
        for doc in docs_recuperados
    ]

    return {
        "respuesta": respuesta,
        "fuentes":   fuentes,
    }


# ── Prueba rápida desde consola 
if __name__ == "__main__":
    pregunta = "¿Cuál es el porcentaje mínimo de asistencia requerido?"
    print(f"\n🔍 Pregunta: {pregunta}\n")
    resultado = consultar(pregunta)
    print(f"💬 Respuesta:\n{resultado['respuesta']}\n")
    print("📄 Fuentes:")
    for i, f in enumerate(resultado["fuentes"], 1):
        print(f"  [{i}] {f['fuente']} — pág. {f['pagina']}")