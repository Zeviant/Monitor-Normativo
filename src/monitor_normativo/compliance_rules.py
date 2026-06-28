from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ReglaCumplimiento:
    severidad: str
    tipo_incidencia: str
    accion_recomendada: str


REGLAS_ERRORES = {
    "OK": ReglaCumplimiento("Válido", "Sin incidencias", "No se requiere ninguna acción."),
    "MISSING_TAX_ID": ReglaCumplimiento(
        "Crítica",
        "Dato obligatorio ausente",
        "Añada la identificación fiscal correcta y vuelva a enviar el reporte.",
    ),
    "INVALID_TAX_ID": ReglaCumplimiento(
        "Alta",
        "Identificador inválido",
        "Verifique la identificación fiscal de la entidad en el registro oficial.",
    ),
    "INVALID_DATE": ReglaCumplimiento(
        "Alta",
        "Fecha inválida",
        "Corrija la fecha al formato AAAA-MM-DD y vuelva a enviar el reporte.",
    ),
    "FUTURE_DATE": ReglaCumplimiento(
        "Alta",
        "Período de reporte inválido",
        "Revise la fecha de la transacción y el período reportado.",
    ),
    "LATE_SUBMISSION": ReglaCumplimiento(
        "Alta",
        "Plazo de presentación",
        "Confirme si se requiere una corrección o notificación por presentación tardía.",
    ),
    "TOTAL_MISMATCH": ReglaCumplimiento(
        "Crítica",
        "Inconsistencia financiera",
        "Concilie los importes antes de volver a enviar el reporte.",
    ),
    "NEGATIVE_AMOUNT": ReglaCumplimiento(
        "Media",
        "Importe inválido",
        "Compruebe si es un error o si debe declararse como un ajuste.",
    ),
    "INVALID_AMOUNT": ReglaCumplimiento(
        "Alta",
        "Importe ilegible",
        "Sustitúyalo por un importe numérico válido.",
    ),
    "DUPLICATE_REPORT": ReglaCumplimiento(
        "Media",
        "Posible duplicado",
        "Confirme la presentación anterior antes de enviar otra copia.",
    ),
    "MISSING_REPORT_ID": ReglaCumplimiento(
        "Crítica",
        "Referencia de reporte ausente",
        "Asigne el identificador correcto y procese de nuevo la entrada.",
    ),
    "MALFORMED_TIMESTAMP": ReglaCumplimiento(
        "Media",
        "Fecha y hora ilegibles",
        "Corrija la fecha y hora y verifique la secuencia de presentación.",
    ),
    "CONNECTION_TIMEOUT": ReglaCumplimiento(
        "Baja",
        "Disponibilidad técnica",
        "Reintente el envío y escale el incidente si el servicio sigue sin responder.",
    ),
    "MALFORMED_PAYLOAD": ReglaCumplimiento(
        "Alta",
        "Envío ilegible",
        "Genere de nuevo el archivo utilizando el esquema requerido.",
    ),
    "ENCODING_ERROR": ReglaCumplimiento(
        "Media",
        "Codificación de texto",
        "Exporte el reporte con codificación UTF-8 y vuelva a enviarlo.",
    ),
    "UNKNOWN_ERROR": ReglaCumplimiento(
        "Requiere revisión",
        "Incidencia sin clasificar",
        "Envíe esta entrada a revisión técnica antes de tomar medidas legales.",
    ),
}

COLUMNAS_REQUERIDAS = {
    "fecha_hora",
    "id_reporte",
    "entidad",
    "fuente",
    "codigo_error",
    "mensaje_tecnico",
}


def validar_columnas(datos_originales: pd.DataFrame) -> set[str]:
    """Devuelve las columnas obligatorias ausentes del CSV."""
    return COLUMNAS_REQUERIDAS.difference(datos_originales.columns)


def obtener_regla(codigo_error: str) -> ReglaCumplimiento:
    """Devuelve la regla aprobada para un código de error."""
    return REGLAS_ERRORES.get(codigo_error, REGLAS_ERRORES["UNKNOWN_ERROR"])


def enriquecer_registros(datos_originales: pd.DataFrame) -> pd.DataFrame:
    """Añade campos comprensibles para negocio sin alterar los datos de origen."""
    registros = datos_originales.copy().fillna("")
    registros["codigo_error"] = registros["codigo_error"].astype(str).str.strip().str.upper()
    registros.loc[registros["codigo_error"] == "", "codigo_error"] = "UNKNOWN_ERROR"

    reglas = [obtener_regla(codigo_error) for codigo_error in registros["codigo_error"]]
    registros["severidad"] = [regla.severidad for regla in reglas]
    registros["tipo_incidencia"] = [regla.tipo_incidencia for regla in reglas]
    registros["accion_recomendada"] = [regla.accion_recomendada for regla in reglas]
    registros["resultado"] = registros["codigo_error"].map(
        lambda code: "Válido" if code == "OK" else "Con incidencias"
    )
    return registros
