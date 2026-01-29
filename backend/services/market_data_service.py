import os
import logging
import random
from typing import Dict, Any, List
from datetime import datetime, timezone
import aiohttp

logger = logging.getLogger(__name__)

class MarketDataService:
    def __init__(self):
        self.simulation_mode = os.getenv('SIMULATION_MODE', 'True') == 'True'
        self.base_url = "https://api.exchange.coinbase.com"
    
    async def get_current_price(self, symbol: str) -> Dict[str, Any]:
        """Get current market price for a symbol"""
        if self.simulation_mode:
            return self._simulate_price_data(symbol)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/products/{symbol}/ticker") as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "symbol": symbol,
                            "price": float(data.get('price', 0)),
                            "volume": float(data.get('volume', 0)),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    else:
                        return self._simulate_price_data(symbol)
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            return self._simulate_price_data(symbol)
    
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
        """Get historical price data for analysis"""
        # Simulate historical data
        base_price = 45000.0 if "BTC" in symbol else 2500.0
        data = []
        
        for i in range(periods):
            price = base_price * (1 + random.uniform(-0.02, 0.02))
            data.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "price": round(price, 2),
                "volume": random.uniform(100, 1000)
            })
        
        return data
