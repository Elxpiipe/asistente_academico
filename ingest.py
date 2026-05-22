"""
ingest.py
Carga los PDFs desde /documentos, los fragmenta
y genera el índice vectorial FAISS local.

Ejecutar UNA vez (o cada vez que agregues nuevos documentos):
    python ingest.py
"""

import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

load_dotenv()

print(os.getenv("GITHUB_TOKEN"))

DOCS_DIR        = "documentos"
VECTORSTORE_DIR = "vectorstore"


def get_embeddings():
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=os.getenv("GITHUB_TOKEN"),
        base_url=os.getenv("OPENAI_EMBEDDINGS_URL"),
    )


def cargar_pdfs():
    """Carga todos los PDFs de la carpeta /documentos."""
    documentos = []
    archivos = [f for f in os.listdir(DOCS_DIR) if f.endswith(".pdf")]

    if not archivos:
        print(f"⚠️  No se encontraron PDFs en '{DOCS_DIR}/'.")
        print("    Agrega documentos institucionales (reglamento, calendario, etc.) y vuelve a ejecutar.")
        return []

    for archivo in archivos:
        ruta = os.path.join(DOCS_DIR, archivo)
        print(f"  📄 Cargando: {archivo}")
        loader = PyPDFLoader(ruta)
        documentos.extend(loader.load())

    print(f"\n✅ {len(documentos)} páginas cargadas desde {len(archivos)} archivo(s)")
    return documentos


def fragmentar(documentos):
    """
    Divide los documentos en chunks de 500 caracteres con overlap de 50.
    Estos valores son óptimos para párrafos de reglamentos académicos.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ".", " "],
    )
    fragmentos = splitter.split_documents(documentos)
    print(f"✅ {len(fragmentos)} fragmentos generados")
    return fragmentos


def crear_vectorstore(fragmentos):
    """Genera embeddings y guarda el índice FAISS en disco."""
    print("⏳ Generando embeddings (puede tardar unos segundos)...")
    vectorstore = FAISS.from_documents(fragmentos, get_embeddings())
    vectorstore.save_local(VECTORSTORE_DIR)
    print(f"✅ Vectorstore guardado en '{VECTORSTORE_DIR}/'")


def main():
    print("=" * 50)
    print("  Ingestión de documentos — Asistente Académico")
    print("=" * 50)

    if not os.path.exists(DOCS_DIR):
        os.makedirs(DOCS_DIR)
        print(f"📁 Carpeta '{DOCS_DIR}/' creada.")
        print("   Agrega tus PDFs institucionales y vuelve a ejecutar.")
        return

    documentos = cargar_pdfs()
    if not documentos:
        return

    fragmentos = fragmentar(documentos)
    crear_vectorstore(fragmentos)

    print("\n🎉 ¡Listo! Ahora ejecuta:")
    print("   streamlit run app.py")


if __name__ == "__main__":
    main()
