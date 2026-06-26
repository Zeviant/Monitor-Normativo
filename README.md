# Monitor Normativo

Prototipo en Streamlit que convierte errores técnicos de reportes CRC en explicaciones y acciones recomendadas comprensibles para los equipos legales.

## Arquitectura del sistema

```text
Usuario legal
      │
      ▼
Streamlit
      │
      ▼
Python
      │
      ▼
Ollama
      │
      ▼
Explicación en Streamlit
```

- **Streamlit:** presenta el dashboard y recibe las acciones del usuario.
- **Python:** procesa los registros, aplica las reglas y coordina el flujo.
- **Ollama:** ejecuta el modelo local que traduce el error técnico.

## Ejecutar la aplicación

```powershell
python -m pip install -r requirements.txt
python generate_dataset.py
streamlit run main.py
```

La aplicación se abrirá en el navegador. Utiliza por defecto los datos sintéticos incluidos.

## Estructura del código

- `main.py`: interfaz principal de Streamlit y flujo de la aplicación.
- `compliance_rules.py`: validación de columnas, catálogo de errores y enriquecimiento de logs.
- `knowledge_base.py`: mini RAG con notas internas recuperadas por código o mensaje.
- `ollama_client.py`: conexión con Ollama, descarga del modelo y generación de explicaciones.
- `charts.py`: métricas y gráficos del dashboard.
- `reporting.py`: generación del resumen ejecutivo descargable.
- `config.py`: rutas y configuración básica del modelo local.
- `generate_dataset.py`: creación del dataset sintético.

## Funcionalidades

- Conteo de entradas válidas, problemáticas y críticas
- Gráficos de resultados, severidad y categorías de incidencia
- Traducción bajo demanda de errores técnicos mediante un modelo local de Ollama
- Modo de explicación rápida o mejorada; la versión mejorada genera varias opciones y conserva la más clara
- Mini RAG con notas internas para dar contexto al modelo antes de generar la explicación
- Severidad y tipo de incidencia controlados por un catálogo de reglas de cumplimiento
- Explicaciones claras y acciones recomendadas para el equipo legal
- Filtros, búsqueda, carga de CSV, descarga del CSV analizado y resumen ejecutivo en Markdown
- Casos límite: identificadores ausentes, fechas e importes inválidos, duplicados, archivos dañados, tiempos de espera, errores de codificación y errores desconocidos

## Datos sintéticos

`generate_dataset.py` crea 100 registros CRC reproducibles mediante una semilla fija:

- 40 reportes válidos
- 58 errores técnicos clasificados
- 2 errores desconocidos para probar la revisión manual

Los resultados se guardan en `data/synthetic_compliance_logs.csv` e incluyen fecha, reporte, entidad, fuente, código de error y mensaje técnico.

## Columnas esperadas en el CSV

`fecha_hora`, `id_reporte`, `entidad`, `fuente`, `codigo_error`, `mensaje_tecnico`

El sistema CRC proporciona el código y mensaje técnico. El catálogo de reglas asigna el tipo, la severidad y una acción aprobada. El mini RAG recupera contexto interno relevante y el modelo local genera la explicación y el posible impacto cuando el usuario lo solicita.

## Estrategia de prompting

El prompt sigue el framework **CRISPE**: Contexto, Rol, Intención, Steps, Presentación y Evaluación. También utiliza **two-shot prompting**, con dos ejemplos completos que muestran al modelo el tono sencillo y la estructura esperada.

La aplicación incluye dos modos:

- **Rápida:** genera una sola explicación usando CRISPE, two-shot prompting y contexto recuperado.
- **Mejorada:** genera varias alternativas internamente y muestra únicamente la más clara para Legal.

## IA local con Ollama

Instale Ollama y descargue un modelo ligero, por ejemplo:

```powershell
ollama pull llama3.2
ollama serve
```

Ollama procesa los logs localmente a través de `http://localhost:11434`; no se necesita una clave de API ni se envían datos a un servicio en la nube.
Si Ollama está activo pero falta `llama3.2`, el panel **Modelo local** permite descargarlo con un botón y muestra el progreso.
