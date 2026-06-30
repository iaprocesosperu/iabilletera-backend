"""
Scraper de Plaza Vea (plazavea.com.pe) usando Playwright headless.

ADVERTENCIA DE MANTENIMIENTO: este scraper depende de la estructura HTML actual
del sitio. Plaza Vea puede cambiar su web sin aviso, lo que rompe los selectores
de abajo. Cuando esto pase, el síntoma será que buscar_producto() devuelve lista
vacía o lanza un timeout — eso ya está manejado en el router (se marca la fuente
como 'no disponible' sin tumbar las demás).

Mantenimiento esperado: revisar selectores cada vez que se reporten 0 resultados
de forma consistente.
"""
from playwright.async_api import async_playwright

BASE_URL = "https://www.plazavea.com.pe/search?_query="


async def buscar_producto(nombre: str, limite: int = 5) -> list[dict]:
    url = BASE_URL + nombre.replace(" ", "%20")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=15000, wait_until="domcontentloaded")
            await page.wait_for_selector(".product-item", timeout=8000)

            tarjetas = await page.query_selector_all(".product-item")
            items = []
            for tarjeta in tarjetas[:limite]:
                nombre_el = await tarjeta.query_selector(".product-item-name")
                precio_el = await tarjeta.query_selector(".price")
                link_el = await tarjeta.query_selector("a")

                if not (nombre_el and precio_el):
                    continue

                titulo = (await nombre_el.inner_text()).strip()
                precio_texto = (await precio_el.inner_text()).strip()
                precio = _parsear_precio(precio_texto)
                href = await link_el.get_attribute("href") if link_el else None

                if precio is not None:
                    items.append({
                        "precio": precio,
                        "presentacion": None,
                        "url": href,
                        "titulo": titulo,
                    })
            return items
        finally:
            await browser.close()


def _parsear_precio(texto: str) -> float | None:
    import re
    match = re.search(r"(\d+[.,]\d{2})", texto)
    if not match:
        return None
    return float(match.group(1).replace(",", "."))
