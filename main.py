from pathlib import Path
import sys

import pandas as pd
import requests
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from monitor_normativo.charts import mostrar_dashboard
from monitor_normativo.compliance_rules import enriquecer_registros, validar_columnas
from monitor_normativo.config import ARCHIVO_DATOS, MODELO_PREDETERMINADO
from monitor_normativo.knowledge_base import recuperar_contexto_interno
from monitor_normativo.ollama_client import (
    descargar_modelo_ollama,
    generar_explicacion_legal,
    obtener_modelos_ollama,
    ollama_esta_activo,
)
from monitor_normativo.reporting import construir_resumen_ejecutivo


COLUMNAS_TABLA = [
    "fecha_hora",
    "id_reporte",
    "entidad",
    "resultado",
    "severidad",
    "tipo_incidencia",
    "codigo_error",
    "mensaje_tecnico",
]

ORDEN_PRIORIDAD = {
    "Crítica": 1,
    "Alta": 2,
    "Media": 3,
    "Baja": 4,
    "Requiere revisión": 5,
}


def cargar_datos_ejemplo() -> pd.DataFrame:
    """Carga el dataset sintético incluido en el proyecto."""
    return pd.read_csv(ARCHIVO_DATOS, dtype=str, keep_default_na=False)


def leer_datos_entrada(archivo_cargado) -> pd.DataFrame:
    """Lee el CSV cargado por el usuario o usa el dataset de ejemplo."""
    if archivo_cargado:
        return pd.read_csv(archivo_cargado, dtype=str, keep_default_na=False)
    return cargar_datos_ejemplo()


def filtrar_registros(registros: pd.DataFrame, filtro_resultado, filtro_severidad, filtro_entidad, busqueda: str) -> pd.DataFrame:
    """Aplica los filtros seleccionados en la barra lateral."""
    filtrados = registros[registros["resultado"].isin(filtro_resultado) & registros["severidad"].isin(filtro_severidad)]
    if filtro_entidad:
        filtrados = filtrados[filtrados["entidad"].isin(filtro_entidad)]
    if busqueda:
        texto_busqueda = filtrados[["id_reporte", "mensaje_tecnico", "entidad"]].astype(str).agg(" ".join, axis=1)
        filtrados = filtrados[texto_busqueda.str.contains(busqueda, case=False, regex=False)]
    return filtrados


def mostrar_configuracion_modelo() -> tuple[str, str]:
    """Muestra la configuración de Ollama y devuelve el modelo y modo seleccionados."""
    st.header("Modelo local")
    modelos = obtener_modelos_ollama()
    ollama_activo = bool(modelos) or ollama_esta_activo()

    if ollama_activo and MODELO_PREDETERMINADO not in modelos:
        modelo_seleccionado = ""
        st.warning(f"El modelo `{MODELO_PREDETERMINADO}` todavía no está descargado.")
        if st.button("Descargar modelo local", type="primary", width="stretch"):
            barra_progreso = st.progress(0)
            texto_estado = st.empty()
            try:
                for estado, progreso in descargar_modelo_ollama(MODELO_PREDETERMINADO):
                    texto_estado.caption(estado)
                    if progreso is not None:
                        barra_progreso.progress(min(progreso, 1.0))
                st.success("Modelo descargado correctamente.")
                st.rerun()
            except (requests.RequestException, RuntimeError, ValueError) as exc:
                st.error(f"No se pudo descargar el modelo: {exc}")
    elif modelos:
        modelo_por_defecto = modelos.index(MODELO_PREDETERMINADO) if MODELO_PREDETERMINADO in modelos else 0
        modelo_seleccionado = st.selectbox("Modelo de Ollama", modelos, index=modelo_por_defecto)
        st.success("Ollama conectado")
    else:
        modelo_seleccionado = ""
        st.warning("Ollama no está instalado o no está activo.")
        st.markdown("[Descargar Ollama](https://ollama.com/download)")
        st.caption("Después de instalarlo, vuelva a cargar esta página para descargar el modelo.")

    st.header("Modo de explicación")
    modo_explicacion = st.radio(
        "Estrategia de IA",
        ["Rápida", "Mejorada"],
        captions=[
            "Una sola respuesta con CRISPE + mini RAG.",
            "Genera varias opciones y conserva la más clara.",
        ],
    )
    return modelo_seleccionado, modo_explicacion


def mostrar_filtros(registros: pd.DataFrame):
    """Muestra filtros y devuelve sus valores."""
    st.header("Filtros")
    filtro_resultado = st.multiselect(
        "Resultado", sorted(registros["resultado"].unique()), default=list(registros["resultado"].unique())
    )
    filtro_severidad = st.multiselect(
        "Severidad", sorted(registros["severidad"].unique()), default=list(registros["severidad"].unique())
    )
    filtro_entidad = st.multiselect("Entidad", sorted(registros["entidad"].unique()))
    busqueda = st.text_input("Buscar reporte o mensaje")
    return filtro_resultado, filtro_severidad, filtro_entidad, busqueda


def mostrar_tabla_registros(registros_filtrados: pd.DataFrame) -> None:
    st.subheader("Entradas de cumplimiento")
    st.dataframe(registros_filtrados[COLUMNAS_TABLA], width="stretch", hide_index=True)


def mostrar_casos_prioritarios(registros_filtrados: pd.DataFrame) -> None:
    st.subheader("Casos prioritarios")
    casos_prioritarios = registros_filtrados.loc[
        registros_filtrados["resultado"] == "Con incidencias"
    ].copy()
    casos_prioritarios["prioridad"] = casos_prioritarios["severidad"].map(ORDEN_PRIORIDAD).fillna(99)
    casos_prioritarios = casos_prioritarios.sort_values(["prioridad", "fecha_hora"]).head(8)

    if casos_prioritarios.empty:
        st.info("No hay incidencias para priorizar con los filtros actuales.")
        return

    st.dataframe(
        casos_prioritarios[
            [
                "id_reporte",
                "entidad",
                "severidad",
                "tipo_incidencia",
                "codigo_error",
            ]
        ],
        width="stretch",
        hide_index=True,
    )


def mostrar_inspector_registro(registros_filtrados: pd.DataFrame, modelo_seleccionado: str, modo_explicacion: str) -> None:
    st.subheader("Inspeccionar una entrada")
    if registros_filtrados.empty:
        st.info("No hay entradas que coincidan con los filtros actuales.")
        return

    seleccionado = st.selectbox(
        "Seleccione un reporte",
        registros_filtrados.index.tolist(),
        format_func=lambda idx: f"{registros_filtrados.loc[idx, 'id_reporte'] or '(ID ausente)'} — {registros_filtrados.loc[idx, 'tipo_incidencia']}",
    )
    registro = registros_filtrados.loc[seleccionado]
    izquierda, derecha = st.columns(2)

    with izquierda:
        st.markdown("**Mensaje técnico original**")
        st.code(registro["mensaje_tecnico"] or "(mensaje vacío)")
        st.write(f"Fuente: {registro['fuente']} · Código de error: `{registro['codigo_error']}`")
        with st.expander("Contexto interno recuperado"):
            st.markdown(recuperar_contexto_interno(registro))

    with derecha:
        st.markdown(f"**{registro['severidad']} — {registro['tipo_incidencia']}**")
        if registro["codigo_error"] == "OK":
            st.success("El reporte superó las validaciones. No necesita explicación adicional.")
            return

        clave_explicacion = f"{seleccionado}:{registro['codigo_error']}:{registro['mensaje_tecnico']}:{modo_explicacion}"
        if st.button(
            "Generar explicación con IA",
            type="primary",
            disabled=not modelo_seleccionado,
            width="stretch",
        ):
            try:
                with st.spinner("Traduciendo el error con el modelo local..."):
                    st.session_state.setdefault("explicaciones_ia", {})[clave_explicacion] = (
                        generar_explicacion_legal(registro, modelo_seleccionado, modo_explicacion)
                    )
            except (requests.RequestException, KeyError) as exc:
                st.error(f"No se pudo generar la explicación: {exc}")

        explicacion_generada = st.session_state.get("explicaciones_ia", {}).get(clave_explicacion)
        if explicacion_generada:
            st.markdown(explicacion_generada)
        else:
            st.caption("Pulse el botón para traducir este error a lenguaje de negocio.")


def mostrar_exportaciones(registros_filtrados: pd.DataFrame) -> None:
    st.subheader("Exportar resultados")
    izquierda, derecha = st.columns(2)
    with izquierda:
        st.download_button(
            "Descargar CSV analizado",
            registros_filtrados.to_csv(index=False).encode("utf-8"),
            file_name="registros_normativos_analizados.csv",
            mime="text/csv",
            width="stretch",
        )
    with derecha:
        st.download_button(
            "Descargar resumen ejecutivo",
            construir_resumen_ejecutivo(registros_filtrados).encode("utf-8"),
            file_name="resumen_monitor_normativo.md",
            mime="text/markdown",
            width="stretch",
        )


def main() -> None:
    st.set_page_config(page_title="Monitor Normativo", page_icon="🏢", layout="wide")
    st.title("🏢 Monitor Normativo")
    st.write("Errores técnicos traducidos en acciones claras de cumplimiento para el equipo legal.")

    with st.sidebar:
        st.header("Fuente de datos")
        archivo_cargado = st.file_uploader("Cargar un archivo de registros", type=["csv"])
        st.caption("Cada registro incluye el código y mensaje generados por el sistema CRC.")
        modelo_seleccionado, modo_explicacion = mostrar_configuracion_modelo()

    try:
        datos_originales = leer_datos_entrada(archivo_cargado)
    except Exception as exc:
        st.error(f"No se pudo leer el archivo CSV: {exc}")
        st.stop()

    columnas_ausentes = validar_columnas(datos_originales)
    if columnas_ausentes:
        st.error("Faltan columnas obligatorias en el CSV: " + ", ".join(sorted(columnas_ausentes)))
        st.stop()

    registros = enriquecer_registros(datos_originales)

    with st.sidebar:
        filtros = mostrar_filtros(registros)

    registros_filtrados = filtrar_registros(registros, *filtros)
    mostrar_dashboard(registros_filtrados)
    mostrar_tabla_registros(registros_filtrados)
    mostrar_casos_prioritarios(registros_filtrados)
    mostrar_inspector_registro(registros_filtrados, modelo_seleccionado, modo_explicacion)
    mostrar_exportaciones(registros_filtrados)


if __name__ == "__main__":
    main()
