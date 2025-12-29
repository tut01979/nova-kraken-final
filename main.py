import asyncio
from fastapi import FastAPI, Request
import os
import ccxt.async_support as ccxt
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Nova Kraken Bot - Check Order")

exchange = ccxt.krakenfutures({
    'apiKey': os.getenv('KRAKEN_API_KEY'),
    'secret': os.getenv('KRAKEN_SECRET'),
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
})

SYMBOL = 'PF_XBTUSD'

@app.get("/")
async def root():
    return {"status": "Nova Bot Check Order activo", "symbol": SYMBOL}

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

        side = 'buy' if action == 'buy' else 'sell'
        sl_side = 'sell' if action == 'buy' else 'buy'

        # Reversal robusto
        positions = await exchange.fetch_positions([SYMBOL])
        closed = False
        for pos in positions:
            curr_qty = float(pos.get('contracts', 0))
            curr_side = pos.get('side', '').lower()
            if curr_qty > 0 and curr_side != side.lower():
                await exchange.create_order(SYMBOL, 'market', sl_side, curr_qty)
                logger.info(f"Reversal: cerrado {curr_side} {curr_qty}")
                closed = True

        if closed:
            await asyncio.sleep(5)
            balance = await exchange.fetch_balance()
        else:
            balance = await exchange.fetch_balance()

        available_margin = 130.0
        try:
            available_margin = float(balance['info']['flex']['availableMargin'])
        except:
            pass

        quantity = round((available_margin * 5) / price, 5)
        if quantity < 0.001:
            return {"status": "error", "message": "quantity pequeña"}

        # Orden principal
        main_order = await exchange.create_order(SYMBOL, 'market', side, quantity)
        logger.info(f"ORDEN ENVIADA → {main_order['id']} | Quantity: {quantity:.5f}")

        # Check si se llenó
        await asyncio.sleep(3)  # Espera fill
        order_status = await exchange.fetch_order(main_order['id'])
        if order_status['status'] == 'closed' or order_status['filled'] > 0:
            logger.info(f"ORDEN CONFIRMADA → filled {order_status['filled']}")
        else:
            logger.warning(f"ORDEN RECHAZADA o no filled → status {order_status['status']}")

        # SL (solo si filled)
        if order_status['filled'] > 0:
            await exchange.create_order(
                SYMBOL,
                'stop',
                sl_side,
                quantity,
                None,
                params={
                    'reduceOnly': True,
                    'triggerSignal': 'last',
                    'triggerPrice': stop_loss
                }
            )
            logger.info(f"SL colocado en {stop_loss}")

        return {"status": "success"}

    except Exception as e:
        logger.error(f"ERROR → {str(e)}")
        return {"status": "error", "message": str(e)}