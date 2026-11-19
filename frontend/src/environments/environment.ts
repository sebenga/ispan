export const environment = {
  production: false,
  apiBaseUrl: 'http://localhost:8001/api/v1',
  /** Also exposed at /api/legal/ for the brief's path shape */
  legalApiBaseUrl: 'http://localhost:8001/api',
  realtimeUrl: 'http://localhost:4000',
  legalVersion: '2026-11-19',
  paymentTestMode: true,
  supportedLanguages: ['en', 'xh', 'af', 'zu'] as const,
};
