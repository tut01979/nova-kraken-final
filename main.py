from fastapi import FastAPI
import os
import asyncio
import ccxt.async_support as ccxt
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Nova Kraken Futures Bot",
    description="Módulo de trading TerraNova - Conexión Kraken Futures",
    version="1.0"
)

@app.get("/")
async def root():
    return {
        "status": "OK",
        "message": "Bot Nova Kraken Futures activo",
        "kraken_api_key_set": bool(os.getenv("KRAKEN_API_KEY")),
        "kraken_secret_set": bool(os.getenv("KRAKEN_SECRET")),
    }

@app.get("/test-balance")
async def test_balance():
    exchange = ccxt.krakenfutures({
        'apiKey': os.getenv('KRAKEN_API_KEY'),
        'secret': os.getenv('KRAKEN_SECRET'),
        # Algunas configs antiguas necesitan esto, pruébalo si falla:
        # 'password': os.getenv('KRAKEN_PASSWORD', ''),
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future',
        },
    })

    try:
        balance = await exchange.fetch_balance()
        await exchange.close()
        return {
            "connection": "SUCCESS",
            "balance": balance['total'],  # o balance completo si quieres más detalle
            "info": "Autenticación y conexión con Kraken Futures OK"
        }
    except Exception as e:
        await exchange.close()
        return {
            "connection": "ERROR",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "info": "Revisa logs para detalle completo"
        }

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)