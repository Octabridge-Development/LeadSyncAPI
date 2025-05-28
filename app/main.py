
from fastapi import FastAPI
from app.api.v1 import router as api_v1_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Incluir el router principal de la API v1 bajo el prefijo /api/v1
app.include_router(api_v1_router.router, prefix="/api/v1")

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
