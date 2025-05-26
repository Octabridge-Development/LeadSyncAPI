# Este archivo es el punto de entrada principal de la aplicación.
# Configura FastAPI, incluye middlewares, y monta los routers de la API.

from fastapi import FastAPI
from app.api.v1.endpoints import manychat
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Incluir el router de ManyChat bajo el prefijo /api/v1
app.include_router(
    manychat.router,
    prefix="/api/v1"
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambiar a dominios específicos en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
