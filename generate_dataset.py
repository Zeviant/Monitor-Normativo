"""Create deterministic fake compliance logs for demos and testing."""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


random.seed(42)
OUTPUT = Path(__file__).parent / "data" / "synthetic_compliance_logs.csv"

CASES = [
    ("OK", "Validation completed successfully"),
    ("MISSING_TAX_ID", "ValidationError: taxpayer_id is null"),
    ("INVALID_TAX_ID", "taxpayer_id '12-ABC' failed checksum validation"),
    ("INVALID_DATE", "submission_date '20/99/2026' is not ISO-8601"),
    ("FUTURE_DATE", "transaction_date is later than processing date"),
    ("LATE_SUBMISSION", "received_at exceeds statutory deadline by 4 days"),
    ("TOTAL_MISMATCH", "declared_total=9850.00 transaction_sum=9480.00"),
    ("NEGATIVE_AMOUNT", "gross_amount=-450.00 violates minimum 0"),
    ("INVALID_AMOUNT", "could not parse amount value 'nine hundred'"),
    ("DUPLICATE_REPORT", "unique constraint violation on report_id"),
    ("MISSING_REPORT_ID", "report_id was absent from payload"),
    ("MALFORMED_TIMESTAMP", "event timestamp 'yesterday' cannot be parsed"),
    ("CONNECTION_TIMEOUT", "POST /regulator/submissions timed out after 30s"),
    ("MALFORMED_PAYLOAD", "JSONDecodeError: expected comma at line 1 column 84"),
    ("ENCODING_ERROR", "UnicodeDecodeError while reading entity_name"),
    ("NEW_VENDOR_ERROR_777", "unexpected vendor response code 777"),
    ("", "worker stopped without returning an error code"),
]

ENTITIES = ["Northwind Trading", "Contoso Finance", "Alpine Holdings", "Fabrikam Ltd"]
SOURCES = ["CRC Portal", "Batch Import", "Regulator API"]
START = datetime(2026, 6, 1, 8, 0)


def build_rows() -> list[dict[str, str]]:
    rows = []
    # Guarantee that every error and edge case appears at least once.
    expanded = CASES + [random.choice(CASES[:15]) for _ in range(55)]
    random.shuffle(expanded)
    for number, (code, message) in enumerate(expanded, start=1):
        timestamp = (START + timedelta(hours=number * 4)).isoformat(timespec="minutes")
        report_id = f"CRC-2026-{number:04d}"
        if code == "MISSING_REPORT_ID":
            report_id = ""
        if code == "MALFORMED_TIMESTAMP":
            timestamp = "not-a-date"
        rows.append(
            {
                "timestamp": timestamp,
                "report_id": report_id,
                "entity": random.choice(ENTITIES),
                "source": random.choice(SOURCES),
                "error_code": code,
                "technical_message": message,
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
    print(f"Created {len(rows)} synthetic records at {OUTPUT}")


if __name__ == "__main__":
    main()
