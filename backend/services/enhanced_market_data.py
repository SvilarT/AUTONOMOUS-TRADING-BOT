import os
import logging
import random
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta
import aiohttp

logger = logging.getLogger(__name__)

class EnhancedMarketDataService:
    def __init__(self):
        self.simulation_mode = os.getenv('SIMULATION_MODE', 'True') == 'True'
        self.base_url = "https://api.exchange.coinbase.com"
        self.price_history = {}  # Cache for historical data
    
    async def get_historical_prices(self, symbol: str, periods: int = 100) -> List[float]:
        """Get historical price data for technical analysis"""
        if self.simulation_mode:
            return self._simulate_historical_prices(symbol, periods)
        
        try:
            # In live mode, fetch real historical data from Coinbase
            async with aiohttp.ClientSession() as session:
                # Coinbase candles endpoint
                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(hours=periods)
                
                params = {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat(),
                    'granularity': 3600  # 1 hour candles
                }
                
                async with session.get(
                    f"{self.base_url}/products/{symbol}/candles",
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Extract closing prices
                        prices = [float(candle[4]) for candle in data]  # Close price is index 4
                        prices.reverse()  # Oldest to newest
                        return prices
                    else:
                        return self._simulate_historical_prices(symbol, periods)
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return self._simulate_historical_prices(symbol, periods)
    
    def _simulate_historical_prices(self, symbol: str, periods: int) -> List[float]:
        """Simulate realistic historical price data with trends"""
        base_prices = {
            "BTC-USD": 45000.0,
            "ETH-USD": 2500.0
        }
        
        base_price = base_prices.get(symbol, 1000.0)
        prices = []
        current_price = base_price
        
        # Create realistic price movement with trend
        trend = random.choice([-1, 0, 1])  # -1: downtrend, 0: sideways, 1: uptrend
        volatility = 0.02  # 2% volatility
        
        for i in range(periods):
            # Random walk with trend bias
            change = random.gauss(trend * 0.001, volatility)
            current_price = current_price * (1 + change)
            prices.append(current_price)
        
        return prices
    
    async def get_current_price(self, symbol: str) -> Dict[str, Any]:
        """Get current market price with volume data"""
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
