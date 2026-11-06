import assert from 'node:assert/strict';
import { afterEach, beforeEach, test } from 'node:test';
import {
  ApiError,
  ApiNetworkError,
  apiClientEvents,
  apiRequest,
  clearCsrfToken,
  errorMessage,
  loginRequest,
  logoutRequest,
} from './client.js';

const originalFetch = globalThis.fetch;
const originalWindow = globalThis.window;

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

beforeEach(() => clearCsrfToken());

afterEach(() => {
  globalThis.fetch = originalFetch;
  if (originalWindow === undefined) delete globalThis.window;
  else globalThis.window = originalWindow;
  clearCsrfToken();
});

test('session login bootstraps CSRF, uses credentials, and retains the rotated token', async () => {
  const calls = [];
  const user = { id: 7, username: 'demo-agent', role: 'AGENT' };
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, options });
    if (url.endsWith('/auth/csrf/')) return jsonResponse({ data: { csrf_token: 'csrf-before-login' }, meta: {} });
    if (url.endsWith('/auth/login/')) {
      assert.equal(options.credentials, 'include');
      assert.equal(new Headers(options.headers).get('X-CSRFToken'), 'csrf-before-login');
      return jsonResponse({ data: { user }, meta: { csrf_token: 'csrf-after-login' } });
    }
    if (url.endsWith('/auth/me/')) {
      assert.equal(options.credentials, 'include');
      return jsonResponse({ data: { user }, meta: {} });
    }
    if (url.endsWith('/auth/logout/')) {
      assert.equal(new Headers(options.headers).get('X-CSRFToken'), 'csrf-after-login');
      return new Response(null, { status: 204 });
    }
    throw new Error(`Unexpected request: ${url}`);
  };

  assert.deepEqual(await loginRequest('demo-agent', 'secret'), user);
  // A refresh rechecks the server session instead of reading a local user cache.
  assert.deepEqual((await apiRequest('/auth/me/')).data.user, user);
  await logoutRequest();
  assert.equal(calls.filter(({ url }) => url.endsWith('/auth/csrf/')).length, 1);
  assert.equal(calls.filter(({ url }) => url.endsWith('/auth/me/')).length, 1);
});

test('a CSRF failure refreshes the token and retries one unsafe request once', async () => {
  const tokens = [];
  let bootstrapCount = 0;
  globalThis.fetch = async (url, options = {}) => {
    if (url.endsWith('/auth/csrf/')) {
      bootstrapCount += 1;
      return jsonResponse({ data: { csrf_token: `token-${bootstrapCount}` }, meta: {} });
    }
    tokens.push(new Headers(options.headers).get('X-CSRFToken'));
    if (tokens.length === 1) {
      return jsonResponse({ error: { code: 'csrf_failed', message: 'CSRF failed', details: {} } }, 403);
    }
    return jsonResponse({ data: { ok: true }, meta: {} });
  };

  const events = [];
  globalThis.window = { dispatchEvent: (event) => events.push(event.type) };
  assert.deepEqual(await apiRequest('/tickets/', { method: 'POST', body: { title: 'Example' } }), { data: { ok: true }, meta: {} });
  assert.deepEqual(tokens, ['token-1', 'token-2']);
  assert.equal(events.filter((event) => event === apiClientEvents.csrfFailure).length, 1);
});

test('401 API responses raise ApiError and notify the auth context to clear the session', async () => {
  const events = [];
  globalThis.window = { dispatchEvent: (event) => events.push(event.type) };
  globalThis.fetch = async () => jsonResponse({
    error: { code: 'not_authenticated', message: 'Authentication is required.', details: {} },
  }, 401);

  await assert.rejects(apiRequest('/tickets/'), (error) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.status, 401);
    assert.equal(error.code, 'not_authenticated');
    return true;
  });
  assert.deepEqual(events, [apiClientEvents.sessionExpired]);
});

test('403 and 404 responses preserve the backend permission and not-found envelopes', async () => {
  for (const [status, code] of [[403, 'permission_denied'], [404, 'not_found']]) {
    globalThis.fetch = async () => jsonResponse({
      error: { code, message: `Request rejected (${status}).`, details: {} },
    }, status);
    await assert.rejects(apiRequest('/tickets/999/'), (error) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.status, status);
      assert.equal(error.code, code);
      return true;
    });
  }
});

test('invalid login credentials do not broadcast a session-expired event', async () => {
  const events = [];
  globalThis.window = { dispatchEvent: (event) => events.push(event.type) };
  globalThis.fetch = async (url) => url.endsWith('/auth/csrf/')
    ? jsonResponse({ data: { csrf_token: 'csrf-token' }, meta: {} })
    : jsonResponse({ error: { code: 'authentication_failed', message: 'Invalid credentials.', details: {} } }, 401);

  await assert.rejects(loginRequest('unknown', 'incorrect'), ApiError);
  assert.deepEqual(events, []);
});

test('network failures are surfaced as a safe, actionable message', async () => {
  globalThis.fetch = async () => { throw new TypeError('socket details'); };
  await assert.rejects(apiRequest('/auth/me/'), (error) => {
    assert.ok(error instanceof ApiNetworkError);
    assert.match(errorMessage(error), /could not reach the backend/i);
    assert.doesNotMatch(errorMessage(error), /socket details/i);
    return true;
  });
});
