from pathlib import Path


CARPETA_BASE = Path(__file__).resolve().parents[2]
ARCHIVO_DATOS = CARPETA_BASE / "data" / "synthetic_compliance_logs.csv"

URL_OLLAMA = "http://localhost:11434"
MODELO_PREDETERMINADO = "llama3.2:latest"
