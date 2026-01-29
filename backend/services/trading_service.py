from coinbase.rest import RESTClient
import os
import logging
from typing import Dict, Any, Optional
import random
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class TradingService:
    def __init__(self):
        self.simulation_mode = os.getenv('SIMULATION_MODE', 'True') == 'True'
        self.api_key = os.getenv('COINBASE_API_KEY', '')
        self.api_secret = os.getenv('COINBASE_API_SECRET', '')
        
        if not self.simulation_mode and self.api_key and self.api_secret:
            try:
                self.client = RESTClient(api_key=self.api_key, api_secret=self.api_secret)
                logger.info("Coinbase client initialized for live trading")
            except Exception as e:
                logger.error(f"Failed to initialize Coinbase client: {e}")
                self.simulation_mode = True
                logger.info("Falling back to simulation mode")
        else:
            self.simulation_mode = True
            logger.info("Running in simulation mode")
    
    async def place_market_order(self, symbol: str, side: str, quantity: float) -> Dict[str, Any]:
        """Place a market order (simulated or real)"""
        if self.simulation_mode:
            return self._simulate_market_order(symbol, side, quantity)
        
        try:
            if side == "BUY":
                result = self.client.market_order_buy(
                    client_order_id=f"order_{int(datetime.now().timestamp() * 1000)}",
                    product_id=symbol,
                    quote_size=str(quantity)
                )
            else:
                result = self.client.market_order_sell(
                    client_order_id=f"order_{int(datetime.now().timestamp() * 1000)}",
                    product_id=symbol,
                    base_size=str(quantity)
                )
            
            if result.get('success'):
                response = result['success_response']
                return {
                    "success": True,
                    "order_id": response.get('order_id'),
                    "status": "filled",
                    "filled_price": float(response.get('fills', [{}])[0].get('price', 0)) if response.get('fills') else None
                }
            else:
                return {"success": False, "error": result.get('error_response')}
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {"success": False, "error": str(e)}
    
    def _simulate_market_order(self, symbol: str, side: str, quantity: float) -> Dict[str, Any]:
        """Simulate a market order with realistic slippage"""
        # Simulated prices
        base_prices = {
            "BTC-USD": 45000.0,
            "ETH-USD": 2500.0
        }
        
        base_price = base_prices.get(symbol, 1000.0)
        # Add realistic slippage (0.1% - 0.3%)
        slippage = random.uniform(0.001, 0.003)
        filled_price = base_price * (1 + slippage if side == "BUY" else 1 - slippage)
        
        return {
            "success": True,
            "order_id": f"sim_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            "status": "filled",
            "filled_price": round(filled_price, 2),
            "simulation": True
        }
    
    async def get_account_balance(self) -> Dict[str, Any]:
        """Get account balance"""
        if self.simulation_mode:
            return {
                "cash_balance": 10000.0,
                "simulation": True
            }
        
        try:
            accounts = self.client.get_accounts()
            return {"accounts": accounts.to_dict()}
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return {"error": str(e)}
