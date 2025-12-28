import asyncio
from fastapi import FastAPI, Request
import os
import ccxt.async_support as ccxt
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Nova Kraken Bot - Reversal Rápido")

exchange = ccxt.krakenfutures({
    'apiKey': os.getenv('KRAKEN_API_KEY'),
    'secret': os.getenv('KRAKEN_SECRET'),
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
})

SYMBOL = 'PF_XBTUSD'

@app.get("/")
async def root():
    return {"status": "Nova Bot 5x + Reversal Rápido activo", "symbol": SYMBOL}

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

        # CÁLCULO 100% EQUITY REAL
        balance = await exchange.fetch_balance()
        logger.info(f"Balance recibido: {balance}")

        available_margin = float(balance['info']['flex']['availableMargin'])

        quantity = round((available_margin * 5) / price, 5)
        if quantity < 0.001:  # mínimo razonable
            return {"status": "error", "message": "quantity demasiado pequeña"}

        side = 'buy' if action == 'buy' else 'sell'
        sl_side = 'sell' if action == 'buy' else 'buy'

        # Reversal: cierra si hay posición contraria
        positions = await exchange.fetch_positions([SYMBOL])
        for pos in positions:
            curr_qty = float(pos.get('contracts', 0))
            curr_side = pos.get('side', '').lower()
            if curr_qty > 0 and curr_side == ('buy' if side == 'sell' else 'sell'):
                await exchange.create_order(SYMBOL, 'market', sl_side, curr_qty)
                logger.info(f"Reversal: cerrado {sl_side} {curr_qty}")
                await asyncio.sleep(2)  # Espera a que libere margen

        # Abre nueva
        main_order = await exchange.create_order(SYMBOL, 'market', side, quantity)
        logger.info(f"ORDEN EJECUTADA → {main_order['id']} | Quantity: {quantity:.5f}")

        # Stop Loss
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

        logger.info(f"SEÑAL → {action.upper()} {quantity:.5f} {SYMBOL} @ {price}")
        return {"status": "success"}

    except Exception as e:
        logger.error(f"ERROR → {str(e)}")
        return {"status": "error", "message": str(e)}