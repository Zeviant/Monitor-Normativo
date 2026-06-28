# Monitor Normativo

Dashboard en Streamlit que analiza logs técnicos de reportes CRC y los convierte en explicaciones claras para equipos legales y de cumplimiento.

<img src="assets/readme/dashboard.png" alt="Dashboard principal" width="900">

## Qué resuelve

| Problema | Solución |
|---|---|
| Los reportes CRC fallan por datos inconsistentes. | El sistema clasifica cada incidencia por severidad y tipo. |
| Legal no entiende mensajes técnicos como `Violación de unicidad`. | Ollama genera una explicación simple con impacto y acción recomendada. |
| Revisar logs manualmente toma tiempo. | El dashboard resume, filtra, prioriza y exporta resultados. |

## Stack

| Componente | Uso |
|---|---|
| Python | Procesamiento, reglas, RAG simple y conexión con Ollama. |
| Streamlit | Interfaz, filtros, gráficas y selección de incidencias. |
| Ollama | Ejecución local del modelo Llama 3.2. |

## Arquitectura

<img src="assets/readme/arquitectura.png" alt="Arquitectura del sistema" width="760">

## Flujo del sistema

| Paso | Archivo | Resultado |
|---:|---|---|
| 1 | `generate_dataset.py` | Genera 100 registros CRC sintéticos. |
| 2 | `main.py` | Carga el CSV generado o uno subido por el usuario. |
| 3 | `compliance_rules.py` | Asigna severidad, tipo de incidencia y acción base. |
| 4 | `knowledge_base.py` + `knowledge_base/*.md` | Recupera documentos internos relevantes mediante mini RAG. |
| 5 | `ollama_client.py` | Envía el prompt a Ollama y recibe la explicación. |
| 6 | `reporting.py` | Exporta CSV analizado y resumen ejecutivo. |

## Interfaz

| Vista | Captura |
|---|---|
| Modelo local | <img src="assets/readme/modelo-local.png" alt="Modelo local" width="320"> |
| Modo de explicación | <img src="assets/readme/modo-explicacion.png" alt="Modo de explicación" width="320"> |
| Tabla de registros | <img src="assets/readme/tabla-registros.png" alt="Tabla de registros" width="520"> |
| Incidencias frecuentes | <img src="assets/readme/incidencias-frecuentes.png" alt="Incidencias frecuentes" width="520"> |
| Inspector de entrada | <img src="assets/readme/inspector.png" alt="Inspector" width="520"> |
| Explicación generada | <img src="assets/readme/explicacion-ia.png" alt="Explicación IA" width="520"> |

## Técnicas de IA

| Técnica | Uso en el proyecto |
|---|---|
| CRISPE | Estructura el prompt con contexto, rol, intención, pasos, presentación y evaluación. |
| Two-shot prompting | Incluye dos ejemplos para guiar tono, formato y nivel de detalle. |
| Mini RAG | Puntúa documentos `.md` por coincidencias y agrega el contexto más relevante al prompt. |
| Self-consistency ligera | En modo mejorado, genera varias alternativas y muestra la más clara. |

## Datos sintéticos

`generate_dataset.py` crea un dataset reproducible en `data/synthetic_compliance_logs.csv`.

| Tipo de registro | Cantidad |
|---|---:|
| Reportes válidos | 40 |
| Errores técnicos clasificados | 58 |
| Errores desconocidos | 2 |
| Total | 100 |

Columnas esperadas:

```text
fecha_hora, id_reporte, entidad, fuente, codigo_error, mensaje_tecnico
```

## Ejecutar

```powershell
python -m pip install -r requirements.txt
python generate_dataset.py
streamlit run main.py
```

## Ollama

La app usa modelos locales de Ollama. El usuario puede elegir cualquier modelo descargado; si no tiene ninguno, puede descargar `llama3.2:latest` desde la interfaz.

```powershell
ollama pull llama3.2
ollama serve
```

## Estructura

```text
main.py                 Interfaz principal
charts.py               Métricas y gráficas
compliance_rules.py     Reglas de clasificación
knowledge_base.py       Mini RAG
knowledge_base/*.md     Documentos internos consultados por el RAG
ollama_client.py        Prompt y conexión con Ollama
reporting.py            Exportación de reportes
generate_dataset.py     Datos sintéticos
config.py               Configuración base
```
