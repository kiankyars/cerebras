export class ApiKeyError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ApiKeyError';
  }
}

export function getApiKeys() {
  if (typeof window === 'undefined') return { googleApiKey: '', trellisApiKey: '' };
  
  return {
    googleApiKey: localStorage.getItem('GOOGLE_API_KEY') || '',
    trellisApiKey: localStorage.getItem('TRELLIS_API_KEY') || ''
  };
}

export function validateApiKeys(): boolean {
  const { googleApiKey, trellisApiKey } = getApiKeys();
  return Boolean(googleApiKey && trellisApiKey);
}

export function getHeaders() {
  const { googleApiKey, trellisApiKey } = getApiKeys();
  
  if (!googleApiKey || !trellisApiKey) {
    throw new ApiKeyError('API keys are not set. Please configure them in the settings.');
  }
  
  return {
    'X-Google-API-Key': googleApiKey,
    'X-Trellis-API-Key': trellisApiKey
  };
}

export function checkApiKeys() {
  if (!validateApiKeys()) {
    throw new ApiKeyError('API keys are not set. Please configure them in the settings.');
  }
} 