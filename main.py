from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
from pathlib import Path

from api.routes import router
from config import settings

app = FastAPI(title="Parquet Viewer", version="1.0.0") # Crea la instancia de FastAPI

# CORS para permitir peticiones desde el navegador
app.add_middleware( 
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(router)

# Incluye las rutas de la API
@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("templates/index.html", "r", encoding="utf-8") as file:
        return file.read()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)