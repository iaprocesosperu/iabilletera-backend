"""
Cliente de Supabase para el backend.
Usa la SERVICE_ROLE key (no la anon key), porque el backend necesita
leer/escribir en nombre de distintos usuarios. La seguridad por usuario
se garantiza filtrando manualmente por user_id en cada query, ya que
el service_role bypassa RLS.

IMPORTANTE: nunca exponer SUPABASE_SERVICE_KEY al frontend.
"""
from supabase import create_client, Client

from app.config import SUPABASE_URL, SUPABASE_SERVICE_KEY

_client: Client | None = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _client
