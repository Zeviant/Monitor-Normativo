from pathlib import Path
import json

import altair as alt
import pandas as pd
import requests
import streamlit as st


DATA_FILE = Path(__file__).parent / "data" / "synthetic_compliance_logs.csv"
OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2:latest"

ERROR_CATALOG = {
    "OK": ("Válido", "Sin incidencias", "No se requiere ninguna acción."),
    "MISSING_TAX_ID": (
        "Crítica", "Dato obligatorio ausente", "Añada la identificación fiscal correcta y vuelva a enviar el reporte."
    ),
    "INVALID_TAX_ID": (
        "Alta", "Identificador inválido", "Verifique la identificación fiscal de la entidad en el registro oficial."
    ),
    "INVALID_DATE": (
        "Alta", "Fecha inválida", "Corrija la fecha al formato AAAA-MM-DD y vuelva a enviar el reporte."
    ),
    "FUTURE_DATE": (
        "Alta", "Período de reporte inválido", "Revise la fecha de la transacción y el período reportado."
    ),
    "LATE_SUBMISSION": (
        "Alta", "Plazo de presentación", "Confirme si se requiere una corrección o notificación por presentación tardía."
    ),
    "TOTAL_MISMATCH": (
        "Crítica", "Inconsistencia financiera", "Concilie los importes antes de volver a enviar el reporte."
    ),
    "NEGATIVE_AMOUNT": (
        "Media", "Importe inválido", "Compruebe si es un error o si debe declararse como un ajuste."
    ),
    "INVALID_AMOUNT": (
        "Alta", "Importe ilegible", "Sustitúyalo por un importe numérico válido."
    ),
    "DUPLICATE_REPORT": (
        "Media", "Posible duplicado", "Confirme la presentación anterior antes de enviar otra copia."
    ),
    "MISSING_REPORT_ID": (
        "Crítica", "Referencia de reporte ausente", "Asigne el identificador correcto y procese de nuevo la entrada."
    ),
    "MALFORMED_TIMESTAMP": (
        "Media", "Fecha y hora ilegibles", "Corrija la fecha y hora y verifique la secuencia de presentación."
    ),
    "CONNECTION_TIMEOUT": (
        "Baja", "Disponibilidad técnica", "Reintente el envío y escale el incidente si el servicio sigue sin responder."
    ),
    "MALFORMED_PAYLOAD": (
        "Alta", "Envío ilegible", "Genere de nuevo el archivo utilizando el esquema requerido."
    ),
    "ENCODING_ERROR": (
        "Media", "Codificación de texto", "Exporte el reporte con codificación UTF-8 y vuelva a enviarlo."
    ),
    "UNKNOWN_ERROR": (
        "Requiere revisión", "Incidencia sin clasificar", "Envíe esta entrada a revisión técnica antes de tomar medidas legales."
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
    df["accion_recomendada"] = details.map(
        lambda value: value[2] if isinstance(value, tuple) else fallback[2]
    )
    df["resultado"] = df["codigo_error"].map(
        lambda code: "Válido" if code == "OK" else "Con incidencias"
    )
    return df


def get_ollama_models() -> list[str]:
    """Devuelve los modelos locales disponibles o una lista vacía si Ollama no responde."""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        response.raise_for_status()
        return [model["name"] for model in response.json().get("models", [])]
    except requests.RequestException:
        return []


def ollama_is_running() -> bool:
    """Comprueba si el servicio local de Ollama está disponible."""
    try:
        return requests.get(f"{OLLAMA_URL}/api/tags", timeout=3).ok
    except requests.RequestException:
        return False


def download_ollama_model(model: str):
    """Descarga un modelo y produce actualizaciones de estado y progreso."""
    with requests.post(
        f"{OLLAMA_URL}/api/pull",
        json={"name": model, "stream": True},
        stream=True,
        timeout=(5, 1800),
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            update = json.loads(line)
            if update.get("error"):
                raise RuntimeError(update["error"])
            total = update.get("total", 0)
            completed = update.get("completed", 0)
            progress = completed / total if total else None
            yield update.get("status", "Descargando..."), progress


def generate_legal_explanation(row: pd.Series, model: str) -> str:
    """Solicita a Ollama una traducción del error técnico para el equipo legal."""
    prompt = f"""# C — Contexto
Un sistema interno procesa reportes de cumplimiento CRC y genera logs técnicos cuando una validación falla. El equipo legal debe comprender el problema y decidir el siguiente paso, pero no tiene conocimientos técnicos. La explicación se utilizará como apoyo interno y no como asesoramiento jurídico definitivo.

# R — Rol
Actúa como especialista interno en cumplimiento normativo con experiencia traduciendo errores de sistemas a lenguaje de negocio simple para equipos legales.

# I — Intención
Transforma el error técnico seleccionado en una explicación breve, comprensible y accionable para el equipo legal. El objetivo es que pueda entender qué sucedió, valorar su posible impacto en cumplimiento y conocer el siguiente paso recomendado.

# S — Separación
1. Lee exclusivamente los datos del log proporcionado.
2. Identifica el problema descrito sin cambiar el tipo ni la severidad aprobados.
3. Interpreta el código y el mensaje técnico usando el tipo de incidencia aprobado, pero nunca copies sus frases literalmente.
4. Explica únicamente el posible impacto para el proceso de cumplimiento.
5. Propón una acción concreta basada en la acción aprobada.
6. Si faltan datos o el error no está claro, indica que se necesita revisión técnica.

Datos que debes analizar:
- Código de error: {row['codigo_error']}
- Mensaje técnico original: {row['mensaje_tecnico']}
- Tipo de incidencia aprobado: {row['tipo_incidencia']}
- Severidad aprobada: {row['severidad']}
- Acción base aprobada: {row['accion_recomendada']}

# P — Presentación
Responde completamente en español, con tono profesional, natural y muy sencillo. Escribe como si se lo explicaras verbalmente a un compañero sin conocimientos de informática. Limita cada apartado a un máximo de dos frases breves y utiliza exactamente esta estructura, sin añadir otros apartados:

**Qué ocurrió:**
[Explicación sencilla]

**Impacto para cumplimiento:**
[Impacto posible]

**Acción recomendada:**
[Siguiente paso concreto]

# E — Evaluación
Antes de responder, comprueba silenciosamente que la salida:
- Sea comprensible para una persona del equipo legal sin conocimientos técnicos.
- No copie ni cite el mensaje técnico: exprese siempre su significado con palabras nuevas y sencillas.
- Utilice palabras cotidianas y frases de aproximadamente 20 palabras o menos.
- Respete el tipo, la severidad y la acción aprobados.
- No invente leyes, artículos, multas, sanciones, fechas límite, obligaciones ni hechos.
- No presente posibilidades como certezas.
- No utilice bajo ninguna circunstancia términos como «unicidad», «violación de unicidad», «restricción», «payload», «checksum», «endpoint» o «timestamp». Sustitúyalos por su significado cotidiano.
- Incluya exactamente los tres encabezados solicitados.
Si alguna condición no se cumple, corrige la respuesta antes de entregarla. No muestres esta evaluación.

# Few-shot — Ejemplos de referencia
Ejemplo 1 — Reporte duplicado
Entrada:
- Código: DUPLICATE_REPORT
- Mensaje: Violación de unicidad para id_reporte

Salida:
**Qué ocurrió**
Este reporte parece haberse enviado anteriormente con el mismo identificador.

**Impacto para cumplimiento**
Enviar otra copia podría duplicar la información o hacer que el sistema rechace el reporte.

**Acción recomendada**
Compruebe la presentación anterior y vuelva a enviarlo solo si es necesario.

Ejemplo 2 — Disponibilidad técnica
Entrada:
- Código: CONNECTION_TIMEOUT
- Mensaje: POST /regulador/envios agotó el tiempo tras 30 s

Salida:
**Qué ocurrió**
El servicio del regulador no respondió dentro del tiempo esperado, por lo que el envío no pudo completarse.

**Impacto para cumplimiento**
El reporte podría seguir pendiente de presentación, aunque este error no indica por sí mismo que sus datos sean incorrectos.

**Acción recomendada**
Reintente el envío y solicite apoyo técnico si el servicio continúa sin responder.

Imita el nivel de sencillez de estos ejemplos. No reutilices la jerga del mensaje técnico en la respuesta final."""
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2},
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["response"].strip()


def load_sample_data() -> pd.DataFrame:
    # The sample is small; reading it again prevents stale data after regeneration.
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
        order = ["Baja", "Media", "Alta", "Crítica", "Requiere revisión"]
        severity_counts = (
            df.loc[df["resultado"] == "Con incidencias", "severidad"]
            .value_counts()
            .reindex(order, fill_value=0)
            .rename_axis("Severidad")
            .to_frame("Entradas")
            .reset_index()
        )
        severity_chart = (
            alt.Chart(severity_counts)
            .mark_bar(color="#D1495B")
            .encode(
                x=alt.X("Severidad:N", sort=order, title=None),
                y=alt.Y("Entradas:Q", title="Entradas"),
                tooltip=["Severidad:N", "Entradas:Q"],
            )
        )
        st.altair_chart(severity_chart, use_container_width=True)

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
        st.caption("Cada registro incluye el código y mensaje generados por el sistema CRC.")
        st.header("Modelo local")
        models = get_ollama_models()
        ollama_running = bool(models) or ollama_is_running()
        if ollama_running and DEFAULT_MODEL not in models:
            selected_model = ""
            st.warning(f"El modelo `{DEFAULT_MODEL}` todavía no está descargado.")
            if st.button("Descargar modelo local", type="primary", use_container_width=True):
                progress_bar = st.progress(0)
                status_text = st.empty()
                try:
                    for status, progress in download_ollama_model(DEFAULT_MODEL):
                        status_text.caption(status)
                        if progress is not None:
                            progress_bar.progress(min(progress, 1.0))
                    st.success("Modelo descargado correctamente.")
                    st.rerun()
                except (requests.RequestException, RuntimeError, ValueError) as exc:
                    st.error(f"No se pudo descargar el modelo: {exc}")
        elif models:
            default_model = models.index(DEFAULT_MODEL) if DEFAULT_MODEL in models else 0
            selected_model = st.selectbox("Modelo de Ollama", models, index=default_model)
            st.success("Ollama conectado")
        else:
            selected_model = ""
            st.warning("Ollama no está instalado o no está activo.")
            st.markdown("[Descargar Ollama](https://ollama.com/download)")
            st.caption("Después de instalarlo, vuelva a cargar esta página para descargar el modelo.")

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
                "codigo_error",
                "mensaje_tecnico",
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
        if row["codigo_error"] == "OK":
            st.success("El reporte superó las validaciones. No necesita explicación adicional.")
        else:
            explanation_key = f"{selected}:{row['codigo_error']}:{row['mensaje_tecnico']}"
            if st.button(
                "Generar explicación con IA",
                type="primary",
                disabled=not selected_model,
                use_container_width=True,
            ):
                try:
                    with st.spinner("Traduciendo el error con el modelo local..."):
                        st.session_state.setdefault("ai_explanations", {})[explanation_key] = (
                            generate_legal_explanation(row, selected_model)
                        )
                except (requests.RequestException, KeyError) as exc:
                    st.error(f"No se pudo generar la explicación: {exc}")

            generated = st.session_state.get("ai_explanations", {}).get(explanation_key)
            if generated:
                st.markdown(generated)
            else:
                st.caption("Pulse el botón para traducir este error a lenguaje de negocio.")

    st.download_button(
        "Descargar resultados analizados",
        filtered.to_csv(index=False).encode("utf-8"),
        file_name="registros_normativos_analizados.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
