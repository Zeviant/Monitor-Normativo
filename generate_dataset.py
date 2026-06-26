"""Crea registros normativos sintéticos y reproducibles para pruebas."""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


random.seed(42)
ARCHIVO_SALIDA = Path(__file__).parent / "data" / "synthetic_compliance_logs.csv"

CASOS = [
    ("OK", "Validación completada correctamente"),
    ("MISSING_TAX_ID", "ErrorValidacion: identificacion_fiscal es nula"),
    ("INVALID_TAX_ID", "La identificación fiscal '12-ABC' no superó la validación"),
    ("INVALID_DATE", "La fecha_presentacion '20/99/2026' no cumple ISO-8601"),
    ("FUTURE_DATE", "La fecha_transaccion es posterior a la fecha de procesamiento"),
    ("LATE_SUBMISSION", "La recepción supera el plazo legal por 4 días"),
    ("TOTAL_MISMATCH", "total_declarado=9850.00 suma_transacciones=9480.00"),
    ("NEGATIVE_AMOUNT", "importe_bruto=-450.00 incumple el mínimo de 0"),
    ("INVALID_AMOUNT", "No se pudo interpretar el importe 'novecientos'"),
    ("DUPLICATE_REPORT", "Violación de unicidad para id_reporte"),
    ("MISSING_REPORT_ID", "El id_reporte no estaba presente en el envío"),
    ("MALFORMED_TIMESTAMP", "No se puede interpretar la fecha del evento 'ayer'"),
    ("CONNECTION_TIMEOUT", "POST /regulador/envios agotó el tiempo tras 30 s"),
    ("MALFORMED_PAYLOAD", "ErrorJSON: se esperaba una coma en la línea 1, columna 84"),
    ("ENCODING_ERROR", "ErrorUnicode al leer el nombre de la entidad"),
    ("NEW_VENDOR_ERROR_777", "Respuesta inesperada del proveedor: código 777"),
    ("", "El proceso terminó sin devolver un código de error"),
]

ENTIDADES = ["Comercial Norte", "Finanzas Contoso", "Grupo Alpino", "Industrias Fabrikam"]
FUENTES = ["Portal CRC", "Importación por lotes", "API del regulador"]
FECHA_INICIO = datetime(2026, 6, 1, 8, 0)


def construir_registros() -> list[dict[str, str]]:
    registros = []
    # Garantiza que cada error y caso límite aparezca al menos una vez.
    # Distribución para demo: 40 reportes válidos, todos los casos límite y solo dos desconocidos.
    casos_expandidos = CASOS + [CASOS[0]] * 39 + [random.choice(CASOS[1:15]) for _ in range(44)]
    random.shuffle(casos_expandidos)
    for numero, (escenario, mensaje) in enumerate(casos_expandidos, start=1):
        fecha_hora = (FECHA_INICIO + timedelta(hours=numero * 4)).isoformat(timespec="minutes")
        id_reporte = f"CRC-2026-{numero:04d}"
        if escenario == "MISSING_REPORT_ID":
            id_reporte = ""
        if escenario == "MALFORMED_TIMESTAMP":
            fecha_hora = "not-a-date"
        if escenario == "DUPLICATE_REPORT":
            id_reporte = "CRC-2026-0001"
        registros.append(
            {
                "fecha_hora": fecha_hora,
                "id_reporte": id_reporte,
                "entidad": random.choice(ENTIDADES),
                "fuente": random.choice(FUENTES),
                "codigo_error": escenario,
                "mensaje_tecnico": mensaje,
            }
        )
    return registros


def main() -> None:
    ARCHIVO_SALIDA.parent.mkdir(parents=True, exist_ok=True)
    registros = construir_registros()
    with ARCHIVO_SALIDA.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=registros[0].keys())
        escritor.writeheader()
        escritor.writerows(registros)
    print(f"Se crearon {len(registros)} registros sintéticos en {ARCHIVO_SALIDA}")


if __name__ == "__main__":
    main()
