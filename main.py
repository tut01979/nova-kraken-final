import asyncio
import ccxt.async_support as ccxt
import os
import logging

logging.basicConfig(level=logging.INFO)

async def test_connection():
    exchange = ccxt.krakenfutures({
        'apiKey': os.getenv('KRAKEN_API_KEY'),
        'secret': os.getenv('KRAKEN_SECRET'),
        # Si el "truco password" sigue siendo necesario, agrégalo:
        # 'password': os.getenv('KRAKEN_PASSWORD'),  # Crea esta variable si aplica
        'enableRateLimit': True,
        'options': {'defaultType': 'future'},
    })

    try:
        balance = await exchange.fetch_balance()
        print("¡Conexión exitosa! Balance:")
        print(balance)
    except Exception as e:
        print("Error:", str(e))
        print("Tipo de error:", type(e).__name__)
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_connection())