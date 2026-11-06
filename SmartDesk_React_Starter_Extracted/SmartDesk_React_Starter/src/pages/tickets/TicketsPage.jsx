import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ChevronLeft, ChevronRight, Download, Plus, Search, Sparkles, Terminal } from 'lucide-react';
import { AppShell } from '../../components/layout/AppShell';
import { ApiState } from '../../components/ui/ApiState';
import { DataTable } from '../../components/ui/DataTable';
import { Drawer } from '../../components/ui/Drawer';
import { PriorityBadge } from '../../components/ui/PriorityBadge';
import { PrimaryButton } from '../../components/ui/PrimaryButton';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { assignmentApi, departmentApi, employeeApi, ticketApi } from '../../api/resources';
import { STATUS_LABELS, STATUS_VALUES } from '../../api/adapters';
import { errorMessage } from '../../api/client';
import { useAuth } from '../../context/AuthContext';

const PRIORITIES = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];
const PAGE_SIZES = [5, 10, 20];

function toIso(date) { return date.toISOString(); }

function csvDownload(rows) {
  const headers = ['Ticket ID', 'Title', 'Department', 'Requester', 'Assignee', 'Priority', 'Status', 'Created'];
  const lines = rows.map((ticket) => [ticket.id, ticket.title, ticket.dept, ticket.requester, ticket.assignee, ticket.priority, ticket.status, ticket.date]);
  const csv = [headers, ...lines].map((row) => row.map((value) => `"${String(value ?? '').replaceAll('"', '""')}"`).join(',')).join('\r\n');
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a'); link.href = url; link.download = 'smartdesk-tickets.csv'; link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function TicketsPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const canManageBulk = ['ADMIN', 'AGENT'].includes(user?.role);
  const initialStatus = searchParams.get('status');
  const initialDepartment = searchParams.get('department') || searchParams.get('dept') || '';
  const [tickets, setTickets] = useState([]);
  const [pagination, setPagination] = useState({ count: 0, total_pages: 0 });
  const [departments, setDepartments] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [departmentError, setDepartmentError] = useState('');
  const [actionError, setActionError] = useState('');
  const [exportMessage, setExportMessage] = useState('');
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailLoaded, setDetailLoaded] = useState(false);
  const detailRequestRef = useRef(0);
  const [selectedIds, setSelectedIds] = useState([]);
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState(STATUS_LABELS[initialStatus] || 'All statuses');
  const [priority, setPriority] = useState(PRIORITIES.includes(searchParams.get('priority')) ? searchParams.get('priority') : 'All priorities');
  const [department, setDepartment] = useState(/^\d+$/.test(initialDepartment) ? initialDepartment : '');
  const [period, setPeriod] = useState('Any time');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [reloadVersion, setReloadVersion] = useState(0);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [draft, setDraft] = useState({ title: '', description: '', departmentId: '', priority: 'MEDIUM' });
  const [edit, setEdit] = useState(null);
  const [assigneeId, setAssigneeId] = useState('');

  const dateFilters = useMemo(() => {
    if (period === 'Any time') return {};
    const now = new Date();
    const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    return period === 'Last 24 hours'
      ? { created_after: toIso(yesterday) }
      : { created_before: toIso(yesterday) };
  }, [period]);
  const statusValue = status === 'All statuses' ? '' : STATUS_VALUES[status];
  const priorityValue = priority === 'All priorities' ? '' : priority;

  useEffect(() => {
    let active = true;
    setLoading(true); setError(''); setSelectedIds([]);
    ticketApi.list({
      page, page_size: pageSize, search: query.trim(), status: statusValue,
      priority: priorityValue, department, ...dateFilters,
    }).then((result) => {
      if (!active) return;
      setTickets(result.items); setPagination(result.pagination || { count: 0, total_pages: 0 });
      if (selectedTicket) {
        const fresh = result.items.find((ticket) => ticket.pk === selectedTicket.pk);
        if (fresh) { setSelectedTicket(fresh); setEdit(fromTicket(fresh)); }
      }
    }).catch((requestError) => { if (active) setError(errorMessage(requestError)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [page, pageSize, query, statusValue, priorityValue, department, dateFilters, reloadVersion]);

  useEffect(() => {
    let active = true;
    departmentApi.list().then((rows) => { if (active) setDepartments(rows); })
      .catch((requestError) => { if (active) setDepartmentError(errorMessage(requestError)); });
    if (canManageBulk) employeeApi.listAll().then((rows) => { if (active) setEmployees(rows.filter((employee) => employee.isAvailable)); })
      .catch((requestError) => { if (active) setActionError(errorMessage(requestError)); });
    return () => { active = false; };
  }, [canManageBulk]);

  function fromTicket(ticket) {
    return { title: ticket.title, description: ticket.description, departmentId: ticket.departmentId == null ? '' : String(ticket.departmentId), priority: ticket.priority, status: ticket.status };
  }

  const pageCount = Math.max(1, pagination.total_pages || 0);
  const selectedPageTickets = tickets.filter((ticket) => selectedIds.includes(ticket.id));

  const openTicket = async (ticket) => {
    const requestId = ++detailRequestRef.current;
    setSelectedTicket(ticket); setEdit(fromTicket(ticket)); setActionError(''); setAssigneeId(''); setDetailLoaded(false); setDetailLoading(true);
    try {
      const latest = await ticketApi.get(ticket.pk);
      if (requestId === detailRequestRef.current) {
        setSelectedTicket(latest); setEdit(fromTicket(latest)); setDetailLoaded(true);
      }
    } catch (requestError) {
      if (requestId === detailRequestRef.current) setActionError(errorMessage(requestError));
    } finally {
      if (requestId === detailRequestRef.current) setDetailLoading(false);
    }
  };
  const refreshList = () => setReloadVersion((version) => version + 1);

  const createTicket = async (event) => {
    event.preventDefault(); setActionError(''); setSaving(true);
    try {
      const body = {
        title: draft.title.trim(), description: draft.description.trim(),
        department_id: draft.departmentId ? Number(draft.departmentId) : null,
        priority: draft.priority,
      };
      await ticketApi.create(body);
      setCreating(false); setDraft({ title: '', description: '', departmentId: '', priority: 'MEDIUM' });
      setPage(1); refreshList();
    } catch (requestError) { setActionError(errorMessage(requestError)); }
    finally { setSaving(false); }
  };

  const saveTicket = async () => {
    if (!selectedTicket || !edit) return;
    setActionError(''); setSaving(true);
    const before = selectedTicket.raw;
    const changes = {};
    if (edit.title !== before.title) changes.title = edit.title;
    if (edit.description !== before.description) changes.description = edit.description;
    if (STATUS_VALUES[edit.status] !== before.status) changes.status = STATUS_VALUES[edit.status];
    if (edit.priority !== before.priority) changes.priority = edit.priority;
    const departmentId = edit.departmentId ? Number(edit.departmentId) : null;
    if (departmentId !== (before.department?.id ?? null)) changes.department_id = departmentId;
    if (!Object.keys(changes).length) { setSaving(false); return; }
    try {
      const updated = await ticketApi.update(selectedTicket.pk, changes, before.updated_at);
      setSelectedTicket(updated); setEdit(fromTicket(updated));
      setTickets((current) => current.map((ticket) => ticket.pk === updated.pk ? updated : ticket));
    } catch (requestError) {
      setActionError(requestError.code === 'conflict' ? 'This ticket changed on the server. Close and reopen it to load the latest version before saving.' : errorMessage(requestError));
    } finally { setSaving(false); }
  };

  const assignTicket = async () => {
    if (!selectedTicket || !assigneeId) return;
    setActionError(''); setAssigning(true);
    try {
      await assignmentApi.create(selectedTicket.pk, Number(assigneeId));
      const latest = await ticketApi.list({ page, page_size: pageSize, search: query.trim(), status: statusValue, priority: priorityValue, department, ...dateFilters });
      setTickets(latest.items); setPagination(latest.pagination);
      const refreshed = latest.items.find((ticket) => ticket.pk === selectedTicket.pk);
      if (refreshed) { setSelectedTicket(refreshed); setEdit(fromTicket(refreshed)); }
      setAssigneeId('');
    } catch (requestError) { setActionError(errorMessage(requestError)); }
    finally { setAssigning(false); }
  };

  const bulkUpdate = async (action, value, target) => {
    if (!value || !selectedPageTickets.length) return;
    setActionError(''); setSaving(true);
    try {
      const updated = await ticketApi.bulk(selectedPageTickets.map((ticket) => ticket.pk), action, value);
      setTickets((current) => current.map((ticket) => updated.find((row) => row.pk === ticket.pk) || ticket));
      setSelectedIds([]);
      if (target) target.value = '';
    } catch (requestError) { setActionError(errorMessage(requestError)); }
    finally { setSaving(false); }
  };

  const exportCsv = async () => {
    setActionError(''); setExportMessage('Preparing export…');
    try {
      const all = await ticketApi.listAll({ search: query.trim(), status: statusValue, priority: priorityValue, department, ...dateFilters });
      csvDownload(all); setExportMessage(`CSV downloaded for ${all.length} matching ticket${all.length === 1 ? '' : 's'}.`);
    } catch (requestError) { setExportMessage(''); setActionError(errorMessage(requestError)); }
  };

  const columns = [
    { header: 'Ticket ID', accessor: 'id', cellClassName: 'font-mono text-xs text-blue-400 font-semibold' },
    { header: 'Title & Context', accessor: 'title', cellClassName: 'font-medium text-white max-w-md' },
    { header: 'Department', accessor: 'dept' }, { header: 'Requester', accessor: 'requester' }, { header: 'Assignee', accessor: 'assignee' },
    { header: 'Priority', render: (row) => <PriorityBadge priority={row.priority} /> },
    { header: 'Status', render: (row) => <StatusBadge status={row.status} /> },
    { header: 'Archive', render: () => <span title="Archive and restore are not connected to this page yet" className="text-xs text-slate-500">Unavailable in this page</span> },
    { header: 'Created', accessor: 'date', cellClassName: 'text-xs text-slate-500' },
  ];

  return <AppShell title="Ticket Management" breadcrumb="Platform > Service Management > Tickets">
    <div className="mb-4 rounded-lg border border-amber-800/50 bg-amber-950/20 p-3 text-xs text-amber-200">Archive and restore endpoints exist in the backend but are not connected to this page yet. This page never permanently deletes tickets.</div>
    <ApiState loading={loading} error={error} onRetry={refreshList}>
      <div className="mb-6 flex flex-col items-center justify-between gap-3 sm:flex-row">
        <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:items-center">
          <div className="relative w-full sm:w-72"><Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><input aria-label="Search tickets" value={query} onChange={(event) => { setPage(1); setQuery(event.target.value); }} placeholder="Filter by ID, incident title..." className="w-full rounded-lg border border-[#1e2638] bg-[#181c24] py-1.5 pl-9 pr-3 text-xs text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none" /></div>
          <select aria-label="Filter ticket status" value={status} onChange={(event) => { setPage(1); setStatus(event.target.value); }} className="rounded-lg border border-[#1e2638] bg-[#181c24] px-3 py-2 text-xs text-slate-300"><option>All statuses</option>{Object.values(STATUS_LABELS).map((value) => <option key={value}>{value}</option>)}</select>
          <select aria-label="Filter ticket priority" value={priority} onChange={(event) => { setPage(1); setPriority(event.target.value); }} className="rounded-lg border border-[#1e2638] bg-[#181c24] px-3 py-2 text-xs text-slate-300"><option>All priorities</option>{PRIORITIES.map((value) => <option key={value}>{value}</option>)}</select>
          <select aria-label="Filter department" value={department} onChange={(event) => { setPage(1); setDepartment(event.target.value); }} className="rounded-lg border border-[#1e2638] bg-[#181c24] px-3 py-2 text-xs text-slate-300"><option value="">All departments</option>{departments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
          <select aria-label="Filter created date" value={period} onChange={(event) => { setPage(1); setPeriod(event.target.value); }} className="rounded-lg border border-[#1e2638] bg-[#181c24] px-3 py-2 text-xs text-slate-300"><option>Any time</option><option>Last 24 hours</option><option>Older</option></select>
        </div>
        <div className="flex flex-wrap gap-2"><PrimaryButton variant="secondary" size="sm" onClick={() => { setQuery(''); setStatus('All statuses'); setPriority('All priorities'); setDepartment(''); setPeriod('Any time'); setPage(1); }}>Clear All</PrimaryButton><PrimaryButton variant="secondary" icon={Download} size="sm" onClick={exportCsv}>Export CSV</PrimaryButton><PrimaryButton icon={Plus} size="sm" onClick={() => { setCreating(true); setActionError(''); }}>Create Ticket</PrimaryButton></div>
      </div>
      {departmentError && <p role="alert" className="mb-3 text-xs text-amber-300">Department filters unavailable: {departmentError}</p>}
      {actionError && <p role="alert" className="mb-3 rounded border border-rose-800/60 bg-rose-950/20 p-3 text-xs text-rose-200">{actionError}</p>}
      {exportMessage && <p role="status" className="mb-3 text-xs text-emerald-300">{exportMessage}</p>}
      <DataTable columns={columns} data={tickets} onRowClick={openTicket} selectedIds={selectedIds}
        onSelectAll={(checked) => setSelectedIds(checked ? tickets.map((ticket) => ticket.id) : [])}
        onSelectRow={(id) => setSelectedIds((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id])} />
      <div className="flex flex-wrap items-center justify-between gap-3 py-4 text-xs text-slate-400"><span>Showing {pagination.count ? (page - 1) * pageSize + 1 : 0}–{Math.min(page * pageSize, pagination.count || 0)} of {pagination.count || 0}</span><div className="flex items-center gap-2"><label>Rows <select value={pageSize} onChange={(event) => { setPageSize(Number(event.target.value)); setPage(1); }} className="rounded border border-[#1e2638] bg-[#181c24] p-1">{PAGE_SIZES.map((size) => <option key={size}>{size}</option>)}</select></label><button aria-label="Previous page" disabled={page <= 1 || loading} onClick={() => setPage((value) => value - 1)} className="disabled:opacity-40"><ChevronLeft className="h-4 w-4" /></button><span>{page} / {pageCount}</span><button aria-label="Next page" disabled={page >= pageCount || loading} onClick={() => setPage((value) => value + 1)} className="disabled:opacity-40"><ChevronRight className="h-4 w-4" /></button></div></div>
      {selectedIds.length > 0 && <div className="my-3 flex flex-wrap items-center gap-3 text-sm text-slate-300"><span>{selectedIds.length} selected</span>{canManageBulk ? <><select aria-label="Bulk status" defaultValue="" disabled={saving} onChange={(event) => bulkUpdate('set_status', event.target.value, event.currentTarget)} className="rounded border border-[#1e2638] bg-[#181c24] p-2"><option value="" disabled>Change status…</option>{Object.entries(STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><select aria-label="Bulk priority" defaultValue="" disabled={saving} onChange={(event) => bulkUpdate('set_priority', event.target.value, event.currentTarget)} className="rounded border border-[#1e2638] bg-[#181c24] p-2"><option value="" disabled>Change priority…</option>{PRIORITIES.map((value) => <option key={value}>{value}</option>)}</select></> : <span className="text-xs text-slate-500">Bulk updates are available to ADMIN and AGENT roles.</span>}<button type="button" disabled aria-label="Bulk assignment unavailable" className="cursor-not-allowed text-xs text-slate-500">Bulk assignment unavailable</button><button type="button" disabled aria-label="Archive unavailable" className="cursor-not-allowed text-xs text-slate-500">Archive unavailable</button><button type="button" className="text-slate-400" onClick={() => setSelectedIds([])}>Clear selection</button></div>}
    </ApiState>

    <Drawer isOpen={Boolean(selectedTicket)} onClose={() => { detailRequestRef.current += 1; setDetailLoading(false); setDetailLoaded(false); setSelectedTicket(null); setEdit(null); setActionError(''); }} title={selectedTicket ? `${selectedTicket.id}: ${selectedTicket.title}` : ''} subtitle="Ticket details and permitted updates">
      {selectedTicket && edit && <fieldset disabled={!detailLoaded || detailLoading} className="min-w-0 space-y-5">
        {detailLoading && <p role="status" className="text-xs text-slate-400">Refreshing ticket details from the server…</p>}
        <p className="text-xs text-slate-500">Requester: {selectedTicket.requester} • Last updated: {selectedTicket.updatedAt ? new Date(selectedTicket.updatedAt).toLocaleString() : '—'}</p>
        <label className="block text-xs text-slate-400">Status<select value={edit.status} onChange={(event) => setEdit({ ...edit, status: event.target.value })} className="mt-1 block w-full rounded border border-[#1e2638] bg-[#181c24] p-2 text-white">{Object.values(STATUS_LABELS).map((value) => <option key={value}>{value}</option>)}</select></label>
        <label className="block text-xs text-slate-400">Title<input value={edit.title} onChange={(event) => setEdit({ ...edit, title: event.target.value })} className="mt-1 block w-full rounded border border-[#1e2638] bg-[#181c24] p-2 text-white" /></label>
        <label className="block text-xs text-slate-400">Description<textarea rows="5" value={edit.description} onChange={(event) => setEdit({ ...edit, description: event.target.value })} className="mt-1 block w-full rounded border border-[#1e2638] bg-[#181c24] p-2 text-white" /></label>
        {user?.role !== 'EMPLOYEE' && <>
          <label className="block text-xs text-slate-400">Department<select value={edit.departmentId} onChange={(event) => setEdit({ ...edit, departmentId: event.target.value })} className="mt-1 block w-full rounded border border-[#1e2638] bg-[#181c24] p-2 text-white"><option value="">No department</option>{departments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <label className="block text-xs text-slate-400">Priority<select value={edit.priority} onChange={(event) => setEdit({ ...edit, priority: event.target.value })} className="mt-1 block w-full rounded border border-[#1e2638] bg-[#181c24] p-2 text-white">{PRIORITIES.map((value) => <option key={value}>{value}</option>)}</select></label>
          <div className="rounded-lg border border-[#1e2638] bg-[#181c24] p-3"><p className="text-xs text-slate-400">Current assignee: <span className="text-slate-200">{selectedTicket.assignee}</span></p><div className="mt-3 flex gap-2"><select aria-label="Reassign ticket" value={assigneeId} onChange={(event) => setAssigneeId(event.target.value)} className="min-w-0 flex-1 rounded border border-[#1e2638] bg-[#0f131c] p-2 text-xs text-white"><option value="">Choose available employee</option>{employees.map((employee) => <option key={employee.id} value={employee.id}>{employee.name} — {employee.dept}</option>)}</select><PrimaryButton size="sm" disabled={!assigneeId || assigning} onClick={assignTicket}>{assigning ? 'Assigning…' : 'Assign'}</PrimaryButton></div></div>
        </>}
        {actionError && <p role="alert" className="rounded border border-rose-800/60 bg-rose-950/20 p-3 text-xs text-rose-200">{actionError}</p>}
        <PrimaryButton disabled={saving} onClick={saveTicket}>{saving ? 'Saving…' : 'Save ticket changes'}</PrimaryButton>
        <div className="rounded-lg border border-purple-800/40 bg-purple-950/20 p-4"><div className="mb-2 flex items-center gap-2 text-xs font-semibold text-purple-300"><Sparkles className="h-4 w-4" />AI analysis</div><p className="mb-3 text-xs text-slate-400">Run the connected ticket analysis service for this ticket.</p><PrimaryButton variant="ai" size="sm" onClick={() => navigate(`/ai-analysis?ticket=${selectedTicket.pk}`)}>Open AI analysis</PrimaryButton></div>
        <div className="space-y-2"><span className="text-xs font-semibold uppercase text-slate-400">Runbook</span><div className="flex items-center justify-between rounded-lg border border-slate-800 bg-black/50 p-3 font-mono text-xs text-slate-500"><span>Runbook dispatch unavailable</span><Terminal className="h-4 w-4" /></div></div>
      </fieldset>}
    </Drawer>
    <Drawer isOpen={creating} onClose={() => { setCreating(false); setActionError(''); }} title="Create Ticket" subtitle="Requester is derived from your signed-in account" width="max-w-lg">
      <form onSubmit={createTicket} className="space-y-4"><label className="block text-sm text-slate-300">Title *<input required maxLength={200} value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} className="mt-1 w-full rounded border border-[#1e2638] bg-[#181c24] p-2 text-white" /></label><label className="block text-sm text-slate-300">Description *<textarea required value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} className="mt-1 w-full rounded border border-[#1e2638] bg-[#181c24] p-2 text-white" /></label><label className="block text-sm text-slate-300">Department<select value={draft.departmentId} onChange={(event) => setDraft({ ...draft, departmentId: event.target.value })} className="mt-1 w-full rounded border border-[#1e2638] bg-[#181c24] p-2 text-white"><option value="">No department</option>{departments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label className="block text-sm text-slate-300">Priority<select value={draft.priority} onChange={(event) => setDraft({ ...draft, priority: event.target.value })} className="mt-1 w-full rounded border border-[#1e2638] bg-[#181c24] p-2 text-white">{PRIORITIES.map((value) => <option key={value}>{value}</option>)}</select></label>{actionError && <p role="alert" className="text-xs text-rose-300">{actionError}</p>}<div className="flex justify-end gap-2"><PrimaryButton type="button" variant="secondary" onClick={() => setCreating(false)}>Cancel</PrimaryButton><PrimaryButton type="submit" disabled={saving}>{saving ? 'Creating…' : 'Create Ticket'}</PrimaryButton></div></form>
    </Drawer>
  </AppShell>;
}
