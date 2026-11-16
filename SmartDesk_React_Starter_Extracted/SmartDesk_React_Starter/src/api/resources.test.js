import test from 'node:test';
import assert from 'node:assert/strict';
import { ApiError, clearCsrfToken } from './client.js';
import { auditApi, departmentApi, notificationApi, ticketApi } from './resources.js';

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

test('department list preserves the existing inactive filter contract', async () => {
  const originalFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, options });
    return jsonResponse({ data: [{ id: 4, name: 'Operations', is_active: true }], meta: {} });
  };
  try {
    const active = await departmentApi.list();
    const all = await departmentApi.list({ includeInactive: true });
    assert.deepEqual(active, [{ id: 4, name: 'Operations', is_active: true }]);
    assert.equal(new URL(calls[0].url).pathname, '/api/departments/');
    assert.equal(new URL(calls[0].url).search, '');
    assert.equal(new URL(calls[1].url).searchParams.get('include_inactive'), 'true');
    assert.deepEqual(all, active);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('department create and update use CSRF-protected writes and unwrap data', async () => {
  const originalFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, options });
    if (url.endsWith('/auth/csrf/')) return jsonResponse({ data: { csrf_token: 'csrf-dept' }, meta: {} });
    const data = JSON.parse(options.body);
    return jsonResponse({ data: { id: 8, ...data }, meta: {} }, options.method === 'POST' ? 201 : 200);
  };
  try {
    const created = await departmentApi.create({ name: 'Platform', code: 'PLAT', is_active: true });
    const updated = await departmentApi.update(8, { is_active: false });
    const writes = calls.filter((call) => call.options.method === 'POST' || call.options.method === 'PATCH');
    assert.equal(created.id, 8);
    assert.equal(updated.is_active, false);
    assert.equal(new URL(writes[0].url).pathname, '/api/departments/');
    assert.equal(writes[0].options.method, 'POST');
    assert.equal(new URL(writes[1].url).pathname, '/api/departments/8/');
    assert.equal(writes[1].options.method, 'PATCH');
    for (const { options } of writes) {
      assert.equal(options.credentials, 'include');
      assert.equal(new Headers(options.headers).get('X-CSRFToken'), 'csrf-dept');
    }
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('notification list and unread count use authenticated notification endpoints', async () => {
  const originalFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, options });
    if (url.endsWith('/notifications/unread-count/')) return jsonResponse({ data: { count: 3 }, meta: {} });
    return jsonResponse({ data: [{ id: 9, is_read: false }], meta: { pagination: { count: 1, page: 1, page_size: 10, total_pages: 1 } } });
  };
  try {
    const result = await notificationApi.list({ page: 1, page_size: 10 });
    const unread = await notificationApi.unreadCount();
    assert.equal(new URL(calls[0].url).pathname, '/api/notifications/');
    assert.equal(new URL(calls[0].url).searchParams.get('page_size'), '10');
    assert.equal(result.items[0].id, 9);
    assert.equal(result.pagination.count, 1);
    assert.equal(unread, 3);
    assert.equal(calls[0].options.credentials, 'include');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('ticket archive listing unwraps pagination and archive metadata', async () => {
  const originalFetch = globalThis.fetch;
  let requestUrl;
  globalThis.fetch = async (url) => {
    requestUrl = url;
    return jsonResponse({
      data: [{ id: 9, ticket_id: 'SD-0009', is_archived: true, archived_at: '2026-11-16T10:00:00Z' }],
      meta: { pagination: { count: 1, page: 1, page_size: 20, total_pages: 1, next: null, previous: null } },
    });
  };
  try {
    const result = await ticketApi.listArchived({ page: 1, page_size: 20, search: 'SD-0009' });
    const url = new URL(requestUrl);
    assert.equal(url.pathname, '/api/tickets/archived/');
    assert.equal(url.searchParams.get('search'), 'SD-0009');
    assert.equal(result.items[0].isArchived, true);
    assert.equal(result.items[0].archivedAt, '2026-11-16T10:00:00Z');
    assert.equal(result.pagination.count, 1);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('ticket archive and restore use CSRF-protected endpoints and surface permission errors', async () => {
  const originalFetch = globalThis.fetch;
  const calls = [];
  let mutationCount = 0;
  clearCsrfToken();
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, options });
    if (url.endsWith('/auth/csrf/')) return jsonResponse({ data: { csrf_token: 'csrf-archive' }, meta: {} });
    if (options.method === 'POST') {
      mutationCount += 1;
      if (mutationCount === 3) return jsonResponse({ error: { code: 'permission_denied', message: 'Forbidden.', details: {} } }, 403);
      const archived = url.endsWith('/archive/');
      return jsonResponse({ data: { id: 9, ticket_id: 'SD-0009', is_archived: archived }, meta: {} });
    }
    return jsonResponse({ error: { code: 'permission_denied', message: 'Forbidden.', details: {} } }, 403);
  };
  try {
    assert.equal((await ticketApi.archive(9)).isArchived, true);
    assert.equal((await ticketApi.restore(9)).isArchived, false);
    const writes = calls.filter(({ options }) => options.method === 'POST');
    assert.equal(new URL(writes[0].url).pathname, '/api/tickets/9/archive/');
    assert.equal(new URL(writes[1].url).pathname, '/api/tickets/9/restore/');
    for (const { options } of writes) {
      assert.equal(options.credentials, 'include');
      assert.equal(new Headers(options.headers).get('X-CSRFToken'), 'csrf-archive');
      assert.deepEqual(JSON.parse(options.body), {});
    }
    await assert.rejects(ticketApi.restore(9), (error) => error.status === 403 && error.code === 'permission_denied');
  } finally {
    clearCsrfToken();
    globalThis.fetch = originalFetch;
  }
});

test('notification read actions send CSRF-protected writes and unwrap envelopes', async () => {
  const originalFetch = globalThis.fetch;
  const calls = [];
  clearCsrfToken();
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, options });
    if (url.endsWith('/auth/csrf/')) return jsonResponse({ data: { csrf_token: 'csrf-notifications' }, meta: {} });
    if (url.endsWith('/mark-all-read/')) return jsonResponse({ data: { updated_count: 2 }, meta: {} });
    return jsonResponse({ data: { id: 9, is_read: true }, meta: {} });
  };
  try {
    const one = await notificationApi.markRead(9);
    const all = await notificationApi.markAllRead();
    const writes = calls.filter(({ options }) => options.method === 'POST');
    assert.equal(one.is_read, true);
    assert.equal(all.updated_count, 2);
    assert.equal(new URL(writes[0].url).pathname, '/api/notifications/9/read/');
    assert.equal(new URL(writes[1].url).pathname, '/api/notifications/mark-all-read/');
    for (const { options } of writes) {
      assert.equal(options.credentials, 'include');
      assert.equal(new Headers(options.headers).get('X-CSRFToken'), 'csrf-notifications');
    }
  } finally {
    clearCsrfToken();
    globalThis.fetch = originalFetch;
  }
});
