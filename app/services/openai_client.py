"""
Cliente de OpenAI: dos usos principales
1. Parsear texto libre/voz ("compré limones en la esquina") a estructura producto/cantidad/precio/tienda
2. Clasificar un producto nuevo en una categoría libre, con observación de por qué

Modelo: gpt-4o-mini (rápido y económico, suficiente para extracción estructurada).
"""
import json

from openai import AsyncOpenAI

from app.config import OPENAI_API_KEY

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

PROMPT_EXTRACCION_TEXTO_LIBRE = """Eres un asistente que extrae datos de compra de un texto en español (Perú).
El usuario puede escribir o dictar algo como "compré 2 limones a 1.50 cada uno en la esquina" o solo "compré limones".

Devuelve SOLO un JSON con este formato exacto, sin texto adicional ni markdown:
{
  "producto": "nombre del producto en formato normal (ej. Limón)",
  "cantidad": numero o null si no se menciona,
  "precio_unitario": numero o null si no se menciona,
  "precio_total": numero o null si no se menciona,
  "tienda": "texto tal cual lo mencionó el usuario, o null si no lo dijo"
}

Si el usuario da precio_total pero no precio_unitario (o viceversa), calcula el que falta usando la cantidad si es posible.
Si no hay NINGÚN precio mencionado, deja ambos precios en null.
Texto del usuario: """


async def extraer_de_texto_libre(texto: str) -> dict:
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Respondes únicamente con JSON válido, sin explicaciones."},
            {"role": "user", "content": PROMPT_EXTRACCION_TEXTO_LIBRE + texto},
        ],
        temperature=0,
    )
    contenido = response.choices[0].message.content.strip()
    contenido = contenido.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(contenido)


PROMPT_CLASIFICACION = """Clasifica el siguiente producto de supermercado/abarrotes peruano en una categoría general
en español (ej. Lácteos, Limpieza del hogar, Abarrotes, Cuidado personal, Snacks, Bebidas, Carnes y embutidos, etc).
Tú decides la categoría libremente, no hay lista fija.

Devuelve SOLO un JSON con este formato exacto, sin texto adicional:
{
  "categoria": "nombre de la categoría",
  "confianza": "alta" | "media" | "baja",
  "observacion": "explicación breve de por qué elegiste esa categoría, una sola oración"
}

Producto: """


async def clasificar_producto(nombre_producto: str) -> dict:
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Respondes únicamente con JSON válido, sin explicaciones."},
            {"role": "user", "content": PROMPT_CLASIFICACION + nombre_producto},
        ],
        temperature=0,
    )
    contenido = response.choices[0].message.content.strip()
    contenido = contenido.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(contenido)
