"""Crea registros normativos sintéticos y reproducibles para pruebas."""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


random.seed(42)
OUTPUT = Path(__file__).parent / "data" / "synthetic_compliance_logs.csv"

CASES = [
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

ENTITIES = ["Comercial Norte", "Finanzas Contoso", "Grupo Alpino", "Industrias Fabrikam"]
SOURCES = ["Portal CRC", "Importación por lotes", "API del regulador"]
START = datetime(2026, 6, 1, 8, 0)


def build_rows() -> list[dict[str, str]]:
    rows = []
    # Garantiza que cada error y caso límite aparezca al menos una vez.
    # A balanced demo: 24 valid reports, every edge case, and only two unknowns.
    expanded = CASES + [CASES[0]] * 23 + [random.choice(CASES[1:15]) for _ in range(32)]
    random.shuffle(expanded)
    for number, (scenario, message) in enumerate(expanded, start=1):
        timestamp = (START + timedelta(hours=number * 4)).isoformat(timespec="minutes")
        report_id = f"CRC-2026-{number:04d}"
        if scenario == "MISSING_REPORT_ID":
            report_id = ""
        if scenario == "MALFORMED_TIMESTAMP":
            timestamp = "not-a-date"
        if scenario == "DUPLICATE_REPORT":
            report_id = "CRC-2026-0001"
        rows.append(
            {
                "fecha_hora": timestamp,
                "id_reporte": report_id,
                "entidad": random.choice(ENTITIES),
                "fuente": random.choice(SOURCES),
                "codigo_error": scenario,
                "mensaje_tecnico": message,
            }
        )
    return rows


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    with OUTPUT.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Se crearon {len(rows)} registros sintéticos en {OUTPUT}")


if __name__ == "__main__":
    main()
