"""
Matching de productos: dado un nombre crudo leído por OCR/texto/voz,
busca el producto más parecido en el catálogo del usuario.

Usa rapidfuzz (token_sort_ratio) porque tolera bien diferencias de orden
de palabras y abreviaturas parciales, comunes en boletas peruanas.
"""
import re
import unicodedata
from dataclasses import dataclass

from rapidfuzz import fuzz, process

from app.config import UMBRAL_MATCH_ALTO, UMBRAL_MATCH_MEDIO


def normalizar_nombre(nombre: str) -> str:
    """Lowercase, sin tildes, sin puntuación duplicada, espacios colapsados."""
    nombre = nombre.lower().strip()
    nombre = "".join(
        c for c in unicodedata.normalize("NFD", nombre) if unicodedata.category(c) != "Mn"
    )
    nombre = re.sub(r"[^\w\s]", " ", nombre)
    nombre = re.sub(r"\s+", " ", nombre).strip()
    return nombre


@dataclass
class ResultadoMatch:
    producto_id: str | None
    nombre_match: str | None
    score: float
    confianza: str  # 'alta' | 'media' | 'baja'


def buscar_match(
    nombre_crudo: str, catalogo: list[dict]
) -> ResultadoMatch:
    """
    catalogo: lista de dicts con al menos {'id': str, 'nombre_normalizado': str}
    Devuelve el mejor match y su nivel de confianza.
    """
    nombre_norm = normalizar_nombre(nombre_crudo)

    if not catalogo:
        return ResultadoMatch(producto_id=None, nombre_match=None, score=0, confianza="baja")

    opciones = {p["id"]: p["nombre_normalizado"] for p in catalogo}
    mejor = process.extractOne(
        nombre_norm, opciones, scorer=fuzz.token_sort_ratio
    )

    if mejor is None:
        return ResultadoMatch(producto_id=None, nombre_match=None, score=0, confianza="baja")

    nombre_match, score, producto_id = mejor

    if score >= UMBRAL_MATCH_ALTO:
        confianza = "alta"
    elif score >= UMBRAL_MATCH_MEDIO:
        confianza = "media"
    else:
        confianza = "baja"

    return ResultadoMatch(
        producto_id=producto_id, nombre_match=nombre_match, score=score, confianza=confianza
    )
