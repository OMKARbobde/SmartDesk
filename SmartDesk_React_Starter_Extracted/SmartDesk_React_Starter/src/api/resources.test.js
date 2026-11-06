import test from 'node:test';
import assert from 'node:assert/strict';
import { ApiError } from './client.js';
import { auditApi } from './resources.js';

function jsonResponse(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: () => 'application/json' },
    json: async () => body,
  };
}

test('audit API requests the authenticated endpoint with filters and unwraps data/meta', async () => {
  const originalFetch = globalThis.fetch;
  let requestUrl;
  let requestOptions;
  globalThis.fetch = async (url, options) => {
    requestUrl = url;
    requestOptions = options;
    return jsonResponse({
      data: [{ id: 7, event_type: 'TICKET_CREATED' }],
      meta: { pagination: { count: 1, page: 2, page_size: 20, total_pages: 2, next: null, previous: 1 } },
    });
  };

  try {
    const result = await auditApi.list({
      event_type: 'TICKET_CREATED', actor: 12, ticket: 44,
      created_after: '2026-11-01T00:00:00Z', created_before: '2026-11-06T00:00:00Z',
      page: 2, page_size: 20,
    });
    const url = new URL(requestUrl);
    assert.equal(url.pathname, '/api/audit-logs/');
    assert.equal(url.searchParams.get('event_type'), 'TICKET_CREATED');
    assert.equal(url.searchParams.get('actor'), '12');
    assert.equal(url.searchParams.get('ticket'), '44');
    assert.equal(url.searchParams.get('created_after'), '2026-11-01T00:00:00Z');
    assert.equal(url.searchParams.get('created_before'), '2026-11-06T00:00:00Z');
    assert.equal(url.searchParams.get('page'), '2');
    assert.equal(url.searchParams.get('page_size'), '20');
    assert.equal(requestOptions.method, 'GET');
    assert.equal(requestOptions.credentials, 'include');
    assert.deepEqual(result, {
      items: [{ id: 7, event_type: 'TICKET_CREATED' }],
      pagination: { count: 1, page: 2, page_size: 20, total_pages: 2, next: null, previous: 1 },
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('audit API preserves standardized authorization errors', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => jsonResponse({
    error: { code: 'permission_denied', message: 'You do not have permission.', details: {} },
  }, 403);
  try {
    await assert.rejects(auditApi.list(), (error) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.status, 403);
      assert.equal(error.code, 'permission_denied');
      return true;
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});
