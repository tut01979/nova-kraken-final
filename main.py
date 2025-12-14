from fastapi import FastAPI, Request
from pydantic import BaseModel
import os
import ccxt.async_support as ccxt
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Nova - Kraken Futures Trading Bot")

exchange = ccxt.krakenfutures({
    'apiKey': os.getenv('KRAKEN_API_KEY'),
    'secret': os.getenv('KRAKEN_SECRET'),
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
})

SYMBOL = 'PI_SOLUSD'
QUANTITY = 1.0
ATR_MULTIPLIER = 2.0
DEFAULT_ATR = 10.0  # Valor fallback si no viene ATR

class AlertPayload(BaseModel):
    signal: str
    atr: float | None = None

@app.get("/")
async def root():
    return {"status": "Nova Bot activo", "symbol": SYMBOL, "quantity": QUANTITY}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        body = await request.body()
        text = body.decode('utf-8')
        logger.info(f"Webhook recibido (raw): {text}")

        # Intentar parsear como JSON primero
        try:
            payload = json.loads(text)
            alert = AlertPayload(**payload)
        except:
            # Si falla, asumir texto plano con placeholders resueltos
            text_lower = text.lower()
            if 'buy' in text_lower or 'long' in text_lower:
                alert = AlertPayload(signal="long", atr=None)
            elif 'sell' in text_lower or 'short' in text_lower:
                alert = AlertPayload(signal="short", atr=None)
            else:
                return {"status": "error", "message": "No se detectó señal válida"}

        atr_value = alert.atr or DEFAULT_ATR
        sl_tp_distance = ATR_MULTIPLIER * atr_value
        side = 'buy' if alert.signal in ["long", "buy"] else 'sell'

        main_order = await exchange.create_order(
            symbol=SYMBOL,
            type='market',
            side=side,
            amount=QUANTITY,
        )

        price = main_order.get('average') or main_order.get('price')

        # SL y TP reduce-only
        await exchange.create_order(
            symbol=SYMBOL,
            type='stop',
            side='sell' if side == 'buy' else 'buy',
            amount=QUANTITY,
            price=price - sl_tp_distance if side == 'buy' else price + sl_tp_distance,
            params={'reduce-only': True}
        )

        await exchange.create_order(
            symbol=SYMBOL,
            type='limit',
            side='sell' if side == 'buy' else 'buy',
            amount=QUANTITY,
            price=price + sl_tp_distance if side == 'buy' else price - sl_tp_distance,
            params={'reduce-only': True, 'postOnly': True}
        )

        logger.info(f"{alert.signal.upper()} ejecutado | Precio ≈ {price} | SL/TP ±{sl_tp_distance:.2f}")
        return {"status": "success", "signal": alert.signal, "price": price}

    except Exception as e:
        logger.error(f"Error crítico: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}

@app.get("/test-balance")
async def test_balance():
    try:
        balance = await exchange.fetch_balance()
        return {"connection": "SUCCESS", "balance": balance['total']}
    except Exception as e:
        return {"connection": "ERROR", "error": str(e)}