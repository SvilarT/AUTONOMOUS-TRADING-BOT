import os
import logging
import random
from typing import Dict, Any, List
from datetime import datetime, timezone
import aiohttp

logger = logging.getLogger(__name__)


class MarketDataUnavailable(RuntimeError):
    pass


class MarketDataService:
    def __init__(self):
        self.simulation_mode = os.getenv('SIMULATION_MODE', 'True').strip().lower() in {'1', 'true', 'yes', 'on'}
        self.base_url = "https://api.exchange.coinbase.com"
    
    async def get_current_price(self, symbol: str) -> Dict[str, Any]:
        """Get current market price for a symbol.

        Simulation mode may return generated prices. Non-simulation mode fails closed
        instead of silently substituting fake market data.
        """
        if self.simulation_mode:
            return self._simulate_price_data(symbol)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/products/{symbol}/ticker") as response:
                    if response.status != 200:
                        raise MarketDataUnavailable(f"Coinbase ticker returned HTTP {response.status} for {symbol}")

                    data = await response.json()
                    price = data.get('price')
                    if price is None:
                        raise MarketDataUnavailable(f"Coinbase ticker response missing price for {symbol}")

                    return {
                        "symbol": symbol,
                        "price": float(price),
                        "volume": float(data.get('volume', 0)),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "simulation": False,
                    }
        except MarketDataUnavailable:
            raise
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            raise MarketDataUnavailable(f"Market data unavailable for {symbol}") from e
    
    def _simulate_price_data(self, symbol: str) -> Dict[str, Any]:
        """Simulate realistic price data"""
        base_prices = {
            "BTC-USD": 45000.0 + random.uniform(-1000, 1000),
            "ETH-USD": 2500.0 + random.uniform(-100, 100)
        }
        
        price = base_prices.get(symbol, 1000.0)
        
        return {
            "symbol": symbol,
            "price": round(price, 2),
            "volume": random.uniform(100, 1000),
            "change_24h": round(random.uniform(-5, 5), 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "simulation": True
        }
    
    async def get_historical_data(self, symbol: str, periods: int = 100) -> List[Dict[str, Any]]:
        """Get historical price data for analysis.

        Historical data is currently implemented only for simulation mode. In
        non-simulation mode this fails closed to prevent trading decisions from
        being made from generated history.
        """
        if not self.simulation_mode:
            raise MarketDataUnavailable(
                "Historical market data is not implemented for non-simulation mode. "
                "Refusing to return simulated history while SIMULATION_MODE is disabled."
            )

        base_price = 45000.0 if "BTC" in symbol else 2500.0
        data = []
        
        for i in range(periods):
            price = base_price * (1 + random.uniform(-0.02, 0.02))
            data.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "price": round(price, 2),
                "volume": random.uniform(100, 1000),
                "simulation": True,
            })
        
        return data
