from fastapi import FastAPI, Request
from pydantic import BaseModel
import ccxt.async_support as ccxt
import os
import json

app = FastAPI()

exchange = ccxt.krakenfutures({
    'apiKey': os.getenv("KRAKEN_API_KEY"),  # ← Clave pública (la larga) aquí
    'secret': os.getenv("KRAKEN_SECRET"),   # ← Clave privada aquí
    'password': os.getenv("KRAKEN_API_KEY"),  # ← Clave pública también aquí (trick de ccxt)
    'enableRateLimit': True,
})

class Signal(BaseModel):
    action: str
    symbol: str
    quantity: str
    price: float
    stop_loss: float = None
    take_profit: float = None
    exchange: str
    market: str

@app.get("/")
async def home():
    return {"status": "NOVA KRAKEN - COBRANDO"}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        raw = await request.body()
        data = raw.decode("utf-8").strip()
        print(f"RAW recibido: {data}")
        payload = json.loads(data)
        signal = Signal(**payload)
        print(f"SEÑAL → {signal.action.upper()} {signal.quantity} {signal.symbol} @ {signal.price}")

        side = "buy" if signal.action == "buy" else "sell"
        symbol = signal.symbol.replace("-PERP", "USD")

        order = await exchange.create_market_order(symbol, side, float(signal.quantity))
        print(f"ORDEN EJECUTADA → {order['id']}")

        return {"status": "OK"}
    except Exception as e:
        print(f"ERROR → {e}")
        return {"error": str(e)}, 400