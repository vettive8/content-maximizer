function normalizeBaseUrl(rawValue) {
  const value = String(rawValue || '').trim();
  if (!value) {
    return '';
  }
  return value.replace(/\/+$/, '');
}

function inferLocalApiBaseUrl() {
  if (typeof window === 'undefined' || !window.location) {
    return 'http://localhost:5000';
  }

  const protocol = window.location.protocol || 'http:';
  const hostname = window.location.hostname || 'localhost';
  return `${protocol}//${hostname}:5000`;
}

export const API_BASE_URL =
  normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL) || inferLocalApiBaseUrl();

export function apiUrl(path = '') {
  const normalizedPath = String(path || '').trim();
  if (!normalizedPath) {
    return API_BASE_URL;
  }
  return `${API_BASE_URL}${normalizedPath.startsWith('/') ? normalizedPath : `/${normalizedPath}`}`;
}

export function rewriteLegacyBackendUrl(inputUrl) {
  const url = String(inputUrl || '');
  if (!url) {
    return url;
  }

  if (url.startsWith('/api/')) {
    return apiUrl(url);
  }

  if (url.startsWith('http://localhost:5000')) {
    return `${API_BASE_URL}${url.slice('http://localhost:5000'.length)}`;
  }

  if (url.startsWith('http://127.0.0.1:5000')) {
    return `${API_BASE_URL}${url.slice('http://127.0.0.1:5000'.length)}`;
  }

  return url;
}

function rewriteRequestInput(input) {
  if (typeof input === 'string') {
    return rewriteLegacyBackendUrl(input);
  }

  if (input instanceof URL) {
    return rewriteLegacyBackendUrl(input.toString());
  }

  if (typeof Request !== 'undefined' && input instanceof Request) {
    const rewrittenUrl = rewriteLegacyBackendUrl(input.url);
    if (rewrittenUrl === input.url) {
      return input;
    }
    return new Request(rewrittenUrl, input);
  }

  return input;
}

export function installBackendFetchRewrite() {
  if (typeof window === 'undefined' || typeof window.fetch !== 'function') {
    return;
  }
  if (window.__backendFetchRewriteInstalled) {
    return;
  }

  const originalFetch = window.fetch.bind(window);
  window.fetch = (input, init) => originalFetch(rewriteRequestInput(input), init);
  window.__backendFetchRewriteInstalled = true;
}
