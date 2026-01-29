import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API } from '../App';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Switch } from './ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { toast } from 'sonner';
import { 
  TrendingUp, 
  TrendingDown,
  DollarSign, 
  Activity, 
  BarChart3, 
  LogOut,
  Brain,
  AlertTriangle,
  CheckCircle,
  Clock
} from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const Dashboard = ({ user, onLogout }) => {
  const [stats, setStats] = useState(null);
  const [botActive, setBotActive] = useState(false);
  const [trades, setTrades] = useState([]);
  const [positions, setPositions] = useState([]);
  const [riskMetrics, setRiskMetrics] = useState(null);
  const [marketAnalysis, setMarketAnalysis] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 10000); // Update every 10s
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [statsRes, tradesRes, positionsRes, riskRes, configRes] = await Promise.all([
        axios.get(`${API}/dashboard/stats`),
        axios.get(`${API}/trades`),
        axios.get(`${API}/positions`),
        axios.get(`${API}/risk-metrics`),
        axios.get(`${API}/bot-config`)
      ]);

      setStats(statsRes.data);
      setTrades(tradesRes.data.trades || []);
      setPositions(positionsRes.data.positions || []);
      setRiskMetrics(riskRes.data);
      setBotActive(configRes.data?.is_active || false);

      // Fetch market analysis for each symbol
      try {
        const btcAnalysis = await axios.get(`${API}/market-analysis?symbol=BTC-USD`);
        const ethAnalysis = await axios.get(`${API}/market-analysis?symbol=ETH-USD`);
        setMarketAnalysis({
          'BTC-USD': btcAnalysis.data,
          'ETH-USD': ethAnalysis.data
        });
      } catch (e) {
        // Analysis not available yet
      }

      setLoading(false);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      toast.error('Failed to load dashboard data');
      setLoading(false);
    }
  };

  const toggleBot = async () => {
    try {
      const endpoint = botActive ? `${API}/bot/stop` : `${API}/bot/start`;
      await axios.post(endpoint);
      setBotActive(!botActive);
      toast.success(botActive ? 'Bot stopped' : 'Bot started');
      fetchDashboardData();
    } catch (error) {
      toast.error('Failed to toggle bot');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-4 md:p-6 lg:p-8 relative">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
          <div>
            <h1 className="text-4xl font-bold mb-2" data-testid="dashboard-title">Trading Dashboard</h1>
            <p className="text-muted-foreground">Welcome back, {user?.email}</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 glass-card px-4 py-2 rounded-lg">
              <span className={`status-dot ${botActive ? 'active' : 'inactive'}`}></span>
              <span className="text-sm font-medium">Bot {botActive ? 'Active' : 'Inactive'}</span>
            </div>
            <Button onClick={onLogout} variant="outline" size="sm" data-testid="logout-button">
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>

        {/* Bot Control */}
        <Card className="glass-card p-6 mb-6" data-testid="bot-control-card">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div>
              <h3 className="text-xl font-semibold mb-1">Autonomous Trading Bot</h3>
              <p className="text-sm text-muted-foreground">
                AI-powered market analysis with GPT-5 | Capital protection enabled
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium">{botActive ? 'Running' : 'Stopped'}</span>
              <Switch checked={botActive} onCheckedChange={toggleBot} data-testid="bot-toggle" />
            </div>
          </div>
        </Card>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <Card className="metric-card" data-testid="total-equity-card">
            <div className="flex justify-between items-start mb-4">
              <div>
                <p className="text-sm text-muted-foreground mb-1">Total Equity</p>
                <h3 className="text-2xl font-bold">${stats?.total_equity?.toLocaleString() || '0'}</h3>
              </div>
              <DollarSign className="w-8 h-8 text-primary opacity-50" />
            </div>
            <div className="flex items-center gap-2 text-sm">
              {stats?.daily_pnl >= 0 ? (
                <TrendingUp className="w-4 h-4 text-green-500" />
              ) : (
                <TrendingDown className="w-4 h-4 text-red-500" />
              )}
              <span className={stats?.daily_pnl >= 0 ? 'text-green-500' : 'text-red-500'}>
                ${Math.abs(stats?.daily_pnl || 0).toFixed(2)} today
              </span>
            </div>
          </Card>

          <Card className="metric-card" data-testid="positions-card">
            <div className="flex justify-between items-start mb-4">
              <div>
                <p className="text-sm text-muted-foreground mb-1">Active Positions</p>
                <h3 className="text-2xl font-bold">{stats?.total_positions || 0}</h3>
              </div>
              <BarChart3 className="w-8 h-8 text-blue-400 opacity-50" />
            </div>
            <p className="text-sm text-muted-foreground">Across {positions.length} symbols</p>
          </Card>

          <Card className="metric-card" data-testid="trades-card">
            <div className="flex justify-between items-start mb-4">
              <div>
                <p className="text-sm text-muted-foreground mb-1">Total Trades</p>
                <h3 className="text-2xl font-bold">{stats?.total_trades || 0}</h3>
              </div>
              <Activity className="w-8 h-8 text-purple-400 opacity-50" />
            </div>
            <p className="text-sm text-muted-foreground">All time executed</p>
          </Card>

          <Card className="metric-card" data-testid="drawdown-card">
            <div className="flex justify-between items-start mb-4">
              <div>
                <p className="text-sm text-muted-foreground mb-1">Current Drawdown</p>
                <h3 className="text-2xl font-bold">{(stats?.current_drawdown || 0).toFixed(2)}%</h3>
              </div>
              {stats?.current_drawdown > 2 ? (
                <AlertTriangle className="w-8 h-8 text-yellow-400 opacity-50" />
              ) : (
                <CheckCircle className="w-8 h-8 text-green-500 opacity-50" />
              )}
            </div>
            <p className="text-sm text-muted-foreground">Risk threshold: 3%</p>
          </Card>
        </div>

        {/* Main Content Tabs */}
        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList className="glass-card">
            <TabsTrigger value="overview" data-testid="tab-overview">Overview</TabsTrigger>
            <TabsTrigger value="trades" data-testid="tab-trades">Trades</TabsTrigger>
            <TabsTrigger value="positions" data-testid="tab-positions">Positions</TabsTrigger>
            <TabsTrigger value="analysis" data-testid="tab-analysis">AI Analysis</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            {/* Risk Metrics */}
            <Card className="glass-card p-6" data-testid="risk-metrics-card">
              <h3 className="text-xl font-semibold mb-4">Risk Metrics</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Max Equity</p>
                  <p className="text-lg font-semibold">${riskMetrics?.max_equity?.toLocaleString() || '0'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Equity Floor</p>
                  <p className="text-lg font-semibold">${riskMetrics?.equity_floor?.toLocaleString() || '0'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Cash Balance</p>
                  <p className="text-lg font-semibold">${riskMetrics?.cash_balance?.toLocaleString() || '0'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Positions Value</p>
                  <p className="text-lg font-semibold">${riskMetrics?.positions_value?.toLocaleString() || '0'}</p>
                </div>
              </div>
            </Card>

            {/* Recent Activity */}
            <Card className="glass-card p-6" data-testid="recent-trades-card">
              <h3 className="text-xl font-semibold mb-4">Recent Trades</h3>
              <div className="space-y-2 max-h-96 overflow-y-auto scrollbar-thin">
                {trades.slice(0, 10).map((trade, idx) => (
                  <div key={idx} className="trade-row p-4 rounded-lg border border-border">
                    <div className="flex justify-between items-center">
                      <div>
                        <p className="font-medium">{trade.symbol}</p>
                        <p className="text-sm text-muted-foreground">
                          {trade.side} • {trade.status}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="font-medium">${trade.quantity?.toFixed(2)}</p>
                        <p className="text-sm text-muted-foreground">
                          {trade.filled_price ? `@$${trade.filled_price}` : 'Pending'}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
                {trades.length === 0 && (
                  <p className="text-center text-muted-foreground py-8">No trades yet. Start the bot to begin trading.</p>
                )}
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="trades">
            <Card className="glass-card p-6" data-testid="all-trades-card">
              <h3 className="text-xl font-semibold mb-4">All Trades</h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Time</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Symbol</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Side</th>
                      <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">Quantity</th>
                      <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">Price</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map((trade, idx) => (
                      <tr key={idx} className="border-b border-border hover:bg-muted/5">
                        <td className="py-3 px-4 text-sm">
                          {new Date(trade.created_at).toLocaleString()}
                        </td>
                        <td className="py-3 px-4 font-medium">{trade.symbol}</td>
                        <td className="py-3 px-4">
                          <span className={`text-sm font-medium ${trade.side === 'BUY' ? 'text-green-500' : 'text-red-500'}`}>
                            {trade.side}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">${trade.quantity?.toFixed(2)}</td>
                        <td className="py-3 px-4 text-right">
                          {trade.filled_price ? `$${trade.filled_price}` : '-'}
                        </td>
                        <td className="py-3 px-4">
                          <span className={`text-xs px-2 py-1 rounded-full ${
                            trade.status === 'filled' ? 'bg-green-500/20 text-green-500' : 'bg-yellow-500/20 text-yellow-500'
                          }`}>
                            {trade.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {trades.length === 0 && (
                  <p className="text-center text-muted-foreground py-12">No trades executed yet</p>
                )}
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="positions">
            <Card className="glass-card p-6" data-testid="positions-list-card">
              <h3 className="text-xl font-semibold mb-4">Open Positions</h3>
              {positions.length > 0 ? (
                <div className="space-y-4">
                  {positions.map((position, idx) => (
                    <div key={idx} className="p-4 rounded-lg border border-border">
                      <div className="flex justify-between items-center">
                        <div>
                          <h4 className="font-semibold text-lg">{position.symbol}</h4>
                          <p className="text-sm text-muted-foreground">Qty: {position.quantity}</p>
                        </div>
                        <div className="text-right">
                          <p className="font-medium">Avg: ${position.avg_price}</p>
                          <p className={`text-sm ${
                            position.pnl >= 0 ? 'text-green-500' : 'text-red-500'
                          }`}>
                            {position.pnl >= 0 ? '+' : ''}{position.pnl_percent?.toFixed(2)}%
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center text-muted-foreground py-12">No open positions</p>
              )}
            </Card>
          </TabsContent>

          <TabsContent value="analysis">
            <div className="space-y-4">
              {['BTC-USD', 'ETH-USD'].map((symbol) => {
                const analysis = marketAnalysis[symbol];
                return (
                  <Card key={symbol} className="glass-card p-6" data-testid={`analysis-${symbol}`}>
                    <div className="flex items-start gap-4 mb-4">
                      <Brain className="w-8 h-8 text-primary" />
                      <div className="flex-1">
                        <h3 className="text-xl font-semibold mb-1">{symbol} Analysis</h3>
                        <p className="text-sm text-muted-foreground">GPT-5 Market Intelligence</p>
                      </div>
                      {analysis && (
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                          analysis.buy_recommendation 
                            ? 'bg-green-500/20 text-green-500' 
                            : 'bg-gray-500/20 text-gray-400'
                        }`}>
                          {analysis.signal || 'HOLD'}
                        </span>
                      )}
                    </div>

                    {analysis ? (
                      <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <p className="text-sm text-muted-foreground mb-1">Regime</p>
                            <p className="font-medium capitalize">{analysis.regime}</p>
                          </div>
                          <div>
                            <p className="text-sm text-muted-foreground mb-1">Confidence</p>
                            <p className="font-medium">{analysis.confidence}%</p>
                          </div>
                        </div>
                        
                        <div>
                          <p className="text-sm text-muted-foreground mb-2">AI Analysis:</p>
                          <p className="text-sm leading-relaxed">{analysis.ai_analysis}</p>
                        </div>

                        {analysis.risks && (
                          <div>
                            <p className="text-sm text-muted-foreground mb-2">Risk Factors:</p>
                            <p className="text-sm leading-relaxed text-yellow-500">{analysis.risks}</p>
                          </div>
                        )}

                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Clock className="w-4 h-4" />
                          <span>{new Date(analysis.timestamp).toLocaleString()}</span>
                        </div>
                      </div>
                    ) : (
                      <p className="text-center text-muted-foreground py-8">
                        No analysis available yet. Start the bot to begin analysis.
                      </p>
                    )}
                  </Card>
                );
              })}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default Dashboard;
