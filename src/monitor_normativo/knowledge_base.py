from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .config import CARPETA_BASE


CARPETA_CONOCIMIENTO = CARPETA_BASE / "knowledge_base"


@dataclass(frozen=True)
class DocumentoConocimiento:
    titulo: str
    palabras_clave: list[str]
    contenido: str


def leer_documento_markdown(ruta: Path) -> DocumentoConocimiento:
    """Lee una nota interna en Markdown con metadatos simples."""
    texto = ruta.read_text(encoding="utf-8").strip()
    metadatos: dict[str, str] = {}
    contenido = texto

    if texto.startswith("---"):
        _, bloque_metadatos, contenido = texto.split("---", 2)
        for linea in bloque_metadatos.strip().splitlines():
            clave, valor = linea.split(":", 1)
            metadatos[clave.strip()] = valor.strip()

    palabras_clave = [
        palabra.strip()
        for palabra in metadatos.get("palabras_clave", "").split(",")
        if palabra.strip()
    ]
    return DocumentoConocimiento(
        titulo=metadatos.get("titulo", ruta.stem.replace("_", " ").title()),
        palabras_clave=palabras_clave,
        contenido=contenido.strip(),
    )


def cargar_documentos_conocimiento() -> list[DocumentoConocimiento]:
    """Carga las notas internas usadas por el mini RAG."""
    return [leer_documento_markdown(ruta) for ruta in sorted(CARPETA_CONOCIMIENTO.glob("*.md"))]


def puntuar_documento(documento: DocumentoConocimiento, texto_busqueda: str) -> int:
    """Calcula relevancia por coincidencias entre palabras clave y el registro seleccionado."""
    puntaje = 0
    for palabra_clave in documento.palabras_clave:
        if palabra_clave.lower() in texto_busqueda:
            puntaje += 2 if palabra_clave.isupper() else 1
    return puntaje


def recuperar_contexto_interno(registro: pd.Series, limite: int = 2) -> str:
    """Mini RAG: recupera las notas internas más relevantes para enriquecer el prompt."""
    texto_busqueda = (
        f"{registro['codigo_error']} "
        f"{registro['mensaje_tecnico']} "
        f"{registro['tipo_incidencia']}"
    ).lower()
    documentos_puntuados = [
        (puntuar_documento(documento, texto_busqueda), documento)
        for documento in cargar_documentos_conocimiento()
    ]
    documentos_relevantes = [
        documento
        for puntaje, documento in sorted(documentos_puntuados, key=lambda item: item[0], reverse=True)
        if puntaje > 0
    ][:limite]

    if not documentos_relevantes:
        return "- No hay una guía interna específica; solicitar revisión técnica si el caso no es claro."

    return "\n\n".join(
        f"**{documento.titulo}**\n\n{documento.contenido.strip()}"
        for documento in documentos_relevantes
    )
