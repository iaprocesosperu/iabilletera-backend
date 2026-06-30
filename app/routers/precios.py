"""
Router de precios: el botón manual "Buscar alternativas".

POST /precios/buscar
  Recibe producto_id, dispara búsqueda en paralelo contra:
    - Mercado Libre (API oficial)
    - Plaza Vea, Tottus, Metro (scraping con Playwright)
  Guarda resultados en precios_observados, calcula ahorro estimado vs. histórico
  del usuario, y genera una alerta_ahorro si hay oportunidad real.

NOTA DE IMPLEMENTACIÓN: el scraping de supermercados (Playwright) requiere
un entorno con navegador headless instalado. En Railway esto se logra con
un Dockerfile que instale Chromium. Este router define la interfaz y el
flujo; los scrapers concretos de cada fuente viven en app/services/scrapers/
y se agregan incrementalmente (empezar por Mercado Libre, que es API, no scraping).
"""
import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.supabase_client import get_supabase
from app.services.scrapers import mercado_libre, plaza_vea, tottus, metro

router = APIRouter()

FUENTES_SCRAPERS = {
    "mercado_libre": mercado_libre.buscar_producto,
    "plaza_vea": plaza_vea.buscar_producto,
    "tottus": tottus.buscar_producto,
    "metro": metro.buscar_producto,
}


class BuscarPreciosInput(BaseModel):
    user_id: str
    producto_id: str


@router.post("/buscar")
async def buscar_alternativas(payload: BuscarPreciosInput):
    supabase = get_supabase()

    producto_resp = supabase.table("productos").select("*").eq(
        "id", payload.producto_id
    ).eq("user_id", payload.user_id).single().execute()

    if not producto_resp.data:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    producto = producto_resp.data
    nombre_busqueda = producto["nombre"]

    # Disparar todas las fuentes en paralelo; cada una maneja sus propios fallos
    resultados_por_fuente = {}
    tareas = {
        fuente: asyncio.create_task(_buscar_con_manejo_de_errores(fn, nombre_busqueda))
        for fuente, fn in FUENTES_SCRAPERS.items()
    }
    for fuente, tarea in tareas.items():
        resultados_por_fuente[fuente] = await tarea

    precios_guardados = []
    for fuente, resultado in resultados_por_fuente.items():
        if resultado["disponible"]:
            for item in resultado["items"]:
                registro = supabase.table("precios_observados").insert({
                    "user_id": payload.user_id,
                    "producto_id": payload.producto_id,
                    "fuente": fuente,
                    "precio": item["precio"],
                    "presentacion": item.get("presentacion"),
                    "url": item.get("url"),
                    "disponible": True,
                }).execute()
                precios_guardados.append(registro.data[0])
        else:
            # Fuente caída: se registra igual para tener histórico de disponibilidad, sin tumbar el flujo
            supabase.table("precios_observados").insert({
                "user_id": payload.user_id,
                "producto_id": payload.producto_id,
                "fuente": fuente,
                "precio": 0,
                "disponible": False,
            }).execute()

    # Comparar contra el precio histórico promedio del usuario para este producto
    compras_resp = supabase.table("compras").select("precio_unitario").eq(
        "producto_id", payload.producto_id
    ).eq("user_id", payload.user_id).execute()
    precios_historicos = [c["precio_unitario"] for c in (compras_resp.data or [])]
    precio_promedio_usuario = (
        sum(precios_historicos) / len(precios_historicos) if precios_historicos else None
    )

    alerta = None
    if precios_guardados and precio_promedio_usuario:
        mejor = min(precios_guardados, key=lambda p: p["precio"])
        if mejor["precio"] < precio_promedio_usuario:
            ahorro = round(precio_promedio_usuario - mejor["precio"], 2)
            ahorro_pct = round((ahorro / precio_promedio_usuario) * 100, 1)
            nueva_alerta = supabase.table("alertas_ahorro").insert({
                "user_id": payload.user_id,
                "producto_id": payload.producto_id,
                "tipo": "cambiar_tienda",
                "detalle": f"Encontramos {producto['nombre']} más barato en {mejor['fuente']}: "
                           f"S/{mejor['precio']} vs tu precio habitual de S/{precio_promedio_usuario:.2f}",
                "ahorro_estimado": ahorro,
                "ahorro_estimado_pct": ahorro_pct,
            }).execute()
            alerta = nueva_alerta.data[0]

    return {
        "producto": producto["nombre"],
        "precio_promedio_usuario": precio_promedio_usuario,
        "resultados_por_fuente": {
            fuente: {"disponible": r["disponible"], "items_encontrados": len(r["items"])}
            for fuente, r in resultados_por_fuente.items()
        },
        "precios_encontrados": precios_guardados,
        "alerta_generada": alerta,
    }


async def _buscar_con_manejo_de_errores(funcion_scraper, nombre_busqueda: str) -> dict:
    """Envuelve cada scraper para que un fallo individual no tumbe la búsqueda completa."""
    try:
        items = await funcion_scraper(nombre_busqueda)
        return {"disponible": True, "items": items}
    except Exception:
        return {"disponible": False, "items": []}
