from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

from api.routes import router
from api.admin_routes import admin_router
from config import settings
from routes.power_bi_routes import router as power_bi_router

app = FastAPI(title="Parquet Viewer", version="1.0.0")

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

# Incluir rutas principales
app.include_router(router)

# Incluir rutas de administrador
app.include_router(admin_router, prefix="/admin", tags=["admin"])

# Incluir rutas Power BI
app.include_router(power_bi_router)

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("templates/index.html", "r", encoding="utf-8") as file:
        return file.read()

@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    with open("templates/admin.html", "r", encoding="utf-8") as file:
        return file.read()

@app.get("/power-bi", response_class=HTMLResponse)
async def power_bi_page():
    with open("templates/power_bi_viewer.html", "r", encoding="utf-8") as file:
        return file.read()

@app.get("/power-bi-viewer", response_class=HTMLResponse)
async def power_bi_viewer_page():
    with open("templates/power_bi_viewer.html", "r", encoding="utf-8") as file:
        return file.read()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)