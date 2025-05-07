import math
import os
from dotenv import load_dotenv
from binance.um_futures import UMFutures

load_dotenv()
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")

client = UMFutures(key=api_key, secret=api_secret)
symbol_step_cache = {}

def load_step_sizes():
    """Загружает stepSize из exchangeInfo один раз."""
    info = client.exchange_info()
    for s in info["symbols"]:
        symbol = s["symbol"]
        for f in s["filters"]:
            if f["filterType"] == "LOT_SIZE":
                symbol_step_cache[symbol] = float(f["stepSize"])
                break

def adjust_quantity(symbol: str, qty: float) -> float:
    """Округляет quantity по stepSize."""
    step = symbol_step_cache.get(symbol)
    if not step:
        return round(qty, 3)
    precision = abs(int(round(math.log10(step))))
    return round(qty, precision)
