"""
IABilletera Backend — FastAPI
Ecosistema IA Procesos — Nina Lopez

Punto de entrada principal. Define la app, CORS, y registra los routers.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import boletas, texto_libre, precios

app = FastAPI(
    title="IABilletera Backend",
    description="Backend de IABilletera: OCR de boletas, parser de texto/voz, scraping de precios.",
    version="1.0.0",
)

# CORS — ajustar allow_origins con la URL real de Vercel cuando esté desplegada
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restringir a la URL de Vercel en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(boletas.router, prefix="/boletas", tags=["Boletas"])
app.include_router(texto_libre.router, prefix="/texto-libre", tags=["Texto libre / Voz"])
app.include_router(precios.router, prefix="/precios", tags=["Precios y alternativas"])


@app.get("/")
def root():
    return {"status": "ok", "servicio": "IABilletera Backend"}


@app.get("/health")
def health():
    return {"status": "healthy"}
