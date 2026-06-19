# Monitor Normativo

Prototipo en Streamlit que convierte errores técnicos de reportes CRC en explicaciones y acciones recomendadas comprensibles para los equipos Legal y de Cumplimiento.

## Ejecutar la aplicación

```powershell
python -m pip install -r requirements.txt
python generate_dataset.py
streamlit run main.py
```

La aplicación se abrirá en el navegador. Utiliza por defecto los datos sintéticos incluidos; no requiere información confidencial ni datos de producción.

## Funcionalidades

- Conteo de entradas válidas, problemáticas y críticas
- Gráficos de resultados, severidad y categorías de incidencia
- Explicaciones claras y acciones recomendadas
- Filtros, búsqueda, carga de CSV y descarga de resultados
- Casos límite: identificadores ausentes, fechas e importes inválidos, duplicados, archivos dañados, tiempos de espera, errores de codificación y errores desconocidos

## Columnas esperadas en el CSV

`fecha_hora`, `id_reporte`, `entidad`, `fuente`, `codigo_error`, `mensaje_tecnico`

Este MVP utiliza un catálogo transparente de reglas en lugar de un servicio externo de IA. En producción, ELK podría suministrar los registros y un modelo de lenguaje aprobado podría explicar errores nuevos, manteniendo revisión humana para los casos inciertos.
