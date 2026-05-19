import React, { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle, FileText, RefreshCw, ShieldCheck, Signature, Siren } from 'lucide-react';
import { toast } from 'sonner';
import { Card } from './ui/card';
import { Button } from './ui/button';
import {
  buildPilotReport,
  emitPilotReconciliationAlerts,
  getPilotExpansionStatus,
  getPilotPendingReconciliation,
  getPilotReadiness,
  getPilotReports,
  getPilotSignoffs,
  resolvePilotReconciliation,
  signoffPilotReport,
} from '../lib/apiClient';

const Pill = ({ children, tone = 'neutral' }) => {
  const classes = {
    good: 'bg-green-500/20 text-green-500',
    warn: 'bg-yellow-500/20 text-yellow-500',
    bad: 'bg-red-500/20 text-red-500',
    neutral: 'bg-muted text-muted-foreground',
  };
  return <span className={`text-xs px-2 py-1 rounded-full ${classes[tone]}`}>{children}</span>;
};

const formatError = (error, fallback) => {
  if (error?.requestId) return `${fallback} Request ID: ${error.requestId}`;
  return error?.message || fallback;
};

const PilotReviewPanel = () => {
  const [loading, setLoading] = useState(true);
  const [readiness, setReadiness] = useState(null);
  const [expansion, setExpansion] = useState(null);
  const [pending, setPending] = useState(null);
  const [reports, setReports] = useState([]);
  const [signoffs, setSignoffs] = useState([]);
  const [selectedOrderId, setSelectedOrderId] = useState('');
  const [notes, setNotes] = useState('');
  const [decision, setDecision] = useState('approved_for_next_tiny_pilot');

  const load = async () => {
    try {
      setLoading(true);
      const [readinessData, expansionData, pendingData, reportsData, signoffsData] = await Promise.all([
        getPilotReadiness(),
        getPilotExpansionStatus(),
        getPilotPendingReconciliation(),
        getPilotReports(),
        getPilotSignoffs(),
      ]);
      setReadiness(readinessData);
      setExpansion(expansionData);
      setPending(pendingData);
      setReports(reportsData.reports || []);
      setSignoffs(signoffsData.signoffs || []);
      const firstPending = pendingData.pending?.[0]?.live_order_id;
      const firstReport = reportsData.reports?.[0]?.live_order_id;
      setSelectedOrderId((current) => current || firstPending || firstReport || '');
    } catch (error) {
      toast.error(formatError(error, 'Failed to load pilot review data.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const resolveSelected = async () => {
    if (!selectedOrderId) return toast.error('Select or enter a live order id.');
    try {
      await resolvePilotReconciliation({ liveOrderId: selectedOrderId, resolution: 'verified_after_live_readonly_reconciliation', notes });
      toast.success('Reconciliation requirement resolved.');
      await load();
    } catch (error) {
      toast.error(formatError(error, 'Failed to resolve reconciliation.'));
    }
  };

  const buildSelectedReport = async () => {
    if (!selectedOrderId) return toast.error('Select or enter a live order id.');
    try {
      await buildPilotReport(selectedOrderId);
      toast.success('Pilot report generated.');
      await load();
    } catch (error) {
      toast.error(formatError(error, 'Failed to build pilot report.'));
    }
  };

  const signoffSelected = async () => {
    if (!selectedOrderId) return toast.error('Select or enter a live order id.');
    try {
      await signoffPilotReport({ liveOrderId: selectedOrderId, decision, notes });
      toast.success('Pilot report signed off.');
      await load();
    } catch (error) {
      toast.error(formatError(error, 'Failed to sign off pilot report.'));
    }
  };

  const emitAlerts = async () => {
    try {
      const result = await emitPilotReconciliationAlerts();
      toast.success(`Alerts emitted: ${result.alerts_emitted || 0}`);
      await load();
    } catch (error) {
      toast.error(formatError(error, 'Failed to emit alerts.'));
    }
  };

  const readyTone = readiness?.ready ? 'good' : 'bad';
  const expansionTone = expansion?.allowed_to_repeat_pilot ? 'good' : 'warn';
  const pendingCount = pending?.pending_count || 0;

  if (loading) {
    return <Card className="glass-card p-6"><p className="text-muted-foreground">Loading pilot review controls...</p></Card>;
  }

  return (
    <div className="space-y-4" data-testid="pilot-review-panel">
      <Card className="glass-card p-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <ShieldCheck className="w-5 h-5 text-primary" />
              <h3 className="text-xl font-semibold">Manual Live Pilot Review</h3>
            </div>
            <p className="text-sm text-muted-foreground">Review readiness, reconciliation, reports, signoffs, and expansion controls.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Pill tone={readyTone}>Readiness: {readiness?.status || 'unknown'}</Pill>
            <Pill tone={expansionTone}>Expansion: {expansion?.status || 'unknown'}</Pill>
            <Pill tone={pendingCount > 0 ? 'bad' : 'good'}>Pending reconciliation: {pendingCount}</Pill>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button onClick={load} variant="outline" size="sm"><RefreshCw className="w-4 h-4 mr-2" />Refresh</Button>
          <Button onClick={emitAlerts} variant="outline" size="sm"><Siren className="w-4 h-4 mr-2" />Emit unresolved alerts</Button>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="glass-card p-6">
          <h4 className="font-semibold mb-3">Readiness Blockers</h4>
          {(readiness?.blockers || []).length === 0 ? (
            <div className="flex items-center gap-2 text-green-500"><CheckCircle className="w-4 h-4" />No readiness blockers reported.</div>
          ) : (
            <div className="space-y-2">
              {readiness.blockers.map((blocker, index) => (
                <div key={index} className="p-3 rounded-lg border border-border">
                  <div className="flex items-center gap-2 text-yellow-500"><AlertTriangle className="w-4 h-4" /><span className="font-medium">{blocker.name}</span></div>
                  <p className="text-sm text-muted-foreground mt-1">{blocker.detail || blocker.severity}</p>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card className="glass-card p-6">
          <h4 className="font-semibold mb-3">Expansion Blockers</h4>
          {(expansion?.blockers || []).length === 0 ? (
            <div className="flex items-center gap-2 text-green-500"><CheckCircle className="w-4 h-4" />No expansion blockers reported.</div>
          ) : (
            <div className="space-y-2">
              {expansion.blockers.map((blocker, index) => (
                <div key={index} className="p-3 rounded-lg border border-border">
                  <div className="flex items-center gap-2 text-yellow-500"><AlertTriangle className="w-4 h-4" /><span className="font-medium">{blocker.name}</span></div>
                  <p className="text-sm text-muted-foreground mt-1">Count: {blocker.count}</p>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Card className="glass-card p-6">
        <h4 className="font-semibold mb-3">Operator Actions</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
          <input className="bg-background border border-border rounded-md px-3 py-2 text-sm" placeholder="live_order_id" value={selectedOrderId} onChange={(e) => setSelectedOrderId(e.target.value)} />
          <select className="bg-background border border-border rounded-md px-3 py-2 text-sm" value={decision} onChange={(e) => setDecision(e.target.value)}>
            <option value="approved_for_next_tiny_pilot">Approve next tiny pilot</option>
            <option value="hold">Hold</option>
            <option value="reject">Reject</option>
            <option value="manual_investigation_required">Manual investigation required</option>
          </select>
          <input className="bg-background border border-border rounded-md px-3 py-2 text-sm" placeholder="operator notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={resolveSelected} variant="outline" size="sm">Resolve reconciliation</Button>
          <Button onClick={buildSelectedReport} variant="outline" size="sm"><FileText className="w-4 h-4 mr-2" />Build report</Button>
          <Button onClick={signoffSelected} variant="outline" size="sm"><Signature className="w-4 h-4 mr-2" />Sign off</Button>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="glass-card p-6">
          <h4 className="font-semibold mb-3">Pending Reconciliation</h4>
          {(pending?.pending || []).slice(0, 5).map((item) => (
            <button key={item.live_order_id} onClick={() => setSelectedOrderId(item.live_order_id)} className="w-full text-left p-3 rounded-lg border border-border mb-2 hover:bg-muted/10">
              <p className="font-medium text-sm">{item.live_order_id}</p>
              <p className="text-xs text-muted-foreground">{item.created_at}</p>
            </button>
          ))}
          {pendingCount === 0 && <p className="text-sm text-muted-foreground">No pending requirements.</p>}
        </Card>

        <Card className="glass-card p-6">
          <h4 className="font-semibold mb-3">Pilot Reports</h4>
          {reports.slice(0, 5).map((report) => (
            <button key={report.live_order_id} onClick={() => setSelectedOrderId(report.live_order_id)} className="w-full text-left p-3 rounded-lg border border-border mb-2 hover:bg-muted/10">
              <p className="font-medium text-sm">{report.live_order_id}</p>
              <p className="text-xs text-muted-foreground">{report.status} • {report.report_hash?.slice(0, 12)}</p>
            </button>
          ))}
          {reports.length === 0 && <p className="text-sm text-muted-foreground">No pilot reports yet.</p>}
        </Card>

        <Card className="glass-card p-6">
          <h4 className="font-semibold mb-3">Signoffs</h4>
          {signoffs.slice(0, 5).map((signoff) => (
            <div key={signoff.live_order_id} className="p-3 rounded-lg border border-border mb-2">
              <p className="font-medium text-sm">{signoff.live_order_id}</p>
              <p className="text-xs text-muted-foreground">{signoff.decision} • {signoff.signoff_hash?.slice(0, 12)}</p>
            </div>
          ))}
          {signoffs.length === 0 && <p className="text-sm text-muted-foreground">No signoffs yet.</p>}
        </Card>
      </div>
    </div>
  );
};

export default PilotReviewPanel;
