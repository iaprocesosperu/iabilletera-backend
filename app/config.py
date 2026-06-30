"""
Configuración centralizada de variables de entorno.
Todas las API keys y URLs sensibles viven en variables de entorno de Railway,
nunca hardcodeadas en el código.
"""
import os

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")  # service_role key, solo backend

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OCR_SPACE_API_KEY = os.getenv("OCR_SPACE_API_KEY", "")

# Umbral de confianza para fuzzy matching de productos (0-100)
UMBRAL_MATCH_ALTO = 85
UMBRAL_MATCH_MEDIO = 50
