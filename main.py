from fastapi import FastAPI, Request
from pydantic import BaseModel
import os
import ccxt.async_support as ccxt
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Nova - Kraken Futures Trading Bot")

# Configuración del exchange (instancia global reutilizable)
exchange = ccxt.krakenfutures({
    'apiKey': os.getenv('KRAKEN_API_KEY'),
    'secret': os.getenv('KRAKEN_SECRET'),
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
})

# Configuración del trading
SYMBOL = 'PI_SOLUSD'       # Perpetual SOL
QUANTITY = 1.0             # 1 SOL fijo (mínimo en Kraken Futures)
ATR_MULTIPLIER = 2.0       # SL y TP = 2 × ATR

class AlertPayload(BaseModel):
    signal: str   # "long" o "short"
    atr: float    # Valor del ATR(14) desde Pine Script

@app.get("/")
async def root():
    return {
        "status": "Nova Bot activo y operativo",
        "symbol": SYMBOL,
        "quantity": QUANTITY,
        "atr_multiplier": ATR_MULTIPLIER
    }

@app.post("/webhook")
async def webhook(request: Request):
    try:
        payload = await request.json()
        logger.info(f"Webhook recibido: {payload}")
        
        alert = AlertPayload(**payload)
        
        if alert.signal not in ["long", "short"]:
            return {"status": "error", "message": "Signal debe ser 'long' o 'short'"}

        side = 'buy' if alert.signal == "long" else 'sell'
        sl_tp_distance = ATR_MULTIPLIER * alert.atr

        # Orden principal: market
        main_order = await exchange.create_order(
            symbol=SYMBOL,
            type='market',
            side=side,
            amount=QUANTITY,
        )

        price = main_order['average'] or main_order['price']  # Kraken devuelve average en market fills

        # Stop-Loss (reduce-only)
        await exchange.create_order(
            symbol=SYMBOL,
            type='stop',
            side='sell' if side == 'buy' else 'buy',
            amount=QUANTITY,
            price=price - sl_tp_distance if side == 'buy' else price + sl_tp_distance,
            params={'reduce-only': True}
        )

        # Take-Profit (limit reduce-only)
        await exchange.create_order(
            symbol=SYMBOL,
            type='limit',
            side='sell' if side == 'buy' else 'buy',
            amount=QUANTITY,
            price=price + sl_tp_distance if side == 'buy' else price - sl_tp_distance,
            params={'reduce-only': True, 'postOnly': True}
        )

        logger.info(f"{alert.signal.upper()} ejecutado | Precio: {price} | SL/TP: ±{sl_tp_distance:.2f}")
        return {"status": "success", "order_id": main_order['id'], "price": price}

    except Exception as e:
        logger.error(f"Error en webhook: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}

@app.get("/test-balance")
async def test_balance():
    try:
        balance = await exchange.fetch_balance()
        return {"connection": "SUCCESS", "balance": balance['total']}
    except Exception as e:
        return {"connection": "ERROR", "error": str(e)}

@app.get("/health")
async def health():
    return {"status": "healthy"}