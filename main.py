import asyncio
from fastapi import FastAPI, Request
import os
import ccxt.async_support as ccxt
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Nova Kraken Bot - Antigua + Delay 10s")

exchange = ccxt.krakenfutures({
    'apiKey': os.getenv('KRAKEN_API_KEY'),
    'secret': os.getenv('KRAKEN_SECRET'),
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
})

SYMBOL = 'PF_XBTUSD'

@app.get("/")
async def root():
    return {"status": "Nova Bot Antigua + Delay 10s activo", "symbol": SYMBOL}

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

        # Balance inicial para comparar
        balance = await exchange.fetch_balance()
        old_margin = 0.0
        try:
            old_margin = float(balance['info']['flex']['availableMargin'])
        except:
            pass

        # Reversal simple
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
            logger.info("Esperando 10 segundos para liberación margen...")
            await asyncio.sleep(10)

            # Re-fetch y check margen liberado
            balance = await exchange.fetch_balance()
            new_margin = 0.0
            try:
                new_margin = float(balance['info']['flex']['availableMargin'])
            except:
                logger.warning("Fallback después delay")

            if new_margin <= old_margin + 10:
                logger.warning("Margen no liberado suficiente, skipped nueva")
                return {"status": "skipped"}

        # Quantity en BTC (como la versión antigua que funcionaba)
        available_margin = 130.0
        try:
            available_margin = float(balance['info']['flex']['availableMargin'])
        except:
            logger.warning("Fallback usado")

        quantity = round((available_margin * 5) / price, 6)
        if quantity < 0.001:
            return {"status": "skipped"}

        # Orden principal
        main_order = await exchange.create_order(SYMBOL, 'market', side, quantity)
        logger.info(f"ORDEN EJECUTADA → {main_order['id']} | Quantity BTC: {quantity}")

        # SL con 'stop' (como la versión antigua)
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