"""
Router de texto libre / voz: maneja el caso "compré limones en la esquina"
(escrito o dictado, llega igual como texto a este endpoint).

POST /texto-libre/procesar
  Si el texto no trae precio -> devuelve needs_price=true para que el frontend
  muestre el campo de precio antes de confirmar el guardado.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.openai_client import extraer_de_texto_libre, clasificar_producto
from app.services.matching import buscar_match, normalizar_nombre
from app.services.supabase_client import get_supabase

router = APIRouter()


class TextoLibreInput(BaseModel):
    user_id: str
    texto: str
    fecha: str | None = None


class ConfirmarCompraInput(BaseModel):
    user_id: str
    producto_nombre: str
    cantidad: float = 1
    precio_unitario: float
    precio_total: float | None = None
    tienda: str | None = None
    fecha: str | None = None


@router.post("/procesar")
async def procesar_texto_libre(payload: TextoLibreInput):
    try:
        extraido = await extraer_de_texto_libre(payload.texto)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error al interpretar el texto: {e}")

    precio_unitario = extraido.get("precio_unitario")
    precio_total = extraido.get("precio_total")

    if precio_unitario is None and precio_total is None:
        return {
            "needs_price": True,
            "producto_sugerido": extraido.get("producto"),
            "cantidad_sugerida": extraido.get("cantidad") or 1,
            "tienda_sugerida": extraido.get("tienda"),
            "mensaje": "Falta el precio para registrar el gasto. Indícalo para continuar.",
        }

    # Si hay precio, completar el faltante y guardar directo (sin más preguntas)
    cantidad = extraido.get("cantidad") or 1
    if precio_unitario is None:
        precio_unitario = round(precio_total / cantidad, 2)
    if precio_total is None:
        precio_total = round(precio_unitario * cantidad, 2)

    resultado = await _guardar_compra(
        user_id=payload.user_id,
        producto_nombre=extraido.get("producto", "Producto sin nombre"),
        cantidad=cantidad,
        precio_unitario=precio_unitario,
        precio_total=precio_total,
        tienda=extraido.get("tienda"),
        fecha=payload.fecha,
        origen="texto_libre",
    )
    return {"needs_price": False, **resultado}


@router.post("/confirmar")
async def confirmar_compra(payload: ConfirmarCompraInput):
    """Se llama cuando el usuario completó el precio que faltaba."""
    precio_total = payload.precio_total or round(payload.precio_unitario * payload.cantidad, 2)
    resultado = await _guardar_compra(
        user_id=payload.user_id,
        producto_nombre=payload.producto_nombre,
        cantidad=payload.cantidad,
        precio_unitario=payload.precio_unitario,
        precio_total=precio_total,
        tienda=payload.tienda,
        fecha=payload.fecha,
        origen="texto_libre",
    )
    return resultado


async def _guardar_compra(
    user_id: str,
    producto_nombre: str,
    cantidad: float,
    precio_unitario: float,
    precio_total: float,
    tienda: str | None,
    fecha: str | None,
    origen: str,
) -> dict:
    supabase = get_supabase()

    catalogo_resp = supabase.table("productos").select("id, nombre_normalizado").eq(
        "user_id", user_id
    ).execute()
    catalogo = catalogo_resp.data or []

    match = buscar_match(producto_nombre, catalogo)
    producto_nuevo = False

    if match.confianza == "alta":
        producto_id = match.producto_id
    else:
        nombre_normalizado = normalizar_nombre(producto_nombre)
        try:
            clasificacion = await clasificar_producto(producto_nombre)
        except Exception:
            clasificacion = {"categoria": None, "confianza": "baja", "observacion": None}

        nuevo = supabase.table("productos").insert({
            "user_id": user_id,
            "nombre": producto_nombre.title(),
            "nombre_normalizado": nombre_normalizado,
            "categoria": clasificacion.get("categoria"),
            "categoria_confianza": clasificacion.get("confianza"),
            "observacion_clasificacion": clasificacion.get("observacion"),
        }).execute()
        producto_id = nuevo.data[0]["id"]
        producto_nuevo = True

    compra = supabase.table("compras").insert({
        "user_id": user_id,
        "producto_id": producto_id,
        "cantidad": cantidad,
        "precio_unitario": precio_unitario,
        "precio_total": precio_total,
        "tienda": tienda,
        "fecha": fecha,
        "origen": origen,
    }).execute()

    return {
        "compra_id": compra.data[0]["id"],
        "producto_id": producto_id,
        "producto_nuevo": producto_nuevo,
        "total_gastado": precio_total,
    }
