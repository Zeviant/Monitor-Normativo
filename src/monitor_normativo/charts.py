import altair as alt
import pandas as pd
import streamlit as st


def mostrar_dashboard(registros: pd.DataFrame) -> None:
    total = len(registros)
    validos = int((registros["resultado"] == "Válido").sum())
    incidencias = total - validos
    criticos = int((registros["severidad"] == "Crítica").sum())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de entradas", f"{total:,}")
    col2.metric("Válidas", f"{validos:,}")
    col3.metric("Con incidencias", f"{incidencias:,}")
    col4.metric("Críticas", f"{criticos:,}")

    st.subheader("Resumen")
    chart1, chart2 = st.columns(2)
    with chart1:
        st.caption("Resultado de validación")
        conteo_resultados = registros["resultado"].value_counts().rename_axis("Resultado").to_frame("Entradas")
        st.bar_chart(conteo_resultados, color="#2E86AB")
    with chart2:
        st.caption("Incidencias por severidad")
        orden = ["Baja", "Media", "Alta", "Crítica", "Requiere revisión"]
        conteo_severidad = (
            registros.loc[registros["resultado"] == "Con incidencias", "severidad"]
            .value_counts()
            .reindex(orden, fill_value=0)
            .rename_axis("Severidad")
            .to_frame("Entradas")
            .reset_index()
        )
        grafico_severidad = (
            alt.Chart(conteo_severidad)
            .mark_bar(color="#D1495B")
            .encode(
                x=alt.X("Severidad:N", sort=orden, title=None),
                y=alt.Y("Entradas:Q", title="Entradas", axis=alt.Axis(tickMinStep=1, format="d")),
                tooltip=["Severidad:N", "Entradas:Q"],
            )
        )
        st.altair_chart(grafico_severidad, use_container_width=True)

    st.caption("Tipos de incidencia más frecuentes")
    conteo_incidencias = (
        registros.loc[registros["resultado"] == "Con incidencias", "tipo_incidencia"]
        .value_counts()
        .head(10)
        .rename_axis("Incidencia")
        .to_frame("Entradas")
        .reset_index()
        .sort_values("Entradas", ascending=False)
    )
    grafico_incidencias = (
        alt.Chart(conteo_incidencias)
        .mark_bar(color="#F4A261")
        .encode(
            x=alt.X("Entradas:Q", title="Entradas", axis=alt.Axis(tickMinStep=1, format="d")),
            y=alt.Y("Incidencia:N", sort="-x", title=None),
            tooltip=["Incidencia:N", "Entradas:Q"],
        )
    )
    st.altair_chart(grafico_incidencias, use_container_width=True)
