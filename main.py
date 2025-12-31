import asyncio
from fastapi import FastAPI, Request
import os
import ccxt.async_support as ccxt
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Nova Kraken Bot - Retry + Long Sleep")

exchange = ccxt.krakenfutures({
    'apiKey': os.getenv('KRAKEN_API_KEY'),
    'secret': os.getenv('KRAKEN_SECRET'),
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
})

SYMBOL = 'PF_XBTUSD'

@app.get("/")
async def root():
    return {"status": "Nova Bot Retry + Long Sleep activo", "symbol": SYMBOL}

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

        # Reversal
        positions = await exchange.fetch_positions([SYMBOL])
        closed = False
        for pos in positions:
            curr_qty = float(pos.get('contracts', 0))
            curr_side = pos.get('side', '').lower()
            if curr_qty > 0 and curr_side != side.lower():
                await exchange.create_order(SYMBOL, 'market', sl_side, curr_qty)
                logger.info(f"Reversal: cerrado {curr_side} {curr_qty}")
                closed = True
                await asyncio.sleep(10)  # más tiempo para liberación

        # Balance
        balance = await exchange.fetch_balance()
        available_margin = 130.0
        try:
            available_margin = float(balance['info']['flex']['availableMargin'])
        except:
            logger.warning("Fallback usado")

        quantity = round((available_margin * 5) / price, 6)
        if quantity < 0.001:
            return {"status": "skipped"}

        # Orden principal con retry + long sleep
        confirmed = False
        for attempt in range(3):
            main_order = await exchange.create_order(SYMBOL, 'market', side, quantity)
            logger.info(f"ORDEN EJECUTADA (attempt {attempt+1}) → {main_order['id']} | Quantity: {quantity}")

            await asyncio.sleep(10)  # long sleep para Kraken actualice

            positions = await exchange.fetch_positions([SYMBOL])
            real_qty = 0.0
            for pos in positions:
                if pos['symbol'] == SYMBOL and pos.get('side', '').lower() == side.lower():
                    real_qty = float(pos.get('contracts', 0))

            if real_qty >= quantity * 0.9:
                logger.info(f"CONFIRMADA en attempt {attempt+1}")
                confirmed = True
                break
            else:
                logger.warning(f"NO confirmada en attempt {attempt+1}")

        if not confirmed:
            logger.error("ORDEN NO CONFIRMADA después de retries")
            return {"status": "failed"}

        # SL
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