import assert from 'node:assert/strict';
import test from 'node:test';
import { describeDetails, EVENT_LABELS } from './auditLogFormatters.js';

test('department audit events have readable labels and safe details', () => {
  const cases = [
    [{ event_type: 'DEPARTMENT_CREATED', details: { department_id: 17, changed_fields: ['name', 'description'], is_active: true } }, 'Department #17 · name, description · Active'],
    [{ event_type: 'DEPARTMENT_UPDATED', details: { department_id: 17, changed_fields: ['code', 'description'] } }, 'Department #17 · Updated: code, description'],
    [{ event_type: 'DEPARTMENT_ACTIVATED', details: { department_id: 17, from: false, to: true } }, 'Department #17 · Inactive → Active'],
    [{ event_type: 'DEPARTMENT_DEACTIVATED', details: { department_id: 17, from: true, to: false } }, 'Department #17 · Active → Inactive'],
  ];

  for (const [event, expected] of cases) {
    assert.equal(typeof EVENT_LABELS[event.event_type], 'string');
    assert.equal(describeDetails(event), expected);
  }
  assert.doesNotMatch(describeDetails(cases[1][0]), /private description contents/i);
});

test('existing ticket details still render correctly', () => {
  assert.equal(describeDetails({ event_type: 'TICKET_STATUS_CHANGED', details: { from: 'OPEN', to: 'RESOLVED' } }), 'OPEN → RESOLVED');
  assert.equal(describeDetails({ event_type: 'TICKET_UPDATED', details: { changed_fields: ['title'], changes: {} } }), 'title');
  assert.equal(EVENT_LABELS.TICKET_CREATED, 'Ticket created');
});
