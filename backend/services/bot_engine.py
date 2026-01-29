import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import os

from services.market_data_service import MarketDataService
from services.enhanced_market_data import EnhancedMarketDataService
from services.ai_analysis_service import AIAnalysisService
from services.trading_service import TradingService
from services.risk_manager import RiskManager
from services.technical_indicators import TechnicalIndicators
from services.multi_timeframe_analysis import MultiTimeframeAnalysis
from services.advanced_risk_manager import AdvancedRiskManager

logger = logging.getLogger(__name__)

class BotEngine:
    def __init__(self, db):
        self.db = db
        self.market_service = MarketDataService()
        self.enhanced_market_service = EnhancedMarketDataService()
        self.ai_service = AIAnalysisService()
        self.trading_service = TradingService()
        self.risk_manager = RiskManager()
        self.tech_indicators = TechnicalIndicators()
        self.mtf_analysis = MultiTimeframeAnalysis()
        self.advanced_risk = AdvancedRiskManager()
        self.running = False
        self.price_history_cache = {}  # Cache for correlation analysis
    
    async def start(self, user_id: str):
        """Start the trading bot for a user"""
        self.running = True
        logger.info(f"Starting bot for user {user_id}")
        
        while self.running:
            try:
                await self.trading_cycle(user_id)
                await asyncio.sleep(60)  # Run every 60 seconds
            except Exception as e:
                logger.error(f"Bot cycle error: {e}")
                await asyncio.sleep(60)
    
    async def stop(self):
        """Stop the trading bot"""
        self.running = False
        logger.info("Bot stopped")
    
    async def trading_cycle(self, user_id: str):
        """Execute one trading cycle"""
        # Get bot config
        config = await self.db.bot_configs.find_one({"user_id": user_id}, {"_id": 0})
        if not config or not config.get('is_active'):
            return
        
        # Update positions with current prices and P&L
        await self.update_positions(user_id)
        
        # Update risk metrics
        await self.update_risk_metrics(user_id)
        
        symbols = config.get('symbols', ['BTC-USD', 'ETH-USD'])
        
        for symbol in symbols:
            try:
                await self.analyze_and_trade(user_id, symbol, config)
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
    
    async def update_positions(self, user_id: str):
        """Update all positions with current prices and P&L"""
        positions = await self.db.positions.find({"user_id": user_id}, {"_id": 0}).to_list(100)
        
        for position in positions:
            try:
                # Get current price
                price_data = await self.market_service.get_current_price(position['symbol'])
                current_price = price_data.get('price', position['avg_price'])
                
                # Calculate P&L
                quantity = position['quantity']
                avg_price = position['avg_price']
                position_value = (quantity / avg_price) * current_price  # Value in USD
                pnl = position_value - quantity  # quantity is the cost basis in USD
                pnl_percent = (pnl / quantity) * 100 if quantity > 0 else 0
                
                # Update position
                await self.db.positions.update_one(
                    {"user_id": user_id, "symbol": position['symbol']},
                    {"$set": {
                        "current_price": current_price,
                        "pnl": pnl,
                        "pnl_percent": pnl_percent,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
            except Exception as e:
                logger.error(f"Error updating position {position['symbol']}: {e}")
    
    async def update_risk_metrics(self, user_id: str):
        """Update risk metrics with current portfolio state"""
        # Get all positions
        positions = await self.db.positions.find({"user_id": user_id}, {"_id": 0}).to_list(100)
        
        # Calculate positions value and total P&L
        positions_value = sum(p['quantity'] for p in positions)  # Total invested
        total_pnl = sum(p.get('pnl', 0) for p in positions)
        
        # Get previous metrics
        prev_metrics = await self.db.risk_metrics.find_one(
            {"user_id": user_id},
            {"_id": 0},
            sort=[("timestamp", -1)]
        )
        
        if prev_metrics:
            starting_equity = prev_metrics.get('max_equity', 10000.0)
            cash_balance = prev_metrics.get('cash_balance', 10000.0)
            max_equity = prev_metrics.get('max_equity', 10000.0)
        else:
            starting_equity = 10000.0
            cash_balance = 10000.0
            max_equity = 10000.0
        
        # Calculate total equity
        total_equity = cash_balance + positions_value + total_pnl
        
        # Update max equity if current is higher
        if total_equity > max_equity:
            max_equity = total_equity
        
        # Calculate equity floor and drawdown
        equity_floor = max_equity * 0.97
        current_drawdown = ((max_equity - total_equity) / max_equity * 100) if max_equity > 0 else 0
        
        # Get today's starting equity for daily P&L
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        daily_start_metrics = await self.db.risk_metrics.find_one(
            {
                "user_id": user_id,
                "timestamp": {"$gte": today_start.isoformat()}
            },
            {"_id": 0},
            sort=[("timestamp", 1)]
        )
        
        if daily_start_metrics:
            daily_start_equity = daily_start_metrics.get('total_equity', starting_equity)
        else:
            daily_start_equity = starting_equity
        
        daily_pnl = total_equity - daily_start_equity
        
        # Create new metrics entry
        new_metrics = {
            "user_id": user_id,
            "total_equity": total_equity,
            "max_equity": max_equity,
            "equity_floor": equity_floor,
            "current_drawdown": current_drawdown,
            "daily_pnl": daily_pnl,
            "positions_value": positions_value,
            "cash_balance": cash_balance,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.risk_metrics.insert_one(new_metrics)
    
    async def analyze_and_trade(self, user_id: str, symbol: str, config: Dict[str, Any]):
        """Analyze market and execute trade if conditions are met"""
        # 1. Get market data with historical prices for technical analysis
        price_data = await self.market_service.get_current_price(symbol)
        current_price = price_data.get('price', 0)
        
        # Get historical prices for technical indicators
        historical_prices = await self.enhanced_market_service.get_historical_prices(symbol, periods=100)
        
        # Cache price history for correlation analysis
        self.price_history_cache[symbol] = historical_prices
        
        # 2. Calculate technical indicators
        rsi = self.tech_indicators.calculate_rsi(historical_prices)
        macd = self.tech_indicators.calculate_macd(historical_prices)
        bollinger = self.tech_indicators.calculate_bollinger_bands(historical_prices)
        
        # 3. Multi-timeframe analysis
        mtf_analysis = self.mtf_analysis.analyze_timeframes(historical_prices)
        mtf_recommendation = self.mtf_analysis.get_trading_recommendation(
            mtf_analysis, 
            current_position=False  # Will update later
        )
        
        # 4. Detect market regime
        regime = self.tech_indicators.detect_market_regime(historical_prices, rsi, macd, bollinger)
        
        # 5. Generate technical signals
        tech_signals = self.tech_indicators.generate_trading_signals(
            rsi, macd, bollinger, current_price, regime
        )
        
        # 6. Get current risk metrics
        risk_metrics = await self.db.risk_metrics.find_one(
            {"user_id": user_id},
            {"_id": 0},
            sort=[("timestamp", -1)]
        )
        
        if not risk_metrics:
            # Initialize default metrics
            risk_metrics = {
                "total_equity": 10000.0,
                "max_equity": 10000.0,
                "daily_pnl": 0.0,
                "cash_balance": 10000.0
            }
        
        # 7. Get all positions for advanced risk analysis
        all_positions = await self.db.positions.find({"user_id": user_id}, {"_id": 0}).to_list(100)
        
        # 8. Calculate portfolio heat
        portfolio_heat = self.advanced_risk.calculate_portfolio_heat(
            all_positions,
            risk_metrics.get('total_equity', 10000.0)
        )
        
        # 9. Check if we have an open position for this symbol
        existing_position = await self.db.positions.find_one(
            {"user_id": user_id, "symbol": symbol},
            {"_id": 0}
        )
        
        # Update MTF recommendation with position info
        mtf_recommendation = self.mtf_analysis.get_trading_recommendation(
            mtf_analysis,
            current_position=existing_position is not None
        )
        
        # 10. Enhanced AI analysis with technical indicators and MTF
        market_indicators = {
            "regime": regime,
            "volatility": "high" if bollinger['bandwidth'] > 5 else "medium" if bollinger['bandwidth'] > 2 else "low",
            "trend": "bullish" if price_data.get('change_24h', 0) > 0 else "bearish",
            "rsi": rsi,
            "macd_histogram": macd['histogram'],
            "technical_signal": tech_signals['signal'],
            "mtf_alignment": mtf_analysis['alignment'],
            "mtf_strength": mtf_analysis['strength']
        }
        
        analysis = await self.ai_service.analyze_market(symbol, price_data, market_indicators)
        
        # Combine AI, technical, and MTF analysis
        ai_confidence = analysis.get('confidence', 50)
        tech_confidence = tech_signals['confidence']
        mtf_confidence = mtf_recommendation['confidence']
        
        # Weighted combination: AI 40%, Technical 30%, MTF 30%
        combined_confidence = (ai_confidence * 0.4 + tech_confidence * 0.3 + mtf_confidence * 0.3)
        combined_signal = analysis.get('signal', 'HOLD')
        
        # If signals disagree, be more conservative
        signals = [tech_signals['signal'], mtf_recommendation['action'], combined_signal]
        if len(set(signals)) > 1:  # Not all agree
            combined_confidence *= 0.75  # Reduce confidence by 25%
        
        # Boost confidence if all signals align
        if tech_signals['signal'] == mtf_recommendation['action'] == combined_signal:
            combined_confidence = min(combined_confidence * 1.15, 95)  # Boost by 15%
        
        # Enhanced analysis with all data
        enhanced_analysis = {
            **analysis,
            "combined_confidence": combined_confidence,
            "technical_indicators": {
                "rsi": rsi,
                "macd": macd,
                "bollinger_bands": bollinger,
                "regime": regime
            },
            "technical_signals": tech_signals,
            "multi_timeframe": mtf_analysis,
            "mtf_recommendation": mtf_recommendation,
            "portfolio_heat": portfolio_heat
        }
        
        # Save enhanced analysis to DB
        analysis_doc = enhanced_analysis.copy()
        await self.db.market_analysis.insert_one(analysis_doc)
        
        logger.info(f"{symbol} | Regime: {regime} | RSI: {rsi} | MACD: {macd['histogram']} | MTF: {mtf_analysis['alignment']} | Heat: {portfolio_heat['heat_percent']:.1f}% | Tech: {tech_signals['signal']} | Conf: {combined_confidence:.1f}%")
        
        # 11. Decide: BUY or SELL
        if existing_position:
            # We have a position - check if we should sell
            await self.check_sell_signal(user_id, symbol, existing_position, enhanced_analysis, current_price, tech_signals)
        else:
            # No position - check if we should buy
            enhanced_analysis['confidence'] = combined_confidence
            enhanced_analysis['buy_recommendation'] = (
                tech_signals['signal'] == 'BUY' and 
                mtf_recommendation['action'] == 'BUY' and
                analysis.get('buy_recommendation', False)
            )
            await self.check_buy_signal(user_id, symbol, enhanced_analysis, risk_metrics, current_price, all_positions)
    
    async def check_buy_signal(self, user_id: str, symbol: str, analysis: Dict[str, Any], 
                                risk_metrics: Dict[str, Any], current_price: float, all_positions: List[Dict[str, Any]]):
        """Check if we should open a new position with advanced risk management"""
        # 1. Basic risk validation
        validation = self.risk_manager.validate_trade(analysis, risk_metrics)
        
        if not validation['approved']:
            logger.info(f"Trade not approved for {symbol}: {validation['reason']}")
            return
        
        if not analysis.get('buy_recommendation'):
            logger.info(f"No buy recommendation for {symbol}")
            return
        
        # 2. Advanced risk checks
        portfolio_heat = analysis.get('portfolio_heat', {})
        
        # Check portfolio heat
        if portfolio_heat.get('heat_percent', 0) >= 15:
            logger.info(f"Trade rejected for {symbol}: Portfolio heat too high ({portfolio_heat['heat_percent']:.1f}%)")
            return
        
        # Check correlation with existing positions
        correlation_check = self.advanced_risk.check_correlation_risk(
            symbol,
            all_positions,
            self.price_history_cache
        )
        
        if not correlation_check['allowed']:
            logger.info(f"Trade rejected for {symbol}: High correlation ({correlation_check['max_correlation']:.2f}) with {correlation_check['correlated_with']}")
            return
        
        # 3. Calculate optimal position size with advanced risk management
        current_heat = portfolio_heat.get('heat_percent', 0) / 100
        
        position_size = self.advanced_risk.calculate_optimal_position_size(
            signal_strength=analysis.get('confidence', 0) / 100,
            volatility=0.10,
            total_equity=risk_metrics.get('total_equity', 10000.0),
            current_heat=current_heat,
            max_heat=0.15
        )
        
        if position_size < 10:
            logger.info(f"Trade rejected for {symbol}: Position size too small (${position_size:.2f})")
            return
            
            # Place order
            order_result = await self.trading_service.place_market_order(
                symbol=symbol,
                side="BUY",
                quantity=position_size
            )
            
            if order_result.get('success'):
                filled_price = order_result.get('filled_price', current_price)
                
                # Record trade
                trade = {
                    "user_id": user_id,
                    "symbol": symbol,
                    "side": "BUY",
                    "order_type": "market",
                    "quantity": position_size,
                    "filled_price": filled_price,
                    "status": "filled",
                    "ai_reasoning": analysis.get('ai_analysis'),
                    "regime": analysis.get('regime'),
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                await self.db.trades.insert_one(trade)
                
                # Create position
                position = {
                    "user_id": user_id,
                    "symbol": symbol,
                    "quantity": position_size,  # USD value invested
                    "avg_price": filled_price,
                    "current_price": filled_price,
                    "pnl": 0.0,
                    "pnl_percent": 0.0,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                await self.db.positions.insert_one(position)
                
                # Update cash balance
                new_cash = risk_metrics.get('cash_balance', 10000.0) - position_size
                await self.db.risk_metrics.update_one(
                    {"user_id": user_id},
                    {"$set": {"cash_balance": new_cash}},
                    sort=[("timestamp", -1)]
                )
                
                logger.info(f"Trade executed: {symbol} BUY ${position_size}")
        else:
            logger.info(f"Trade not approved for {symbol}: {validation['reason']}")
    
    async def check_sell_signal(self, user_id: str, symbol: str, position: Dict[str, Any],
                                  analysis: Dict[str, Any], current_price: float, tech_signals: Dict[str, Any]):
        """Check if we should close an existing position with enhanced technical analysis"""
        # Calculate current P&L
        quantity = position['quantity']
        avg_price = position['avg_price']
        entry_price = position.get('entry_price', avg_price)  # Track original entry for trailing stop
        position_value = (quantity / avg_price) * current_price
        pnl = position_value - quantity
        pnl_percent = (pnl / quantity) * 100 if quantity > 0 else 0
        
        # Get high water mark for trailing stop
        high_water_mark = position.get('high_water_mark', avg_price)
        if current_price > high_water_mark:
            high_water_mark = current_price
            # Update high water mark in DB
            await self.db.positions.update_one(
                {"user_id": user_id, "symbol": symbol},
                {"$set": {"high_water_mark": high_water_mark}}
            )
        
        should_sell = False
        sell_reason = ""
        
        # Get technical indicators from analysis
        tech_indicators = analysis.get('technical_indicators', {})
        rsi = tech_indicators.get('rsi', 50)
        regime = tech_indicators.get('regime', 'neutral')
        
        # Enhanced sell conditions with technical analysis:
        
        # 1. Trailing Stop Loss (protects profits)
        trailing_stop_percent = 2.0  # Trail by 2% from high
        drawdown_from_high = ((high_water_mark - current_price) / high_water_mark * 100) if high_water_mark > 0 else 0
        if pnl_percent > 3.0 and drawdown_from_high >= trailing_stop_percent:
            should_sell = True
            sell_reason = f"Trailing stop triggered (down {drawdown_from_high:.1f}% from high)"
        
        # 2. Profit target reached (5% gain)
        elif pnl_percent >= 5.0:
            should_sell = True
            sell_reason = "Profit target reached (+5%)"
        
        # 3. Hard stop loss triggered (3% loss)
        elif pnl_percent <= -3.0:
            should_sell = True
            sell_reason = "Stop loss triggered (-3%)"
        
        # 4. Technical indicators suggest sell
        elif tech_signals.get('signal') == 'SELL' and tech_signals.get('confidence', 0) > 70:
            should_sell = True
            sell_reason = f"Strong technical sell signal (confidence: {tech_signals['confidence']}%)"
        
        # 5. Overbought conditions + profit (take profit on RSI overbought)
        elif rsi > 70 and pnl_percent > 2.0:
            should_sell = True
            sell_reason = f"RSI overbought ({rsi:.1f}) with profit - taking gains"
        
        # 6. Market regime change to bearish
        elif regime in ['strong_downtrend', 'downtrend'] and pnl_percent < 3.0:
            should_sell = True
            sell_reason = f"Market regime changed to {regime}"
        
        # 7. AI + Technical both recommend sell
        elif (analysis.get('signal') == 'SELL' or not analysis.get('buy_recommendation')) and tech_signals.get('signal') == 'SELL':
            if analysis.get('combined_confidence', 0) > 60:
                should_sell = True
                sell_reason = "Combined AI + Technical sell signal"
        
        # 8. Position held too long (24 hours) with no significant gain
        from datetime import datetime, timezone
        created_at = datetime.fromisoformat(position['created_at'].replace('Z', '+00:00'))
        hours_held = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600
        if hours_held > 24 and pnl_percent < 2.0:
            should_sell = True
            sell_reason = "Time-based exit (24h hold with <2% gain)"
        
        if should_sell:
            # Execute sell order
            order_result = await self.trading_service.place_market_order(
                symbol=symbol,
                side="SELL",
                quantity=quantity  # Sell the USD value
            )
            
            if order_result.get('success'):
                filled_price = order_result.get('filled_price', current_price)
                
                # Calculate final P&L
                final_value = (quantity / avg_price) * filled_price
                final_pnl = final_value - quantity
                
                # Record sell trade
                trade = {
                    "user_id": user_id,
                    "symbol": symbol,
                    "side": "SELL",
                    "order_type": "market",
                    "quantity": quantity,
                    "filled_price": filled_price,
                    "status": "filled",
                    "ai_reasoning": sell_reason,
                    "regime": analysis.get('regime'),
                    "pnl": final_pnl,
                    "pnl_percent": pnl_percent,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                await self.db.trades.insert_one(trade)
                
                # Remove position
                await self.db.positions.delete_one(
                    {"user_id": user_id, "symbol": symbol}
                )
                
                # Update cash balance (add back initial + profit/loss)
                risk_metrics = await self.db.risk_metrics.find_one(
                    {"user_id": user_id},
                    {"_id": 0},
                    sort=[("timestamp", -1)]
                )
                new_cash = risk_metrics.get('cash_balance', 10000.0) + final_value
                await self.db.risk_metrics.update_one(
                    {"user_id": user_id},
                    {"$set": {"cash_balance": new_cash}},
                    sort=[("timestamp", -1)]
                )
                
                logger.info(f"Position closed: {symbol} SELL ${quantity:.2f} | P&L: ${final_pnl:.2f} ({pnl_percent:.2f}%) | Reason: {sell_reason}")
        else:
            logger.info(f"Holding {symbol} position | P&L: ${pnl:.2f} ({pnl_percent:.2f}%)")
