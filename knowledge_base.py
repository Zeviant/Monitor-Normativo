import pandas as pd


BASE_CONOCIMIENTO_INTERNA = [
    {
        "title": "Guía interna: identificación fiscal",
        "keywords": ["MISSING_TAX_ID", "INVALID_TAX_ID", "identificación", "fiscal"],
        "content": "Los reportes CRC deben incluir una identificación fiscal clara de la entidad. Si falta o no coincide con el formato esperado, Legal debe pedir corrección antes de considerar el reporte como completo.",
    },
    {
        "title": "Guía interna: fechas y plazos",
        "keywords": ["INVALID_DATE", "FUTURE_DATE", "LATE_SUBMISSION", "fecha", "plazo"],
        "content": "Las fechas permiten confirmar a qué período pertenece el reporte y si fue presentado a tiempo. Fechas ausentes, futuras o tardías requieren revisión antes de continuar.",
    },
    {
        "title": "Guía interna: importes financieros",
        "keywords": ["TOTAL_MISMATCH", "NEGATIVE_AMOUNT", "INVALID_AMOUNT", "importe", "total"],
        "content": "Los importes deben ser legibles y consistentes. Si los totales no cuadran o aparece un valor inesperado, se debe conciliar la información antes de reenviar.",
    },
    {
        "title": "Guía interna: duplicados e identificadores",
        "keywords": ["DUPLICATE_REPORT", "MISSING_REPORT_ID", "duplicado", "id_reporte"],
        "content": "Cada reporte debe poder rastrearse con un identificador único. Si el identificador falta o parece repetido, se debe confirmar el envío anterior y evitar doble presentación.",
    },
    {
        "title": "Guía interna: problemas técnicos de envío",
        "keywords": ["CONNECTION_TIMEOUT", "MALFORMED_PAYLOAD", "ENCODING_ERROR", "envío", "archivo"],
        "content": "Algunos errores provienen del envío o del formato del archivo, no necesariamente del contenido legal. Conviene reintentar, regenerar el archivo o pedir apoyo técnico.",
    },
    {
        "title": "Guía interna: errores desconocidos",
        "keywords": ["UNKNOWN_ERROR", "desconocido", "sin clasificar"],
        "content": "Si el sistema no reconoce el error, no se debe asumir una causa legal. La entrada debe pasar primero por revisión técnica.",
    },
]


def recuperar_contexto_interno(registro: pd.Series) -> str:
    """Mini RAG: recupera notas internas relevantes para enriquecer el prompt."""
    texto_busqueda = f"{registro['codigo_error']} {registro['mensaje_tecnico']} {registro['tipo_incidencia']}".lower()
    coincidencias = []
    for documento in BASE_CONOCIMIENTO_INTERNA:
        if any(palabra_clave.lower() in texto_busqueda for palabra_clave in documento["keywords"]):
            coincidencias.append(f"- {documento['title']}: {documento['content']}")
    return "\n".join(coincidencias[:2]) or "- No hay una guía interna específica; solicitar revisión técnica si el caso no es claro."
