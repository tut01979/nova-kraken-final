from fastapi import FastAPI
import os

# Esto es CRUCIAL: la variable debe llamarse exactamente "app"
app = FastAPI(
    title="Nova Kraken Futures Bot - Test",
    description="Módulo de trading TerraNova - Prueba de conexión",
    version="1.0"
)

@app.get("/")
async def root():
    return {
        "status": "OK",
        "message": "Bot Nova Kraken Futures activo y listo",
        "environment": "Production" if os.getenv("RAILWAY_ENVIRONMENT") else "Local/Development",
        "kraken_api_key_set": bool(os.getenv("KRAKEN_API_KEY")),
        "kraken_secret_set": bool(os.getenv("KRAKEN_SECRET")),
        "hint": "Si ves true en las keys, las variables están cargadas correctamente"
    }

# Opcional: endpoint de health para monitoreo
@app.get("/health")
async def health():
    return {"status": "healthy"}

# Esto es importante para cuando corras localmente con uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)