from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)

class AdvancedOrderManager:
    """Manage advanced order types: limit, stop-limit, OCO, etc."""
    
    def __init__(self, db, trading_service):
        self.db = db
        self.trading_service = trading_service
        self.pending_orders = {}  # order_id -> order details
    
    async def place_limit_order(self, user_id: str, symbol: str, side: str, 
                                 quantity: float, limit_price: float, 
                                 time_in_force: str = 'GTC') -> Dict[str, Any]:
        """Place a limit order"""
        order = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'symbol': symbol,
            'side': side,
            'type': 'LIMIT',
            'quantity': quantity,
            'limit_price': limit_price,
            'time_in_force': time_in_force,
            'status': 'PENDING',
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Save to database
        await self.db.pending_orders.insert_one(order)
        self.pending_orders[order['id']] = order
        
        logger.info(f"Limit order placed: {symbol} {side} {quantity} @ ${limit_price}")
        
        return {
            'success': True,
            'order_id': order['id'],
            'status': 'PENDING'
        }
    
    async def place_stop_limit_order(self, user_id: str, symbol: str, side: str,
                                      quantity: float, stop_price: float, 
                                      limit_price: float) -> Dict[str, Any]:
        """Place a stop-limit order"""
        order = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'symbol': symbol,
            'side': side,
            'type': 'STOP_LIMIT',
            'quantity': quantity,
            'stop_price': stop_price,
            'limit_price': limit_price,
            'status': 'PENDING',
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.pending_orders.insert_one(order)
        self.pending_orders[order['id']] = order
        
        logger.info(f"Stop-limit order placed: {symbol} {side} stop@${stop_price} limit@${limit_price}")
        
        return {
            'success': True,
            'order_id': order['id'],
            'status': 'PENDING'
        }
    
    async def place_oco_order(self, user_id: str, symbol: str, quantity: float,
                               take_profit_price: float, stop_loss_price: float) -> Dict[str, Any]:
        """Place One-Cancels-Other order (take profit + stop loss)"""
        order = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'symbol': symbol,
            'type': 'OCO',
            'quantity': quantity,
            'take_profit_price': take_profit_price,
            'stop_loss_price': stop_loss_price,
            'status': 'PENDING',
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.pending_orders.insert_one(order)
        self.pending_orders[order['id']] = order
        
        logger.info(f"OCO order placed: {symbol} TP@${take_profit_price} SL@${stop_loss_price}")
        
        return {
            'success': True,
            'order_id': order['id'],
            'status': 'PENDING'
        }
    
    async def check_pending_orders(self, current_prices: Dict[str, float]):
        """Check and execute pending orders based on current prices"""
        executed_orders = []
        
        for order_id, order in list(self.pending_orders.items()):
            symbol = order['symbol']
            current_price = current_prices.get(symbol, 0)
            
            if current_price == 0:
                continue
            
            should_execute = False
            
            # Check limit orders
            if order['type'] == 'LIMIT':
                if order['side'] == 'BUY' and current_price <= order['limit_price']:
                    should_execute = True
                elif order['side'] == 'SELL' and current_price >= order['limit_price']:
                    should_execute = True
            
            # Check stop-limit orders
            elif order['type'] == 'STOP_LIMIT':
                if order['side'] == 'BUY' and current_price >= order['stop_price']:
                    # Convert to limit order
                    if current_price <= order['limit_price']:
                        should_execute = True
                elif order['side'] == 'SELL' and current_price <= order['stop_price']:
                    if current_price >= order['limit_price']:
                        should_execute = True
            
            # Check OCO orders
            elif order['type'] == 'OCO':
                if current_price >= order['take_profit_price']:
                    order['side'] = 'SELL'
                    order['executed_reason'] = 'Take Profit'
                    should_execute = True
                elif current_price <= order['stop_loss_price']:
                    order['side'] = 'SELL'
                    order['executed_reason'] = 'Stop Loss'
                    should_execute = True
            
            if should_execute:
                # Execute the order
                result = await self.trading_service.place_market_order(
                    symbol=symbol,
                    side=order['side'],
                    quantity=order['quantity']
                )
                
                if result.get('success'):
                    order['status'] = 'EXECUTED'
                    order['executed_at'] = datetime.now(timezone.utc).isoformat()
                    order['executed_price'] = result.get('filled_price', current_price)
                    
                    # Update in database
                    await self.db.pending_orders.update_one(
                        {'id': order_id},
                        {'$set': {'status': 'EXECUTED', 'executed_at': order['executed_at']}}
                    )
                    
                    executed_orders.append(order)
                    del self.pending_orders[order_id]
                    
                    logger.info(f"Order executed: {order['type']} {symbol} @ ${order['executed_price']}")
        
        return executed_orders
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel a pending order"""
        if order_id in self.pending_orders:
            del self.pending_orders[order_id]
            
            await self.db.pending_orders.update_one(
                {'id': order_id},
                {'$set': {'status': 'CANCELLED', 'cancelled_at': datetime.now(timezone.utc).isoformat()}}
            )
            
            return {'success': True, 'message': 'Order cancelled'}
        else:
            return {'success': False, 'message': 'Order not found'}
    
    async def get_pending_orders(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all pending orders for a user"""
        orders = await self.db.pending_orders.find(
            {'user_id': user_id, 'status': 'PENDING'},
            {'_id': 0}
        ).to_list(100)
        
        return orders
