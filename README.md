# Autonomous Trading Bot

An AI-powered cryptocurrency trading bot with GPT-5 market analysis, intelligent risk management, and automated execution on Coinbase Advanced Trade.

## Features

### 🤖 AI-Powered Analysis
- **GPT-5 Integration**: Real-time market analysis using OpenAI's GPT-5 via Emergent LLM key
- **Regime Detection**: Automatically identifies market conditions (Trend/Mean-Reversion/Volatility-Crush/Shock)
- **Signal Generation**: AI-driven buy/sell recommendations with confidence scores
- **Risk Assessment**: Comprehensive risk factor analysis for each trade decision

### 🛡️ Advanced Risk Management
- **Capital Floor Protection**: Hard stop at 97% of all-time high equity (configurable)
- **Daily Loss Limits**: Automatic trading halt at 1.5% daily loss threshold
- **Position Sizing**: Kelly Criterion-based sizing with safety factors
- **Drawdown Monitoring**: Real-time tracking of portfolio drawdown

### 📊 Smart Execution
- **Cost-Aware Trading**: Considers slippage and execution costs
- **Simulation Mode**: Test strategies without real funds
- **Order Management**: Market orders with fill tracking
- **Multi-Symbol Support**: Trade BTC-USD, ETH-USD, and more

### 📈 Beautiful Dashboard
- **Real-Time Metrics**: Live portfolio value, P&L, positions, and trades
- **Risk Dashboard**: Visual display of equity floor, drawdown, and risk limits
- **AI Analysis View**: See GPT-5 market insights and recommendations
- **Trade History**: Complete audit trail of all executed trades

## Tech Stack

**Backend:**
- FastAPI (Python)
- MongoDB (database)
- Coinbase Advanced Trade API
- GPT-5 (via Emergent LLM key)
- JWT authentication

**Frontend:**
- React 19
- Tailwind CSS + shadcn/ui
- Recharts for data visualization
- Axios for API calls

## Getting Started

### 1. Environment Setup

The application runs in **simulation mode** by default. All environment variables are pre-configured in `/app/backend/.env`:

- ✅ **EMERGENT_LLM_KEY**: Already configured for GPT-5 analysis
- ✅ **SIMULATION_MODE**: Set to `True` (uses simulated market data and trades)
- ⚠️ **COINBASE_API_KEY/SECRET**: Empty (add real keys to enable live trading)

### 2. Launch the Application

The services are already running via supervisor:

```bash
# Check service status
sudo supervisorctl status

# Restart services if needed
sudo supervisorctl restart backend frontend
```

### 3. Access the Dashboard

Open your browser to: **http://localhost:3000**

1. **Sign Up**: Create an account with email/password
2. **Dashboard**: View your portfolio (starts with $10,000 simulated capital)
3. **Start Bot**: Toggle the bot switch to begin autonomous trading

### 4. Monitor Trading

- **Overview Tab**: Portfolio metrics, risk stats, recent trades
- **Trades Tab**: Complete trade history with execution details
- **Positions Tab**: Current open positions and P&L
- **AI Analysis Tab**: GPT-5 market analysis and recommendations

## Simulation Mode

**Current Mode**: Simulation ✅

- Uses realistic simulated market data
- Executes "paper trades" with slippage
- No real funds at risk
- Perfect for testing strategies

**Switching to Live Trading** ⚠️

1. Obtain Coinbase Advanced Trade API credentials:
   - Go to https://coinbase.com/developer-platform
   - Create API key with ECDSA (ES256) signature
   - Enable "View" and "Trade" permissions

2. Update `/app/backend/.env`:
   ```
   COINBASE_API_KEY=organizations/{org_id}/apiKeys/{key_id}
   COINBASE_API_SECRET=-----BEGIN EC PRIVATE KEY-----
   YOUR_PRIVATE_KEY_HERE
   -----END EC PRIVATE KEY-----
   SIMULATION_MODE=False
   ```

3. Restart backend:
   ```bash
   sudo supervisorctl restart backend
   ```

⚠️ **Warning**: Live trading involves real financial risk. Start with small amounts.

## Safety Features

The bot includes multiple safety mechanisms:

1. **Capital Floor**: Trading halts if equity drops below 97% of ATH
2. **Daily Loss Limit**: Automatic stop at 1.5% daily loss
3. **Position Limits**: Maximum 5% of capital per trade
4. **Confidence Threshold**: Only trades signals with 60%+ confidence
5. **Cost Validation**: Rejects trades with excessive slippage
6. **Time-to-Live**: Exits stale positions after signal decay

## Trading Strategy

The bot implements a multi-factor approach:

1. **Market Regime Detection**: Classifies current market state
2. **GPT-5 Analysis**: Deep analysis of market conditions
3. **Signal Generation**: BUY/HOLD/SELL with confidence
4. **Risk Validation**: Multi-layer risk checks
5. **Position Sizing**: Kelly-based with safety factors
6. **Execution**: Cost-aware market orders
7. **Monitoring**: Continuous P&L and risk tracking

---

**Built with Emergent** | AI-First Development Platform
