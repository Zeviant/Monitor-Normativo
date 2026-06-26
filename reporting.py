import pandas as pd


def construir_resumen_ejecutivo(registros: pd.DataFrame) -> str:
    """Genera un resumen ejecutivo descargable del estado de los registros filtrados."""
    total = len(registros)
    validos = int((registros["resultado"] == "Válido").sum())
    incidencias = total - validos
    orden_severidad = ["Crítica", "Alta", "Media", "Baja", "Requiere revisión"]
    prioritarios = registros[registros["resultado"] == "Con incidencias"].copy()
    prioritarios["orden_severidad"] = prioritarios["severidad"].map(
        {severidad: indice for indice, severidad in enumerate(orden_severidad)}
    ).fillna(99)
    prioritarios = prioritarios.sort_values(["orden_severidad", "fecha_hora"]).head(10)

    lineas = [
        "# Resumen de Monitor Normativo",
        "",
        f"- Total de entradas analizadas: {total}",
        f"- Reportes válidos: {validos}",
        f"- Reportes con incidencias: {incidencias}",
        "",
        "## Incidencias por severidad",
    ]
    conteo_severidad = registros[registros["resultado"] == "Con incidencias"]["severidad"].value_counts()
    for severidad in ["Baja", "Media", "Alta", "Crítica", "Requiere revisión"]:
        lineas.append(f"- {severidad}: {int(conteo_severidad.get(severidad, 0))}")

    lineas.extend(["", "## Tipos de incidencia más frecuentes"])
    conteo_incidencias = registros[registros["resultado"] == "Con incidencias"]["tipo_incidencia"].value_counts()
    for tipo_incidencia, conteo in conteo_incidencias.head(8).items():
        lineas.append(f"- {tipo_incidencia}: {conteo}")

    lineas.extend(["", "## Casos prioritarios"])
    if prioritarios.empty:
        lineas.append("- No hay incidencias en los filtros actuales.")
    else:
        for _, registro in prioritarios.iterrows():
            id_reporte = registro["id_reporte"] or "(ID ausente)"
            lineas.append(
                f"- {id_reporte}: {registro['severidad']} — {registro['tipo_incidencia']} — {registro['accion_recomendada']}"
            )
    return "\n".join(lineas)
