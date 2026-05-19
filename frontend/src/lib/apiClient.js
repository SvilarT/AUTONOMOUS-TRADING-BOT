import axios from 'axios';

export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API_BASE_URL = `${BACKEND_URL}/api`;

export class ApiClientError extends Error {
  constructor({ code, message, requestId, status, details }) {
    super(message || 'API request failed');
    this.name = 'ApiClientError';
    this.code = code || 'API_ERROR';
    this.requestId = requestId || null;
    this.status = status || null;
    this.details = details || {};
  }
}

export function createRequestId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `req-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function normalizeApiError(error) {
  const response = error?.response;
  const envelope = response?.data?.error;
  const requestId = response?.headers?.['x-request-id'] || envelope?.request_id || null;

  if (envelope) {
    return new ApiClientError({
      code: envelope.code,
      message: envelope.message,
      requestId,
      status: response.status,
      details: envelope.details || {},
    });
  }

  if (response) {
    return new ApiClientError({
      code: `HTTP_${response.status}`,
      message: response.statusText || 'HTTP request failed',
      requestId,
      status: response.status,
      details: response.data || {},
    });
  }

  return new ApiClientError({
    code: 'NETWORK_ERROR',
    message: error?.message || 'Network request failed',
    requestId: null,
    status: null,
    details: {},
  });
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  config.headers['X-Request-ID'] = config.headers['X-Request-ID'] || createRequestId();
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(normalizeApiError(error))
);

export async function getTradingMode() {
  const response = await apiClient.get('/trading-mode');
  return response.data;
}

export async function getOperationalReadiness(strict = false) {
  const response = await apiClient.get(`/ops/readiness?strict=${strict ? 'true' : 'false'}`);
  return response.data;
}

export async function getWorkerStatus() {
  const response = await apiClient.get('/ops/workers');
  return response.data;
}

export async function getLiveReadonlyStatus() {
  const response = await apiClient.get('/live-readonly/status');
  return response.data;
}

export async function getPilotReadiness() {
  const response = await apiClient.get('/live-trading/pilot-readiness');
  return response.data;
}

export async function getPilotExpansionStatus() {
  const response = await apiClient.get('/live-trading/pilot/expansion-status');
  return response.data;
}

export async function getPilotPendingReconciliation(limit = 100) {
  const response = await apiClient.get(`/live-trading/pilot/pending-reconciliation?limit=${limit}`);
  return response.data;
}

export async function getPilotReports(limit = 100) {
  const response = await apiClient.get(`/live-trading/pilot/reports?limit=${limit}`);
  return response.data;
}

export async function getPilotSignoffs(limit = 100) {
  const response = await apiClient.get(`/live-trading/pilot/signoffs?limit=${limit}`);
  return response.data;
}

export async function resolvePilotReconciliation({ liveOrderId, resolution, notes }) {
  const response = await apiClient.post('/live-trading/pilot/resolve-reconciliation', {
    live_order_id: liveOrderId,
    resolution,
    notes,
  });
  return response.data;
}

export async function buildPilotReport(liveOrderId) {
  const response = await apiClient.post('/live-trading/pilot/report', {
    live_order_id: liveOrderId,
  });
  return response.data;
}

export async function signoffPilotReport({ liveOrderId, decision, notes }) {
  const response = await apiClient.post('/live-trading/pilot/signoff', {
    live_order_id: liveOrderId,
    decision,
    notes,
  });
  return response.data;
}

export async function emitPilotReconciliationAlerts() {
  const response = await apiClient.post('/live-trading/pilot/unresolved-reconciliation-alerts');
  return response.data;
}
