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

        if not payload:
            logger.warning("Payload vacío ignorado")
            return {"status": "ignored", "message": "payload vacío"}

        action = payload.get('action')
        if action not in ['buy', 'sell']:
            logger.error("Action inválido")
            return {"status": "error", "message": "action debe ser buy o sell"}

        price = float(payload['price'])
        stop_loss = float(payload['stop_loss'])

        # CÁLCULO 100% EQUITY REAL
        balance = await exchange.fetch_balance()
        logger.info(f"Balance recibido: {balance}")

        available_margin = 41.0  # fallback
        if 'info' in balance and 'flex' in balance['info'] and 'availableMargin' in balance['info']['flex']:
            available_margin = float(balance['info']['flex']['availableMargin'])
        elif 'total' in balance:
            available_margin = float(balance['total'].get('USD', 41.0))

        quantity = (available_margin * 10) / price  # 10x

        side = 'buy' if action == 'buy' else 'sell'
        sl_side = 'sell' if action == 'buy' else 'buy'

        # Orden principal market
        main_order = await exchange.create_order(SYMBOL, 'market', side, quantity)
        logger.info(f"ORDEN EJECUTADA → {main_order['id']} | Quantity: {quantity:.5f}")

        # Stop Loss reduce-only (tipo correcto para Kraken Futures)
        await exchange.create_order(
            SYMBOL, 
            'stopLoss',  # tipo correcto
            sl_side, 
            quantity, 
            stop_loss, 
            params={'reduceOnly': True}
        )
        logger.info(f"SL colocado en {stop_loss}")

        logger.info(f"SEÑAL → {action.upper()} {quantity:.5f} {SYMBOL} @ {price}")
        return {"status": "success", "quantity": quantity, "sl": stop_loss}

    except Exception as e:
        logger.error(f"ERROR → {str(e)}")
        return {"status": "error", "message": str(e)}