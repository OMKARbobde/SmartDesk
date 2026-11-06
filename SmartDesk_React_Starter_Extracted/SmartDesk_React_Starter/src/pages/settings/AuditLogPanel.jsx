import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle, ChevronLeft, ChevronRight, RotateCcw } from 'lucide-react';
import { auditApi } from '../../api/resources';
import { ApiError, errorMessage } from '../../api/client';

const DEFAULT_PAGE_SIZE = 20;
const EVENT_LABELS = {
  TICKET_CREATED: 'Ticket created',
  TICKET_UPDATED: 'Ticket updated',
  TICKET_STATUS_CHANGED: 'Ticket status changed',
  TICKET_PRIORITY_CHANGED: 'Ticket priority changed',
  TICKET_BULK_STATUS_CHANGED: 'Bulk status change',
  TICKET_BULK_PRIORITY_CHANGED: 'Bulk priority change',
  ASSIGNMENT_CREATED: 'Assignment created',
  ASSIGNMENT_REASSIGNED: 'Assignment reassigned',
  ASSIGNMENT_ACCEPTED: 'Assignment accepted',
  ASSIGNMENT_COMPLETED: 'Assignment completed',
  TICKET_ARCHIVED: 'Ticket archived',
  TICKET_RESTORED: 'Ticket restored',
};

const EVENT_OPTIONS = Object.entries(EVENT_LABELS);
const INPUT_CLASS = 'mt-1 w-full rounded border border-[#1e2638] bg-[#0f131c] px-3 py-2 text-xs text-white placeholder:text-slate-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500';

function formatDateTime(value) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString();
}

function describeDetails(event) {
  const { details = {}, target_user: targetUser } = event;
  if (Array.isArray(details.changed_fields)) {
    const names = details.changed_fields.map((field) => field.replaceAll('_', ' '));
    const department = details.changes?.department_id;
    return department
      ? `${names.join(', ')} · department ${department.from ?? 'none'} → ${department.to ?? 'none'}`
      : names.join(', ');
  }
  if ('from' in details && 'to' in details) return `${details.from} → ${details.to}`;
  if (details.assignment_status) return `${details.assignment_status} · ${targetUser?.display_name || 'Assignee unavailable'}`;
  if (details.assigned_to_profile_id) return `Assigned to ${targetUser?.display_name || 'employee'} · profile #${details.assigned_to_profile_id}`;
  if (details.previous_assignee_user_id) return `Reassigned from user #${details.previous_assignee_user_id} to ${targetUser?.display_name || 'new assignee'}`;
  if (details.status || details.priority) return [details.status, details.priority].filter(Boolean).join(' · ');
  return '—';
}

function toApiFilters(filters, page, pageSize) {
  const result = { page, page_size: pageSize };
  if (filters.event_type) result.event_type = filters.event_type;
  if (filters.actor.trim()) result.actor = filters.actor.trim();
  if (filters.ticket.trim()) result.ticket = filters.ticket.trim();
  if (filters.created_after) result.created_after = new Date(filters.created_after).toISOString();
  if (filters.created_before) result.created_before = new Date(filters.created_before).toISOString();
  return result;
}

export function AuditLogPanel() {
  const [filters, setFilters] = useState({ event_type: '', actor: '', ticket: '', created_after: '', created_before: '' });
  const [appliedFilters, setAppliedFilters] = useState(filters);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [items, setItems] = useState([]);
  const [pagination, setPagination] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const requestId = useRef(0);

  const query = useMemo(() => toApiFilters(appliedFilters, page, pageSize), [appliedFilters, page, pageSize]);
  const load = useCallback(async () => {
    const currentRequest = ++requestId.current;
    setLoading(true);
    setError(null);
    try {
      const result = await auditApi.list(query);
      if (currentRequest !== requestId.current) return;
      setItems(result.items);
      setPagination(result.pagination || null);
    } catch (requestError) {
      if (currentRequest !== requestId.current) return;
      setItems([]);
      setPagination(null);
      setError(requestError);
    } finally {
      if (currentRequest === requestId.current) setLoading(false);
    }
  }, [query]);

  useEffect(() => {
    load();
    return () => { requestId.current += 1; };
  }, [load]);

  const applyFilters = (event) => {
    event.preventDefault();
    setPage(1);
    setAppliedFilters({ ...filters });
  };
  const resetFilters = () => {
    const cleared = { event_type: '', actor: '', ticket: '', created_after: '', created_before: '' };
    setFilters(cleared);
    setAppliedFilters(cleared);
    setPage(1);
  };
  const updateFilter = (name) => (event) => setFilters((current) => ({ ...current, [name]: event.target.value }));
  const unauthorized = error instanceof ApiError && error.status === 403;

  return <section aria-labelledby="audit-log-title" className="rounded-lg border border-[#1e2638] bg-[#181c24] p-5">
    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div><h3 id="audit-log-title" className="text-sm font-semibold text-white">Audit log</h3><p className="mt-1 text-xs text-slate-400">Live, read-only activity records. Times use your browser’s local timezone.</p></div>
      <span className="rounded border border-[#1e2638] bg-[#0f131c] px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-blue-300">Admin only</span>
    </div>

    <form onSubmit={applyFilters} className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
      <label className="text-[11px] text-slate-400">Event type<select aria-label="Filter by event type" value={filters.event_type} onChange={updateFilter('event_type')} className={INPUT_CLASS}><option value="">All event types</option>{EVENT_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      <label className="text-[11px] text-slate-400">Actor user ID<input aria-label="Filter by actor user ID" inputMode="numeric" pattern="[0-9]*" value={filters.actor} onChange={updateFilter('actor')} className={INPUT_CLASS} placeholder="Any actor" /></label>
      <label className="text-[11px] text-slate-400">Ticket database ID<input aria-label="Filter by ticket database ID" inputMode="numeric" pattern="[0-9]*" value={filters.ticket} onChange={updateFilter('ticket')} className={INPUT_CLASS} placeholder="Any ticket" /></label>
      <label className="text-[11px] text-slate-400">Created after<input aria-label="Created after" type="datetime-local" value={filters.created_after} onChange={updateFilter('created_after')} className={INPUT_CLASS} /></label>
      <label className="text-[11px] text-slate-400">Created before<input aria-label="Created before" type="datetime-local" value={filters.created_before} onChange={updateFilter('created_before')} className={INPUT_CLASS} /></label>
      <div className="flex flex-wrap items-end gap-2 sm:col-span-2 xl:col-span-5">
        <button type="submit" disabled={loading} className="rounded bg-blue-600 px-3 py-2 text-xs font-medium text-white hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-400 disabled:opacity-50">Apply filters</button>
        <button type="button" onClick={resetFilters} className="inline-flex items-center gap-1 rounded border border-[#30394a] px-3 py-2 text-xs text-slate-300 hover:bg-[#202634] focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500"><RotateCcw className="h-3.5 w-3.5" />Reset</button>
        <label className="ml-auto flex items-center gap-2 text-xs text-slate-400">Rows<select aria-label="Audit log page size" value={pageSize} onChange={(event) => { setPageSize(Number(event.target.value)); setPage(1); }} className="rounded border border-[#1e2638] bg-[#0f131c] px-2 py-2 text-xs text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500"><option value="20">20 per page</option><option value="50">50 per page</option><option value="100">100 per page</option></select></label>
      </div>
    </form>

    {error ? <div role="alert" className="rounded-lg border border-rose-800/60 bg-rose-950/20 p-4 text-sm text-rose-200"><div className="flex items-start gap-2"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /><div><p className="font-medium">{unauthorized ? 'Audit logs are restricted to administrators.' : 'Audit logs could not be loaded.'}</p><p className="mt-1 text-xs text-rose-200/80">{unauthorized ? 'Your account does not have permission to view these records.' : errorMessage(error)}</p>{!unauthorized && <button type="button" onClick={load} className="mt-3 rounded border border-rose-700 px-3 py-1.5 text-xs hover:bg-rose-900/40">Retry</button>}</div></div></div>
      : <>
        {loading && <div role="status" className="mb-3 rounded-lg border border-[#1e2638] bg-[#0f131c] p-3 text-xs text-slate-400">Loading audit events…</div>}
        <div className="overflow-x-auto rounded border border-[#1e2638]">
          <table className="w-full min-w-[720px] text-left text-xs">
            <thead className="bg-[#0f131c] text-[10px] uppercase tracking-wide text-slate-500"><tr><th scope="col" className="px-3 py-2.5">Action</th><th scope="col" className="px-3 py-2.5">Actor</th><th scope="col" className="px-3 py-2.5">Ticket</th><th scope="col" className="px-3 py-2.5">Date and time</th><th scope="col" className="px-3 py-2.5">Details</th></tr></thead>
            <tbody className="divide-y divide-[#1e2638]">
              {items.map((item) => <tr key={item.id} className="text-slate-300"><td className="px-3 py-3 font-medium text-slate-100">{EVENT_LABELS[item.event_type] || item.event_type}</td><td className="px-3 py-3">{item.actor?.display_name || (item.actor?.id ? `User #${item.actor.id}` : 'Deleted user')}</td><td className="px-3 py-3 font-mono text-blue-300">{item.ticket?.ticket_id || '—'}</td><td className="px-3 py-3 whitespace-nowrap text-slate-400">{formatDateTime(item.created_at)}</td><td className="max-w-[320px] px-3 py-3 text-slate-400">{describeDetails(item)}</td></tr>)}
              {!loading && items.length === 0 && <tr><td colSpan="5" className="px-3 py-8 text-center text-slate-500">No audit events match these filters.</td></tr>}
            </tbody>
          </table>
        </div>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400"><p>{pagination ? `${pagination.count} events · page ${pagination.page} of ${pagination.total_pages}` : 'No pagination data available'}</p><div className="flex gap-2"><button type="button" aria-label="Previous audit log page" disabled={loading || !pagination?.previous} onClick={() => setPage((current) => Math.max(1, current - 1))} className="inline-flex items-center gap-1 rounded border border-[#30394a] px-2.5 py-1.5 hover:bg-[#202634] focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500 disabled:cursor-not-allowed disabled:opacity-40"><ChevronLeft className="h-3.5 w-3.5" />Previous</button><button type="button" aria-label="Next audit log page" disabled={loading || !pagination?.next} onClick={() => setPage((current) => current + 1)} className="inline-flex items-center gap-1 rounded border border-[#30394a] px-2.5 py-1.5 hover:bg-[#202634] focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500 disabled:cursor-not-allowed disabled:opacity-40">Next<ChevronRight className="h-3.5 w-3.5" /></button></div></div>
      </>}
  </section>;
}
