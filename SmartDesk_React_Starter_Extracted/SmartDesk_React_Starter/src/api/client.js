const API_BASE = (import.meta.env?.VITE_API_BASE_URL || 'http://localhost:8000/api').replace(/\/$/, '');
let csrfToken = null;
const UNSAFE_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);
const CSRF_FAILURE_EVENT = 'smartdesk:csrf-failed';
const SESSION_EXPIRED_EVENT = 'smartdesk:session-expired';

export class ApiError extends Error {
  constructor(status, payload) {
    const error = payload?.error || {};
    super(error.message || `Request failed (${status}).`);
    this.name = 'ApiError';
    this.status = status;
    this.code = error.code || 'api_error';
    this.details = error.details || {};
  }
}

export class ApiNetworkError extends Error {
  constructor(cause) {
    super('SmartDesk could not reach the backend. Check the connection and try again.', { cause });
    this.name = 'ApiNetworkError';
  }
}

async function parseResponse(response) {
  if (response.status === 204) return null;
  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json') ? await response.json() : null;
  if (!response.ok) throw new ApiError(response.status, payload);
  return payload;
}

function dispatchBrowserEvent(name) {
  if (typeof window !== 'undefined' && typeof window.dispatchEvent === 'function') {
    window.dispatchEvent(new Event(name));
  }
}

async function send(path, options = {}, csrfRetry = false) {
  const { method = 'GET', body, headers = {} } = options;
  const requestHeaders = new Headers(headers);
  const upperMethod = method.toUpperCase();
  if (UNSAFE_METHODS.has(upperMethod)) {
    if (!csrfToken) await bootstrapCsrf();
    requestHeaders.set('X-CSRFToken', csrfToken);
  }
  if (body !== undefined) requestHeaders.set('Content-Type', 'application/json');
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: upperMethod,
      credentials: 'include',
      headers: requestHeaders,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (cause) {
    throw new ApiNetworkError(cause);
  }
  try {
    return await parseResponse(response);
  } catch (error) {
    if (error instanceof ApiError && error.status === 403 && error.code === 'csrf_failed') {
      dispatchBrowserEvent(CSRF_FAILURE_EVENT);
      if (UNSAFE_METHODS.has(upperMethod) && !csrfRetry) {
        await bootstrapCsrf();
        return send(path, options, true);
      }
    }
    if (error instanceof ApiError && error.status === 401 && path !== '/auth/login/') {
      dispatchBrowserEvent(SESSION_EXPIRED_EVENT);
    }
    throw error;
  }
}

export async function bootstrapCsrf() {
  let response;
  try {
    response = await fetch(`${API_BASE}/auth/csrf/`, { credentials: 'include' });
  } catch (cause) {
    throw new ApiNetworkError(cause);
  }
  const payload = await parseResponse(response);
  csrfToken = payload?.data?.csrf_token || null;
  if (!csrfToken) throw new Error('The server did not return a CSRF token.');
  return csrfToken;
}

export async function apiRequest(path, options) {
  return send(path, options);
}

export async function loginRequest(identifier, password) {
  await bootstrapCsrf();
  const payload = await send('/auth/login/', { method: 'POST', body: { identifier, password } });
  csrfToken = payload?.meta?.csrf_token || csrfToken;
  return payload?.data?.user;
}

export async function logoutRequest() {
  await send('/auth/logout/', { method: 'POST', body: {} });
  csrfToken = null;
}

export function clearCsrfToken() {
  csrfToken = null;
}

export function errorMessage(error) {
  if (error instanceof ApiNetworkError) return error.message;
  if (error instanceof ApiError) {
    const detail = Object.values(error.details || {}).flat().filter(Boolean)[0];
    return detail ? `${error.message} ${detail}` : error.message;
  }
  return error?.message || 'The request could not be completed.';
}

export const apiClientEvents = {
  csrfFailure: CSRF_FAILURE_EVENT,
  sessionExpired: SESSION_EXPIRED_EVENT,
};
