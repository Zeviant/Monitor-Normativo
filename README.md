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

## Funcionalidades

- Conteo de entradas válidas, problemáticas y críticas
- Gráficos de resultados, severidad y categorías de incidencia
- Traducción bajo demanda de errores técnicos mediante un modelo local de Ollama
- Severidad y tipo de incidencia controlados por un catálogo de reglas de cumplimiento
- Explicaciones claras y acciones recomendadas para el equipo legal
- Filtros, búsqueda, carga de CSV y descarga de resultados
- Casos límite: identificadores ausentes, fechas e importes inválidos, duplicados, archivos dañados, tiempos de espera, errores de codificación y errores desconocidos

## Columnas esperadas en el CSV

`fecha_hora`, `id_reporte`, `entidad`, `fuente`, `codigo_error`, `mensaje_tecnico`

El sistema CRC proporciona el código y mensaje técnico. El monitor utiliza reglas aprobadas para asignar el tipo y la severidad, y un modelo local genera una explicación sencilla cuando el usuario la solicita.

## IA local con Ollama

Instale Ollama y descargue un modelo ligero, por ejemplo:

```powershell
ollama pull llama3.2
ollama serve
```

Ollama procesa los logs localmente a través de `http://localhost:11434`; no se necesita una clave de API ni se envían datos a un servicio en la nube.
Si Ollama está activo pero falta `llama3.2`, el panel **Modelo local** permite descargarlo con un botón y muestra el progreso.
