import logging
from typing import Dict, Any, List
import numpy as np

logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(self, capital_floor_pct: float = 0.97, max_daily_loss_pct: float = 0.015):
        self.capital_floor_pct = capital_floor_pct
        self.max_daily_loss_pct = max_daily_loss_pct
    
    def check_capital_floor(self, current_equity: float, max_equity: float) -> Dict[str, Any]:
        """Check if equity is above the capital floor"""
        equity_floor = max_equity * self.capital_floor_pct
        current_ratio = current_equity / max_equity if max_equity > 0 else 1.0
        
        breach = current_equity < equity_floor
        buffer = ((current_equity - equity_floor) / equity_floor * 100) if equity_floor > 0 else 0
        
        return {
            "equity_floor": equity_floor,
            "current_equity": current_equity,
            "current_ratio": current_ratio,
            "floor_breach": breach,
            "buffer_percent": round(buffer, 2),
            "allow_trading": not breach
        }
    
    def check_daily_loss(self, daily_pnl: float, starting_equity: float) -> Dict[str, Any]:
        """Check if daily loss exceeds threshold"""
        max_loss = starting_equity * self.max_daily_loss_pct
        loss_pct = (daily_pnl / starting_equity * 100) if starting_equity > 0 else 0
        
        breach = daily_pnl < -max_loss
        
        return {
            "daily_pnl": daily_pnl,
            "loss_percent": round(loss_pct, 2),
            "max_allowed_loss": max_loss,
            "loss_breach": breach,
            "allow_trading": not breach
        }
    
    def calculate_position_size(self, 
                                 signal_strength: float,
                                 confidence: float,
                                 available_capital: float,
                                 volatility: float = 0.1) -> float:
        """Calculate optimal position size using Kelly Criterion with safety factors"""
        # Simplified Kelly with heavy safety discount
        edge = signal_strength * (confidence / 100)
        
        # Safety factor: never risk more than 2% per trade
        max_risk_per_trade = 0.02
        
        # Kelly fraction with 0.25x leverage (very conservative)
        kelly_fraction = edge / (volatility ** 2) if volatility > 0 else 0
        kelly_fraction = min(kelly_fraction * 0.25, max_risk_per_trade)
        
        position_size = available_capital * kelly_fraction
        
        # Minimum position: $10, Maximum: 5% of capital
        position_size = max(10, min(position_size, available_capital * 0.05))
        
        return round(position_size, 2)
    
    def validate_trade(self, 
                       signal: Dict[str, Any],
                       risk_metrics: Dict[str, Any]) -> Dict[str, bool]:
        """Validate if a trade should be executed based on all risk checks"""
        
        # Check 1: Capital floor
        floor_check = self.check_capital_floor(
            risk_metrics.get('total_equity', 0),
            risk_metrics.get('max_equity', 0)
        )
        
        # Check 2: Daily loss
        loss_check = self.check_daily_loss(
            risk_metrics.get('daily_pnl', 0),
            risk_metrics.get('max_equity', 0)
        )
        
        # Check 3: Signal confidence threshold
        confidence_ok = signal.get('confidence', 0) >= 60
        
        # Check 4: Signal strength
        strong_signal = signal.get('buy_recommendation', False)
        
        all_checks_pass = (
            floor_check['allow_trading'] and
            loss_check['allow_trading'] and
            confidence_ok and
            strong_signal
        )
        
        return {
            "approved": all_checks_pass,
            "floor_check": floor_check['allow_trading'],
            "loss_check": loss_check['allow_trading'],
            "confidence_check": confidence_ok,
            "signal_check": strong_signal,
            "reason": self._get_rejection_reason(floor_check, loss_check, confidence_ok, strong_signal)
        }
    
    def _get_rejection_reason(self, floor_check, loss_check, confidence_ok, strong_signal) -> str:
        if not floor_check['allow_trading']:
            return "Capital floor breach - trading halted"
        if not loss_check['allow_trading']:
            return "Daily loss limit reached"
        if not confidence_ok:
            return "Signal confidence too low"
        if not strong_signal:
            return "No strong buy signal"
        return "All checks passed"
