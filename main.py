from fastapi import FastAPI, Request
import os
import ccxt.async_support as ccxt
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Nova - Kraken Futures Bot (Final)")

exchange = ccxt.krakenfutures({
    'apiKey': os.getenv('KRAKEN_API_KEY'),
    'secret': os.getenv('KRAKEN_SECRET'),
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
})

SYMBOL = 'PI_SOLUSD'
QUANTITY = 1.0

@app.get("/")
async def root():
    return {"status": "Nova Bot FINAL activo", "symbol": SYMBOL, "quantity": QUANTITY, "mode": "Usando SL/TP desde Pine Script"}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        payload = await request.json()
        logger.info(f"Webhook recibido: {payload}")

        # Validar campos mínimos
        action = payload.get('action')
        if action not in ['buy', 'sell']:
            return {"status": "error", "message": "action debe ser 'buy' o 'sell'"}

        price = float(payload['price'])
        stop_loss = float(payload['stop_loss'])
        take_profit = float(payload['take_profit'])

        side = 'buy' if action == 'buy' else 'sell'
        sl_side = 'sell' if action == 'buy' else 'buy'
        tp_side = sl_side  # mismo lado para cerrar

        # Orden principal: market
        main_order = await exchange.create_order(
            symbol=SYMBOL,
            type='market',
            side=side,
            amount=QUANTITY,
        )
        fill_price = main_order.get('average') or main_order.get('price') or price
        logger.info(f"Orden principal {action.upper()} ejecutada @ {fill_price}")

        # Stop Loss (reduce-only)
        await exchange.create_order(
            symbol=SYMBOL,
            type='stop',
            side=sl_side,
            amount=QUANTITY,
            price=stop_loss,
            params={'reduce-only': True}
        )

        # Take Profit (limit reduce-only)
        await exchange.create_order(
            symbol=SYMBOL,
            type='limit',
            side=tp_side,
            amount=QUANTITY,
            price=take_profit,
            params={'reduce-only': True, 'postOnly': True}
        )

        logger.info(f"SL colocado en {stop_loss} | TP colocado en {take_profit}")
        return {
            "status": "success",
            "action": action.upper(),
            "fill_price": fill_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit
        }

    except Exception as e:
        logger.error(f"Error crítico en webhook: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}

@app.get("/test-balance")
async def test_balance():
    try:
        balance = await exchange.fetch_balance()
        return {"connection": "SUCCESS", "balance": balance['total']}
    except Exception as e:
        return {"connection": "ERROR", "error": str(e)}