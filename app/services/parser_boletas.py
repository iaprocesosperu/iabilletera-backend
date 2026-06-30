"""
Parser de boletas: convierte el texto crudo que devuelve OCR.space
en líneas estructuradas (cantidad, nombre, presentación, precio_unitario, precio_total).

Casos reales que este parser debe manejar (validado contra boleta real de supermercado):
  - Nombre y presentación en líneas separadas: "MOLINO ROJO ARROZ INTEGRAL" / ".1KG"
  - Abreviatura de empaque: "Emp.3" significa empaque de 3 unidades, no cantidad 1
  - Validación aritmética: cantidad x precio_unitario debe ser ~= precio_total
  - Cantidad y unidad pegadas: "4  U" significa cantidad=4, unidad=U (unidad)
"""
import re
from dataclasses import dataclass, field


@dataclass
class LineaBoleta:
    cantidad: float
    nombre_crudo: str
    presentacion: str | None
    precio_unitario: float
    precio_total: float
    es_empaque: bool = False
    unidades_por_empaque: int | None = None
    aritmetica_valida: bool = True
    necesita_revision: bool = False
    texto_ocr_crudo: str = ""


# Patrón de presentación: número + unidad de medida (kg, g, ml, l, und, un)
PATRON_PRESENTACION = re.compile(
    r"^\.?(\d+[.,]?\d*)\s*(kg|g|ml|l|und|un|u)\b", re.IGNORECASE
)

# Patrón de línea de cantidad/precio: "1  U  ...  27.30  27.30"
PATRON_CANTIDAD_PRECIO = re.compile(
    r"^(\d+)\s+(U|EMP\.?\s*\d+)\s+(.+?)\s+(\d+[.,]\d{2})\s+(\d+[.,]\d{2})\s*$",
    re.IGNORECASE,
)


def _to_float(valor: str) -> float:
    return float(valor.replace(",", "."))


def parsear_texto_ocr(texto_crudo: str) -> list[LineaBoleta]:
    """
    Recibe el texto crudo devuelto por OCR.space y devuelve una lista
    de líneas estructuradas, uniendo líneas de presentación partidas
    y validando la aritmética de cada línea.
    """
    lineas_raw = [l.strip() for l in texto_crudo.split("\n") if l.strip()]
    resultado: list[LineaBoleta] = []

    i = 0
    while i < len(lineas_raw):
        linea = lineas_raw[i]
        match = PATRON_CANTIDAD_PRECIO.match(linea)

        if not match:
            i += 1
            continue

        cantidad_str, empaque_str, nombre, precio_unit_str, precio_total_str = match.groups()
        cantidad = float(cantidad_str)
        es_empaque = "emp" in empaque_str.lower()
        unidades_por_empaque = None
        if es_empaque:
            num_match = re.search(r"\d+", empaque_str)
            if num_match:
                unidades_por_empaque = int(num_match.group())

        precio_unitario = _to_float(precio_unit_str)
        precio_total = _to_float(precio_total_str)

        # Mirar la siguiente línea: si es solo presentación (ej. ".1KG"), se une al nombre
        presentacion = None
        if i + 1 < len(lineas_raw):
            siguiente = lineas_raw[i + 1]
            if PATRON_PRESENTACION.match(siguiente) and not PATRON_CANTIDAD_PRECIO.match(siguiente):
                presentacion = siguiente.strip()
                i += 1  # consumir la línea de presentación

        # Validación aritmética: cantidad x precio_unitario ~= precio_total
        esperado = round(cantidad * precio_unitario, 2)
        aritmetica_valida = abs(esperado - precio_total) < 0.05
        necesita_revision = not aritmetica_valida

        resultado.append(
            LineaBoleta(
                cantidad=cantidad,
                nombre_crudo=nombre.strip(),
                presentacion=presentacion,
                precio_unitario=precio_unitario,
                precio_total=precio_total,
                es_empaque=es_empaque,
                unidades_por_empaque=unidades_por_empaque,
                aritmetica_valida=aritmetica_valida,
                necesita_revision=necesita_revision,
                texto_ocr_crudo=linea + (f" / {presentacion}" if presentacion else ""),
            )
        )
        i += 1

    return resultado
