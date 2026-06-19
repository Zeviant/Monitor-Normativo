from pathlib import Path

import pandas as pd
import streamlit as st


DATA_FILE = Path(__file__).parent / "data" / "synthetic_compliance_logs.csv"

ERROR_CATALOG = {
    "OK": (
        "Válido",
        "Sin incidencias",
        "El reporte superó todas las validaciones automáticas.",
        "No se requiere ninguna acción.",
    ),
    "MISSING_TAX_ID": (
        "Crítica",
        "Dato obligatorio ausente",
        "No se puede identificar a la entidad regulada porque falta su identificación fiscal.",
        "Añada la identificación fiscal correcta y vuelva a enviar el reporte.",
    ),
    "INVALID_TAX_ID": (
        "Alta",
        "Identificador inválido",
        "La identificación fiscal proporcionada no cumple con el formato aceptado.",
        "Verifique la identificación fiscal de la entidad en el registro oficial.",
    ),
    "INVALID_DATE": (
        "Alta",
        "Fecha inválida",
        "Falta una fecha o utiliza un formato que el sistema no acepta.",
        "Corrija la fecha al formato AAAA-MM-DD y vuelva a enviar el reporte.",
    ),
    "FUTURE_DATE": (
        "Alta",
        "Período de reporte inválido",
        "El reporte contiene una fecha de transacción futura.",
        "Revise la fecha de la transacción y el período reportado.",
    ),
    "LATE_SUBMISSION": (
        "Alta",
        "Plazo de presentación",
        "El reporte se recibió después del plazo de cumplimiento.",
        "Confirme si se requiere una corrección o notificación por presentación tardía.",
    ),
    "TOTAL_MISMATCH": (
        "Crítica",
        "Inconsistencia financiera",
        "El total declarado no coincide con la suma de las transacciones.",
        "Concilie los importes antes de volver a enviar el reporte.",
    ),
    "NEGATIVE_AMOUNT": (
        "Media",
        "Importe inválido",
        "Un valor que debe ser igual o mayor que cero fue enviado como importe negativo.",
        "Compruebe si es un error o si debe declararse como un ajuste.",
    ),
    "INVALID_AMOUNT": (
        "Alta",
        "Importe ilegible",
        "Un campo financiero contiene texto o un formato numérico no admitido.",
        "Sustitúyalo por un importe numérico válido.",
    ),
    "DUPLICATE_REPORT": (
        "Media",
        "Posible duplicado",
        "Parece que ya se presentó un reporte con el mismo identificador.",
        "Confirme la presentación anterior antes de enviar otra copia.",
    ),
    "MISSING_REPORT_ID": (
        "Crítica",
        "Referencia de reporte ausente",
        "La entrada no tiene un identificador de reporte y no puede rastrearse ni auditarse correctamente.",
        "Asigne el identificador correcto y procese de nuevo la entrada.",
    ),
    "MALFORMED_TIMESTAMP": (
        "Media",
        "Fecha y hora ilegibles",
        "El sistema no puede determinar cuándo ocurrió el evento.",
        "Corrija la fecha y hora y verifique la secuencia de presentación.",
    ),
    "CONNECTION_TIMEOUT": (
        "Baja",
        "Disponibilidad técnica",
        "El servicio del regulador no respondió; los datos del reporte podrían ser correctos.",
        "Reintente el envío y escale el incidente si el servicio sigue sin responder.",
    ),
    "MALFORMED_PAYLOAD": (
        "Alta",
        "Envío ilegible",
        "El archivo o mensaje está dañado o no sigue la estructura requerida.",
        "Genere de nuevo el archivo utilizando el esquema requerido.",
    ),
    "ENCODING_ERROR": (
        "Media",
        "Codificación de texto",
        "Algunos nombres o descripciones contienen caracteres que el sistema receptor no puede leer.",
        "Exporte el reporte con codificación UTF-8 y vuelva a enviarlo.",
    ),
    "UNKNOWN_ERROR": (
        "Requiere revisión",
        "Incidencia sin clasificar",
        "El sistema encontró un error que todavía no figura en el catálogo de reglas.",
        "Envíe esta entrada a revisión técnica antes de tomar medidas legales.",
    ),
}

REQUIRED_COLUMNS = {
    "fecha_hora",
    "id_reporte",
    "entidad",
    "fuente",
    "codigo_error",
    "mensaje_tecnico",
}

LEGACY_COLUMNS = {
    "timestamp": "fecha_hora",
    "report_id": "id_reporte",
    "entity": "entidad",
    "source": "fuente",
    "error_code": "codigo_error",
    "technical_message": "mensaje_tecnico",
}


def enrich_logs(raw: pd.DataFrame) -> pd.DataFrame:
    """Añade campos comprensibles para negocio sin alterar los datos de origen."""
    df = raw.copy().fillna("")
    df = df.rename(columns=LEGACY_COLUMNS)
    df["codigo_error"] = df["codigo_error"].astype(str).str.strip().str.upper()
    df.loc[df["codigo_error"] == "", "codigo_error"] = "UNKNOWN_ERROR"

    details = df["codigo_error"].map(ERROR_CATALOG)
    fallback = ERROR_CATALOG["UNKNOWN_ERROR"]
    df["severidad"] = details.map(lambda value: value[0] if isinstance(value, tuple) else fallback[0])
    df["tipo_incidencia"] = details.map(lambda value: value[1] if isinstance(value, tuple) else fallback[1])
    df["explicacion_negocio"] = details.map(
        lambda value: value[2] if isinstance(value, tuple) else fallback[2]
    )
    df["accion_recomendada"] = details.map(
        lambda value: value[3] if isinstance(value, tuple) else fallback[3]
    )
    df["resultado"] = df["codigo_error"].map(
        lambda code: "Válido" if code == "OK" else "Con incidencias"
    )
    return df


@st.cache_data
def load_sample_data() -> pd.DataFrame:
    return pd.read_csv(DATA_FILE, dtype=str, keep_default_na=False)


def show_dashboard(df: pd.DataFrame) -> None:
    total = len(df)
    valid = int((df["resultado"] == "Válido").sum())
    issues = total - valid
    critical = int((df["severidad"] == "Crítica").sum())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de entradas", f"{total:,}")
    col2.metric("Válidas", f"{valid:,}")
    col3.metric("Con incidencias", f"{issues:,}")
    col4.metric("Críticas", f"{critical:,}")

    st.subheader("Resumen")
    chart1, chart2 = st.columns(2)
    with chart1:
        st.caption("Resultado de validación")
        result_counts = df["resultado"].value_counts().rename_axis("Resultado").to_frame("Entradas")
        st.bar_chart(result_counts, color="#2E86AB")
    with chart2:
        st.caption("Incidencias por severidad")
        order = ["Crítica", "Alta", "Media", "Baja", "Requiere revisión"]
        severity_counts = (
            df.loc[df["resultado"] == "Con incidencias", "severidad"]
            .value_counts()
            .reindex(order, fill_value=0)
            .rename_axis("Severidad")
            .to_frame("Entradas")
        )
        st.bar_chart(severity_counts, color="#D1495B")

    st.caption("Tipos de incidencia más frecuentes")
    issue_counts = (
        df.loc[df["resultado"] == "Con incidencias", "tipo_incidencia"]
        .value_counts()
        .head(10)
        .sort_values()
        .rename_axis("Incidencia")
        .to_frame("Entradas")
    )
    st.bar_chart(issue_counts, horizontal=True, color="#F4A261")


def main() -> None:
    st.set_page_config(page_title="Monitor Normativo", page_icon="🏢", layout="wide")
    st.title("🏢 Monitor Normativo")
    st.write("Errores técnicos traducidos en acciones claras de cumplimiento para el equipo legal.")

    with st.sidebar:
        st.header("Fuente de datos")
        uploaded = st.file_uploader("Cargar un archivo de registros", type=["csv"])
        st.caption("Use los datos de ejemplo incluidos o cargue un CSV con las mismas columnas.")

    try:
        raw = pd.read_csv(uploaded, dtype=str, keep_default_na=False) if uploaded else load_sample_data()
    except Exception as exc:
        st.error(f"No se pudo leer el archivo CSV: {exc}")
        st.stop()

    available_columns = set(raw.columns) | {LEGACY_COLUMNS[col] for col in raw.columns if col in LEGACY_COLUMNS}
    missing = REQUIRED_COLUMNS.difference(available_columns)
    if missing:
        st.error("Faltan columnas obligatorias en el CSV: " + ", ".join(sorted(missing)))
        st.stop()

    df = enrich_logs(raw)

    with st.sidebar:
        st.header("Filtros")
        result_filter = st.multiselect(
            "Resultado", sorted(df["resultado"].unique()), default=list(df["resultado"].unique())
        )
        severity_filter = st.multiselect(
            "Severidad", sorted(df["severidad"].unique()), default=list(df["severidad"].unique())
        )
        entity_filter = st.multiselect("Entidad", sorted(df["entidad"].unique()))
        search = st.text_input("Buscar reporte o mensaje")

    filtered = df[df["resultado"].isin(result_filter) & df["severidad"].isin(severity_filter)]
    if entity_filter:
        filtered = filtered[filtered["entidad"].isin(entity_filter)]
    if search:
        searchable = filtered[["id_reporte", "mensaje_tecnico", "entidad"]].astype(str).agg(" ".join, axis=1)
        filtered = filtered[searchable.str.contains(search, case=False, regex=False)]

    show_dashboard(filtered)

    st.subheader("Entradas de cumplimiento")
    st.dataframe(
        filtered[
            [
                "fecha_hora",
                "id_reporte",
                "entidad",
                "resultado",
                "severidad",
                "tipo_incidencia",
                "explicacion_negocio",
                "accion_recomendada",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Inspeccionar una entrada")
    if filtered.empty:
        st.info("No hay entradas que coincidan con los filtros actuales.")
        return
    choices = filtered.index.tolist()
    selected = st.selectbox(
        "Seleccione un reporte",
        choices,
        format_func=lambda idx: f"{filtered.loc[idx, 'id_reporte'] or '(ID ausente)'} — {filtered.loc[idx, 'tipo_incidencia']}",
    )
    row = filtered.loc[selected]
    left, right = st.columns(2)
    with left:
        st.markdown("**Mensaje técnico original**")
        st.code(row["mensaje_tecnico"] or "(mensaje vacío)")
        st.write(f"Fuente: {row['fuente']} · Código de error: `{row['codigo_error']}`")
    with right:
        st.markdown(f"**{row['severidad']} — {row['tipo_incidencia']}**")
        st.write(row["explicacion_negocio"])
        st.info("Acción recomendada: " + row["accion_recomendada"])

    st.download_button(
        "Descargar resultados analizados",
        filtered.to_csv(index=False).encode("utf-8"),
        file_name="registros_normativos_analizados.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
