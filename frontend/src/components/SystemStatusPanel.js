import React, { useEffect, useState } from 'react';
import { Activity, AlertTriangle, CheckCircle, Server } from 'lucide-react';
import { Card } from './ui/card';
import { getOperationalReadiness, getTradingMode, getWorkerStatus } from '../lib/apiClient';

const StatusPill = ({ label, tone = 'neutral' }) => {
  const classes = {
    good: 'bg-green-500/20 text-green-500',
    warn: 'bg-yellow-500/20 text-yellow-500',
    bad: 'bg-red-500/20 text-red-500',
    neutral: 'bg-muted text-muted-foreground',
  };
  return <span className={`text-xs px-2 py-1 rounded-full ${classes[tone]}`}>{label}</span>;
};

const SystemStatusPanel = () => {
  const [mode, setMode] = useState(null);
  const [readiness, setReadiness] = useState(null);
  const [workers, setWorkers] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const [modeData, readinessData, workerData] = await Promise.all([
          getTradingMode(),
          getOperationalReadiness(false),
          getWorkerStatus(),
        ]);
        if (!active) return;
        setMode(modeData);
        setReadiness(readinessData);
        setWorkers(workerData.workers || []);
        setError(null);
      } catch (err) {
        if (!active) return;
        setError(err);
      }
    };
    load();
    const interval = setInterval(load, 15000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  const staleWorkers = workers.filter((worker) => worker.stale).length;
  const readinessOk = readiness?.status === 'ready' || readiness?.ready === true || readiness?.status === 'ok';
  const modeLabel = mode?.mode || mode?.trading_mode || 'unknown';

  return (
    <Card className="glass-card p-4 mb-6" data-testid="system-status-panel">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Server className="w-5 h-5 text-primary" />
            <h3 className="text-lg font-semibold">System Status</h3>
          </div>
          <p className="text-sm text-muted-foreground">
            Paper-production visibility for trading mode, readiness, and worker health.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusPill label={`Mode: ${modeLabel}`} tone={modeLabel === 'paper' ? 'good' : 'warn'} />
          <StatusPill label={`Readiness: ${readinessOk ? 'OK' : 'Check'}`} tone={readinessOk ? 'good' : 'warn'} />
          <StatusPill label={`Workers: ${workers.length}`} tone={staleWorkers > 0 ? 'warn' : 'good'} />
          {error && <StatusPill label={`Status error: ${error.requestId || error.code}`} tone="bad" />}
        </div>
      </div>

      {workers.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4">
          {workers.slice(0, 3).map((worker) => (
            <div key={worker.worker_id} className="rounded-lg border border-border p-3">
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className="text-sm font-medium truncate">{worker.worker_id}</span>
                {worker.stale ? <AlertTriangle className="w-4 h-4 text-yellow-500" /> : <CheckCircle className="w-4 h-4 text-green-500" />}
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Activity className="w-3 h-3" />
                <span>{worker.status} • {worker.active_bots?.length || 0} active bots</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
};

export default SystemStatusPanel;
