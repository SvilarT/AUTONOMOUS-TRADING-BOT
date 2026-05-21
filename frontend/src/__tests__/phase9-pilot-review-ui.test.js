const fs = require('fs');
const path = require('path');

const srcPath = (...parts) => path.join(__dirname, '..', ...parts);

describe('Phase 9 pilot review UI verification', () => {
  test('App exposes authenticated pilot review route', () => {
    const app = fs.readFileSync(srcPath('App.js'), 'utf8');

    expect(app).toContain("import PilotReviewPage from './components/PilotReviewPage'");
    expect(app).toContain('path="/pilot-review"');
    expect(app).toContain('<PilotReviewPage user={user} onLogout={handleLogout} />');
  });

  test('pilot review panel imports required API helpers', () => {
    const panel = fs.readFileSync(srcPath('components', 'PilotReviewPanel.js'), 'utf8');

    [
      'getPilotReadiness',
      'getPilotExpansionStatus',
      'getPilotPendingReconciliation',
      'getPilotReports',
      'getPilotSignoffs',
      'resolvePilotReconciliation',
      'buildPilotReport',
      'signoffPilotReport',
      'emitPilotReconciliationAlerts',
    ].forEach((helper) => expect(panel).toContain(helper));
  });

  test('API client contains all pilot review endpoint paths', () => {
    const apiClient = fs.readFileSync(srcPath('lib', 'apiClient.js'), 'utf8');

    [
      '/live-trading/pilot-readiness',
      '/live-trading/pilot/expansion-status',
      '/live-trading/pilot/pending-reconciliation',
      '/live-trading/pilot/reports',
      '/live-trading/pilot/signoffs',
      '/live-trading/pilot/resolve-reconciliation',
      '/live-trading/pilot/report',
      '/live-trading/pilot/signoff',
      '/live-trading/pilot/unresolved-reconciliation-alerts',
    ].forEach((endpoint) => expect(apiClient).toContain(endpoint));
  });
});
