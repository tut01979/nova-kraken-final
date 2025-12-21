from fastapi import FastAPI, Request
import os
import ccxt.async_support as ccxt
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Nova Kraken Bot - 100% Equity Final")

exchange = ccxt.krakenfutures({
    'apiKey': os.getenv('KRAKEN_API_KEY'),
    'secret': os.getenv('KRAKEN_SECRET'),
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
})

SYMBOL = 'PF_XBTUSD'

@app.get("/")
async def root():
    return {"status": "Nova Bot 100% Equity activo", "symbol": SYMBOL}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        payload = await request.json()
        logger.info(f"RAW recibido: {payload}")

        action = payload.get('action')
        if action not in ['buy', 'sell']:
            return {"status": "error", "message": "action inválido"}

        price = float(payload['price'])
        stop_loss = float(payload['stop_loss'])

        # Calcular quantity = 100% equity real
        balance = await exchange.fetch_balance()
        collateral = balance['info']['marginAvailable'] or balance['total'].get('BTC', 0) or balance['total'].get('XBT', 0)
        quantity = (collateral * 10) / price  # 10x leverage approx

        side = 'buy' if action == 'buy' else 'sell'

        # Orden principal market
        main_order = await exchange.create_order(SYMBOL, 'market', side, quantity)
        logger.info(f"ORDEN EJECUTADA → {main_order['id']}")

        # SL reduce-only
        sl_side = 'sell' if action == 'buy' else 'buy'
        await exchange.create_order(SYMBOL, 'stop', sl_side, quantity, stop_loss, params={'reduceOnly': True})

        logger.info(f"SEÑAL → {action.upper()} {quantity:.5f} {SYMBOL} @ {price} | SL {stop_loss}")
        return {"status": "success", "quantity": quantity}

    except Exception as e:
        logger.error(f"ERROR → {str(e)}")
        return {"status": "error", "message": str(e)}