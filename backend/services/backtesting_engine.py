import numpy as np
from typing import Dict, List, Any, Tuple
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)

class BacktestingEngine:
    """Backtest trading strategies on historical data"""
    
    def __init__(self):
        self.initial_capital = 10000.0
        self.trades = []
        self.equity_curve = []
    
    async def run_backtest(self, 
                          strategy_signals: List[Dict[str, Any]],
                          historical_data: List[Dict[str, Any]],
                          capital: float = 10000.0) -> Dict[str, Any]:
        """Run a backtest with given strategy signals"""
        
        self.initial_capital = capital
        self.trades = []
        self.equity_curve = [{'timestamp': datetime.now(timezone.utc), 'equity': capital}]
        
        cash = capital
        positions = {}
        equity = capital
        
        for i, signal in enumerate(strategy_signals):
            timestamp = signal.get('timestamp')
            symbol = signal.get('symbol')
            action = signal.get('action')  # BUY, SELL, HOLD
            price = signal.get('price', 0)
            confidence = signal.get('confidence', 0)
            
            if action == 'BUY' and cash > 100:
                # Calculate position size (2% risk per trade)
                position_size = min(cash * 0.02 * (confidence / 100), cash * 0.05)
                
                if position_size >= 10:
                    # Execute buy
                    quantity = position_size / price
                    cash -= position_size
                    
                    positions[symbol] = {
                        'quantity': quantity,
                        'entry_price': price,
                        'entry_time': timestamp,
                        'cost_basis': position_size
                    }
                    
                    self.trades.append({
                        'type': 'BUY',
                        'symbol': symbol,
                        'price': price,
                        'quantity': quantity,
                        'value': position_size,
                        'timestamp': timestamp
                    })
            
            elif action == 'SELL' and symbol in positions:
                # Execute sell
                position = positions[symbol]
                sell_value = position['quantity'] * price
                pnl = sell_value - position['cost_basis']
                pnl_percent = (pnl / position['cost_basis']) * 100
                
                cash += sell_value
                
                self.trades.append({
                    'type': 'SELL',
                    'symbol': symbol,
                    'price': price,
                    'quantity': position['quantity'],
                    'value': sell_value,
                    'pnl': pnl,
                    'pnl_percent': pnl_percent,
                    'timestamp': timestamp,
                    'hold_time': (timestamp - position['entry_time']).total_seconds() / 3600 if isinstance(timestamp, datetime) else 0
                })
                
                del positions[symbol]
            
            # Calculate current equity
            positions_value = sum(p['quantity'] * price for p in positions.values())
            equity = cash + positions_value
            
            self.equity_curve.append({
                'timestamp': timestamp,
                'equity': equity
            })
        
        # Calculate performance metrics
        results = self._calculate_metrics(equity)
        
        return results
    
    def _calculate_metrics(self, final_equity: float) -> Dict[str, Any]:
        """Calculate comprehensive backtest metrics"""
        
        # Basic metrics
        total_return = final_equity - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100
        
        # Trade statistics
        completed_trades = [t for t in self.trades if t['type'] == 'SELL']
        total_trades = len(completed_trades)
        
        winning_trades = [t for t in completed_trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in completed_trades if t.get('pnl', 0) < 0]
        
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
        
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
        
        # Profit factor
        total_wins = sum(t['pnl'] for t in winning_trades)
        total_losses = abs(sum(t['pnl'] for t in losing_trades))
        profit_factor = (total_wins / total_losses) if total_losses > 0 else 0
        
        # Drawdown analysis
        drawdown_data = self._calculate_drawdown()
        
        # Sharpe ratio (simplified)
        sharpe = self._calculate_sharpe_ratio()
        
        return {
            'initial_capital': self.initial_capital,
            'final_equity': final_equity,
            'total_return': round(total_return, 2),
            'total_return_pct': round(total_return_pct, 2),
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(win_rate, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'max_drawdown': drawdown_data['max_drawdown'],
            'max_drawdown_pct': drawdown_data['max_drawdown_pct'],
            'sharpe_ratio': sharpe,
            'equity_curve': self.equity_curve[-100:],  # Last 100 points
            'trades': completed_trades[-20:]  # Last 20 trades
        }
    
    def _calculate_drawdown(self) -> Dict[str, float]:
        """Calculate maximum drawdown"""
        if len(self.equity_curve) < 2:
            return {'max_drawdown': 0, 'max_drawdown_pct': 0}
        
        equity_values = [point['equity'] for point in self.equity_curve]
        peak = equity_values[0]
        max_dd = 0
        max_dd_pct = 0
        
        for equity in equity_values:
            if equity > peak:
                peak = equity
            
            dd = peak - equity
            dd_pct = (dd / peak * 100) if peak > 0 else 0
            
            if dd > max_dd:
                max_dd = dd
                max_dd_pct = dd_pct
        
        return {
            'max_drawdown': round(max_dd, 2),
            'max_drawdown_pct': round(max_dd_pct, 2)
        }
    
    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio (simplified)"""
        if len(self.equity_curve) < 2:
            return 0.0
        
        equity_values = [point['equity'] for point in self.equity_curve]
        returns = np.diff(equity_values) / equity_values[:-1]
        
        if len(returns) == 0:
            return 0.0
        
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        # Annualized Sharpe (assuming daily returns)
        sharpe = (avg_return / std_return) * np.sqrt(252)
        
        return round(float(sharpe), 2)
