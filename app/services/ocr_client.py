"""
Cliente de OCR.space (Engine 3, mismo proveedor que usa el catálogo).
Recibe bytes de imagen y devuelve el texto crudo extraído.
"""
import base64

import httpx

from app.config import OCR_SPACE_API_KEY

OCR_SPACE_URL = "https://api.ocr.space/parse/image"


async def extraer_texto_de_imagen(imagen_bytes: bytes, nombre_archivo: str = "boleta.jpg") -> str:
    """
    Envía la imagen a OCR.space y devuelve el texto crudo (todas las líneas).
    Lanza excepción si OCR.space devuelve error.
    """
    imagen_b64 = base64.b64encode(imagen_bytes).decode("utf-8")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            OCR_SPACE_URL,
            data={
                "apikey": OCR_SPACE_API_KEY,
                "base64Image": f"data:image/jpeg;base64,{imagen_b64}",
                "OCREngine": 3,
                "language": "spa",
                "isTable": True,  # ayuda a preservar la estructura de columnas de la boleta
            },
        )
        response.raise_for_status()
        data = response.json()

    if data.get("IsErroredOnProcessing"):
        mensaje = data.get("ErrorMessage", ["Error desconocido de OCR"])
        raise RuntimeError(f"OCR.space falló: {mensaje}")

    resultados = data.get("ParsedResults", [])
    if not resultados:
        return ""

    return resultados[0].get("ParsedText", "")
