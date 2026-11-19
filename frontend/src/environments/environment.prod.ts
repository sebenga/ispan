export const environment = {
  production: true,
  apiBaseUrl: '/api/v1',
  legalApiBaseUrl: '/api',
  /** Socket.IO service on Render (same Blueprint). */
  realtimeUrl: 'https://ispan-realtime.onrender.com',
  legalVersion: '2026-11-19',
  paymentTestMode: true,
  supportedLanguages: ['en', 'xh', 'af', 'zu'] as const,
};
