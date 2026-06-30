"""
Router de boletas: el endpoint que implementa el flujo de "un solo botón +".

POST /boletas/procesar
  Recibe: imagen (multipart) + user_id
  Hace: OCR -> parser -> matching contra catálogo -> clasificación IA de productos nuevos
        -> guarda compras y productos en Supabase
  Devuelve: resumen (cuántos productos, total gastado, cuántos nuevos) + líneas que necesitan revisión
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.services.ocr_client import extraer_texto_de_imagen
from app.services.parser_boletas import parsear_texto_ocr
from app.services.matching import buscar_match, normalizar_nombre
from app.services.openai_client import clasificar_producto
from app.services.supabase_client import get_supabase

router = APIRouter()


@router.post("/procesar")
async def procesar_boleta(
    user_id: str = Form(...),
    tienda: str | None = Form(None),
    fecha: str | None = Form(None),
    imagen: UploadFile = File(...),
):
    supabase = get_supabase()

    # 1. OCR
    imagen_bytes = await imagen.read()
    try:
        texto_crudo = await extraer_texto_de_imagen(imagen_bytes, imagen.filename or "boleta.jpg")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error al procesar OCR: {e}")

    if not texto_crudo.strip():
        raise HTTPException(
            status_code=422,
            detail="No se pudo leer texto en la imagen. Intenta con una foto más clara.",
        )

    # 2. Parsear líneas
    lineas = parsear_texto_ocr(texto_crudo)
    if not lineas:
        raise HTTPException(
            status_code=422,
            detail="Se leyó texto pero no se reconoció ninguna línea de producto. Revisa la foto.",
        )

    # 3. Cargar catálogo actual del usuario para matching
    catalogo_resp = supabase.table("productos").select("id, nombre_normalizado").eq(
        "user_id", user_id
    ).execute()
    catalogo = catalogo_resp.data or []

    productos_nuevos = 0
    compras_insertadas = []
    lineas_dudosas = []

    for linea in lineas:
        match = buscar_match(linea.nombre_crudo, catalogo)

        producto_id = None
        if match.confianza == "alta":
            producto_id = match.producto_id
        else:
            # Confianza media o baja: se crea producto nuevo automáticamente (no se interrumpe el flujo)
            nombre_normalizado = normalizar_nombre(linea.nombre_crudo)

            try:
                clasificacion = await clasificar_producto(linea.nombre_crudo)
            except Exception:
                clasificacion = {"categoria": None, "confianza": "baja", "observacion": "No se pudo clasificar automáticamente."}

            nuevo_producto = supabase.table("productos").insert({
                "user_id": user_id,
                "nombre": linea.nombre_crudo.title(),
                "nombre_normalizado": nombre_normalizado,
                "categoria": clasificacion.get("categoria"),
                "categoria_confianza": clasificacion.get("confianza"),
                "observacion_clasificacion": clasificacion.get("observacion"),
                "presentacion_habitual": linea.presentacion,
            }).execute()

            producto_id = nuevo_producto.data[0]["id"]
            productos_nuevos += 1
            # Agregar al catálogo en memoria para que líneas siguientes de la misma boleta puedan matchear contra él
            catalogo.append({"id": producto_id, "nombre_normalizado": nombre_normalizado})

        compra = supabase.table("compras").insert({
            "user_id": user_id,
            "producto_id": producto_id,
            "cantidad": linea.cantidad,
            "precio_unitario": linea.precio_unitario,
            "precio_total": linea.precio_total,
            "presentacion": linea.presentacion,
            "tienda": tienda,
            "fecha": fecha,
            "origen": "foto_boleta",
            "necesita_revision": linea.necesita_revision,
            "texto_ocr_crudo": linea.texto_ocr_crudo,
        }).execute()

        compras_insertadas.append(compra.data[0])

        if linea.necesita_revision:
            lineas_dudosas.append({
                "texto_ocr": linea.texto_ocr_crudo,
                "nombre_crudo": linea.nombre_crudo,
                "motivo": "La cantidad x precio unitario no coincide con el precio total leído.",
            })

    total_gastado = sum(c["precio_total"] for c in compras_insertadas)

    return {
        "productos_registrados": len(compras_insertadas),
        "productos_nuevos": productos_nuevos,
        "total_gastado": round(total_gastado, 2),
        "lineas_que_necesitan_revision": lineas_dudosas,
    }
