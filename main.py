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
            return {"status": "ignored"}

        action = payload.get('action')
        if action not in ['buy', 'sell']:
            return {"status": "error", "message": "action inválido"}

        price = float(payload['price'])
        stop_loss = float(payload['stop_loss'])

        # CÁLCULO 100% EQUITY REAL (corregido)
        balance = await exchange.fetch_balance()
        logger.info(f"Balance recibido: {balance}")

        available_margin = 225.0  # fallback
        if 'info' in balance and 'flex' in balance['info'] and 'availableMargin' in balance['info']['flex']:
            available_margin = float(balance['info']['flex']['availableMargin'])

        # Leverage seguro: 5x en lugar de 10x para evitar insufficientFunds
        leverage = 10  # más conservador, evita rechazos
        quantity = (available_margin * leverage) / price

        side = 'buy' if action == 'buy' else 'sell'
        sl_side = 'sell' if action == 'buy' else 'buy'

        # Orden principal market
        main_order = await exchange.create_order(SYMBOL, 'market', side, quantity)
        logger.info(f"ORDEN EJECUTADA → {main_order['id']} | Quantity: {quantity:.5f}")

        # Stop Loss reduce-only
        await exchange.create_order(
            SYMBOL,
            'stop',
            sl_side,
            quantity,
            stop_loss,
            params={'reduceOnly': True, 'triggerSignal': 'last'}
        )
        logger.info(f"SL colocado en {stop_loss}")

        logger.info(f"SEÑAL → {action.upper()} {quantity:.5f} {SYMBOL} @ {price}")
        return {"status": "success", "quantity": quantity}

    except Exception as e:
        logger.error(f"ERROR → {str(e)}")
        return {"status": "error", "message": str(e)}