// Environment configuration
export const config = {
  apiUrl: process.env.NEXT_PUBLIC_API_URL || 'https://ned-production.up.railway.app',
  wsUrl: process.env.NEXT_PUBLIC_WS_URL || 'wss://ned-production.up.railway.app',
  isDevelopment: process.env.NODE_ENV === 'development',
  isProduction: process.env.NODE_ENV === 'production',
} as const;

export default config;