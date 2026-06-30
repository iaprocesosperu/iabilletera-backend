"""
Mercado Libre Perú — API pública oficial, no requiere autenticación para búsqueda básica.
Esta es la fuente más estable del sistema: no se rompe con cambios de HTML.

Docs: https://developers.mercadolibre.com.pe/
"""
import httpx

ML_SEARCH_URL = "https://api.mercadolibre.com/sites/MPE/search"


async def buscar_producto(nombre: str, limite: int = 5) -> list[dict]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            ML_SEARCH_URL, params={"q": nombre, "limit": limite}
        )
        response.raise_for_status()
        data = response.json()

    items = []
    for resultado in data.get("results", []):
        items.append({
            "precio": resultado.get("price"),
            "presentacion": None,
            "url": resultado.get("permalink"),
            "titulo": resultado.get("title"),
        })
    return items
