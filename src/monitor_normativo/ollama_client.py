import json
import re

import pandas as pd
import requests

from .config import URL_OLLAMA
from .knowledge_base import recuperar_contexto_interno


def obtener_modelos_ollama() -> list[str]:
    """Devuelve los modelos locales disponibles o una lista vacía si Ollama no responde."""
    try:
        respuesta = requests.get(f"{URL_OLLAMA}/api/tags", timeout=3)
        respuesta.raise_for_status()
        return [modelo["name"] for modelo in respuesta.json().get("models", [])]
    except requests.RequestException:
        return []


def ollama_esta_activo() -> bool:
    """Comprueba si el servicio local de Ollama está disponible."""
    try:
        return requests.get(f"{URL_OLLAMA}/api/tags", timeout=3).ok
    except requests.RequestException:
        return False


def descargar_modelo_ollama(modelo: str):
    """Descarga un modelo y produce actualizaciones de estado y progreso."""
    with requests.post(
        f"{URL_OLLAMA}/api/pull",
        json={"name": modelo, "stream": True},
        stream=True,
        timeout=(5, 1800),
    ) as respuesta:
        respuesta.raise_for_status()
        for linea in respuesta.iter_lines():
            if not linea:
                continue
            actualizacion = json.loads(linea)
            if actualizacion.get("error"):
                raise RuntimeError(actualizacion["error"])
            total = actualizacion.get("total", 0)
            completado = actualizacion.get("completed", 0)
            progreso = completado / total if total else None
            yield actualizacion.get("status", "Descargando..."), progreso


def consultar_ollama(prompt: str, modelo: str, temperatura: float = 0.2, tiempo_espera: int = 120) -> str:
    """Envía un prompt a Ollama y devuelve la respuesta del modelo."""
    respuesta = requests.post(
        f"{URL_OLLAMA}/api/generate",
        json={
            "model": modelo,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperatura},
        },
        timeout=tiempo_espera,
    )
    respuesta.raise_for_status()
    return respuesta.json()["response"].strip()


def normalizar_formato_explicacion(texto: str) -> str:
    """Unifica los encabezados de la respuesta generada por el modelo."""
    encabezados = [
        ("Qué ocurrió", r"Qu[eé]\s+ocurri[oó]"),
        ("Impacto para cumplimiento", r"Impacto\s+para\s+cumplimiento"),
        ("Acción recomendada", r"Acci[oó]n\s+recomendada"),
    ]
    texto_normalizado = texto.strip()
    for encabezado, patron_encabezado in encabezados:
        patron = rf"(?:\*\*)?\s*{patron_encabezado}\s*:?\s*(?:\*\*)?\s*"
        texto_normalizado = re.sub(
            patron,
            f"\n\n**{encabezado}:**\n\n",
            texto_normalizado,
            flags=re.IGNORECASE,
        )
    texto_normalizado = re.sub(r"\n{3,}", "\n\n", texto_normalizado)
    return texto_normalizado.strip()


def construir_prompt_legal(registro: pd.Series) -> str:
    """Construye el prompt CRISPE con contexto recuperado y two-shot prompting."""
    contexto_interno = recuperar_contexto_interno(registro)
    return f"""# C — Contexto
Un sistema interno procesa reportes de cumplimiento CRC y genera logs técnicos cuando una validación falla. El equipo legal debe comprender el problema y decidir el siguiente paso, pero no tiene conocimientos técnicos. La explicación se utilizará como apoyo interno y no como asesoramiento jurídico definitivo.

# R — Rol
Actúa como especialista interno en cumplimiento normativo con experiencia traduciendo errores de sistemas a lenguaje de negocio simple para equipos legales.

# I — Intención
Transforma el error técnico seleccionado en una explicación breve, comprensible y accionable para el equipo legal. El objetivo es que pueda entender qué sucedió, valorar su posible impacto en cumplimiento y conocer el siguiente paso recomendado.

# S — Separación
1. Lee exclusivamente los datos del log proporcionado.
2. Identifica el problema descrito sin cambiar el tipo ni la severidad aprobados.
3. Interpreta el código y el mensaje técnico usando el tipo de incidencia aprobado, pero nunca copies sus frases literalmente.
4. Explica únicamente el posible impacto para el proceso de cumplimiento.
5. Propón una acción concreta basada en la acción aprobada.
6. Si faltan datos o el error no está claro, indica que se necesita revisión técnica.

Datos que debes analizar:
- Código de error: {registro['codigo_error']}
- Mensaje técnico original: {registro['mensaje_tecnico']}
- Tipo de incidencia aprobado: {registro['tipo_incidencia']}
- Severidad aprobada: {registro['severidad']}
- Acción base aprobada: {registro['accion_recomendada']}

Contexto recuperado de documentos internos (mini RAG):
{contexto_interno}

# P — Presentación
Responde completamente en español, con tono profesional, natural y muy sencillo. Escribe como si se lo explicaras verbalmente a un compañero sin conocimientos de informática. Limita cada apartado a un máximo de dos frases breves y utiliza exactamente esta estructura, sin añadir otros apartados. Cada encabezado debe ir en negrita, terminar con dos puntos y estar separado del texto por una línea en blanco:

**Qué ocurrió:**
[Explicación sencilla]

**Impacto para cumplimiento:**
[Impacto posible]

**Acción recomendada:**
[Siguiente paso concreto]

# E — Evaluación
Antes de responder, comprueba silenciosamente que la salida:
- Sea comprensible para una persona del equipo legal sin conocimientos técnicos.
- No copie ni cite el mensaje técnico: exprese siempre su significado con palabras nuevas y sencillas.
- Utilice palabras cotidianas y frases de aproximadamente 20 palabras o menos.
- Respete el tipo, la severidad y la acción aprobados.
- No invente leyes, artículos, multas, sanciones, fechas límite, obligaciones ni hechos.
- No presente posibilidades como certezas.
- No utilice bajo ninguna circunstancia términos como «unicidad», «violación de unicidad», «restricción», «payload», «checksum», «endpoint» o «timestamp». Sustitúyalos por su significado cotidiano.
- Incluya exactamente los tres encabezados solicitados.
- Use exactamente estos encabezados: **Qué ocurrió:**, **Impacto para cumplimiento:** y **Acción recomendada:**.
- Deje una línea en blanco entre cada encabezado y su texto.
Si alguna condición no se cumple, corrige la respuesta antes de entregarla. No muestres esta evaluación.

# Few-shot — Ejemplos de referencia
Ejemplo 1 — Reporte duplicado
Entrada:
- Código: DUPLICATE_REPORT
- Mensaje: Violación de unicidad para id_reporte

Salida:
**Qué ocurrió:**

Este reporte parece haberse enviado anteriormente con el mismo identificador.

**Impacto para cumplimiento:**

Enviar otra copia podría duplicar la información o hacer que el sistema rechace el reporte.

**Acción recomendada:**

Compruebe la presentación anterior y vuelva a enviarlo solo si es necesario.

Ejemplo 2 — Disponibilidad técnica
Entrada:
- Código: CONNECTION_TIMEOUT
- Mensaje: POST /regulador/envios agotó el tiempo tras 30 s

Salida:
**Qué ocurrió:**

El servicio del regulador no respondió dentro del tiempo esperado, por lo que el envío no pudo completarse.

**Impacto para cumplimiento:**

El reporte podría seguir pendiente de presentación, aunque este error no indica por sí mismo que sus datos sean incorrectos.

**Acción recomendada:**

Reintente el envío y solicite apoyo técnico si el servicio continúa sin responder.

Imita el nivel de sencillez de estos ejemplos. No reutilices la jerga del mensaje técnico en la respuesta final."""


def generar_explicacion_legal(registro: pd.Series, modelo: str, modo: str = "Rápida") -> str:
    """Solicita a Ollama una traducción del error técnico para el equipo legal."""
    prompt = construir_prompt_legal(registro)
    if modo == "Mejorada":
        prompt += "\n\nGenera 3 versiones distintas de la respuesta. Después selecciona la mejor según claridad, sencillez, utilidad para Legal y respeto de las reglas. Muestra únicamente la versión ganadora."
        respuesta = consultar_ollama(prompt, modelo, temperatura=0.35, tiempo_espera=180)
        return normalizar_formato_explicacion(respuesta)
    respuesta = consultar_ollama(prompt, modelo, temperatura=0.2)
    return normalizar_formato_explicacion(respuesta)
