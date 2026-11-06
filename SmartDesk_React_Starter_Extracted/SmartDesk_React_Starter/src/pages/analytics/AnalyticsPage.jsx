import { useEffect, useMemo, useState } from 'react';
import { Activity, AlertOctagon, BarChart3, CheckCircle, Clock3, Download } from 'lucide-react';
import { AppShell } from '../../components/layout/AppShell';
import { ApiState } from '../../components/ui/ApiState';
import { DataTable } from '../../components/ui/DataTable';
import { KpiCard } from '../../components/ui/KpiCard';
import { PrimaryButton } from '../../components/ui/PrimaryButton';
import { analyticsApi, departmentApi } from '../../api/resources';
import { errorMessage } from '../../api/client';

const periods = { '7 days': 7, '30 days': 30, '90 days': 90, 'All time': null };
const priorities = [
  { value: 'LOW', label: 'Low', color: '#64748b' },
  { value: 'MEDIUM', label: 'Medium', color: '#3b82f6' },
  { value: 'HIGH', label: 'High', color: '#f59e0b' },
  { value: 'CRITICAL', label: 'Critical', color: '#f43f5e' },
];

function makeCsv(rows, period) {
  const headers = [
    'Department', 'Tickets created', 'Currently open', 'Currently in progress',
    'Currently resolved', 'Currently closed', 'Current workload',
    'Priority low', 'Priority medium', 'Priority high', 'Priority critical',
    'Average resolution time seconds',
  ];
  const body = rows.map((row) => [
    row.departmentName,
    row.total,
    row.statusCounts.OPEN,
    row.statusCounts.IN_PROGRESS,
    row.statusCounts.RESOLVED,
    row.statusCounts.CLOSED,
    row.workload,
    row.priorityCounts.LOW,
    row.priorityCounts.MEDIUM,
    row.priorityCounts.HIGH,
    row.priorityCounts.CRITICAL,
    row.averageResolutionSeconds ?? '',
  ]);
  const csv = [headers, ...body]
    .map((line) => line.map((cell) => `"${String(cell ?? '').replaceAll('"', '""')}"`).join(','))
    .join('\r\n');
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = `smartdesk-department-analytics-${period.replaceAll(' ', '-')}.csv`;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function AnalyticsPage() {
  const [department, setDepartment] = useState('');
  const [period, setPeriod] = useState('30 days');
  const [departments, setDepartments] = useState([]);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [exportMessage, setExportMessage] = useState('');

  const dateRange = useMemo(() => {
    const days = periods[period];
    if (!days) return {};
    const end = new Date();
    const start = new Date(end.getTime() - days * 24 * 60 * 60 * 1000);
    return { created_after: start.toISOString(), created_before: end.toISOString() };
  }, [period]);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const [departmentRows, analytics] = await Promise.all([
        departmentApi.list(),
        analyticsApi.departments({ department, ...dateRange }),
      ]);
      setDepartments(departmentRows);
      setReport(analytics);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [department, dateRange]);

  const rows = useMemo(() => (report?.departments || []).map((item) => ({
    id: item.department?.id ?? 'unassigned',
    departmentName: item.department?.name || 'Unassigned',
    total: item.total_tickets,
    statusCounts: item.status_counts,
    priorityCounts: item.priority_counts,
    workload: item.workload_count,
    averageResolutionSeconds: item.average_resolution_time_seconds,
  })), [report]);
  const summary = report?.summary;
  const maxWorkload = Math.max(1, ...rows.map((row) => row.workload));

  const columns = [
    { header: 'Department', accessor: 'departmentName', cellClassName: 'font-semibold text-white' },
    { header: 'Total tickets', accessor: 'total' },
    { header: 'Open', render: (row) => row.statusCounts.OPEN },
    { header: 'In progress', render: (row) => row.statusCounts.IN_PROGRESS },
    { header: 'Resolved', render: (row) => row.statusCounts.RESOLVED },
    { header: 'Closed', render: (row) => row.statusCounts.CLOSED },
    { header: 'Workload', accessor: 'workload', cellClassName: 'font-semibold text-blue-300' },
    ...priorities.map((priority) => ({
      header: priority.label,
      render: (row) => row.priorityCounts[priority.value],
    })),
  ];

  const exportCsv = () => {
    makeCsv(rows, period);
    setExportMessage(`CSV downloaded for ${rows.length} departments in the selected view.`);
  };

  const resolutionUnavailable = summary?.resolution_time_unavailable_reason
    || 'No reliable resolved_at timestamp is available from the backend.';

  return <AppShell title="Department Performance & Analytics" breadcrumb="Platform > Analytics > Department SLA">
    <div className="mb-4 rounded-lg border border-amber-800/50 bg-amber-950/20 p-3 text-xs text-amber-200">
      Analytics are calculated by Django from visible, non-archived ticket records. Ticket membership uses creation time; status and priority show current values.
    </div>
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div className="flex flex-wrap gap-3">
        <label className="text-xs text-slate-400">Department
          <select aria-label="Filter analytics department" value={department} onChange={(event) => setDepartment(event.target.value)} className="mt-1 block rounded-lg border border-[#1e2638] bg-[#181c24] px-3 py-2 text-sm text-white">
            <option value="">All visible departments</option>
            {departments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </label>
        <label className="text-xs text-slate-400">Date range
          <select aria-label="Filter analytics date range" value={period} onChange={(event) => setPeriod(event.target.value)} className="mt-1 block rounded-lg border border-[#1e2638] bg-[#181c24] px-3 py-2 text-sm text-white">
            {Object.keys(periods).map((item) => <option key={item}>{item}</option>)}
          </select>
        </label>
      </div>
      <PrimaryButton icon={Download} size="sm" onClick={exportCsv} disabled={loading || !report}>Export CSV</PrimaryButton>
    </div>
    {exportMessage && <p role="status" className="mb-3 text-xs text-emerald-300">{exportMessage}</p>}
    <ApiState loading={loading} error={error} onRetry={load}>
      {summary && <>
        <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <KpiCard title="Tickets created" value={summary.total_tickets} subtext={`Visible tickets created during ${period}`} icon={BarChart3} />
          <KpiCard title="Current workload" value={summary.workload_count} subtext="Open + in-progress tickets in the selected window" icon={Activity} />
          <KpiCard title="Currently resolved" value={summary.status_counts.RESOLVED} subtext="Current status; not a resolved-date count" icon={CheckCircle} />
          <KpiCard title="Average resolution time" value={summary.resolution_time_available ? `${summary.average_resolution_time_seconds}s` : 'Unavailable'} subtext="Not inferred from updated_at" icon={Clock3} />
        </div>

        <section className="mb-6 rounded-lg border border-[#1e2638] bg-[#181c24] p-5">
          <h2 className="mb-1 text-sm font-semibold text-white">Current workload by department</h2>
          <p className="mb-4 text-xs text-slate-400">Workload is the current count of open and in-progress tickets created in the selected range.</p>
          {rows.length ? <div className="space-y-4">
            {rows.map((row) => <div key={row.id} className="grid grid-cols-[minmax(100px,1fr)_3fr_auto] items-center gap-3 text-xs">
              <span className="truncate text-slate-300">{row.departmentName}</span>
              <div className="h-3 overflow-hidden rounded-full bg-[#0f131c]" role="img" aria-label={`${row.departmentName}: ${row.workload} current workload tickets`}>
                <div className="h-full rounded-full bg-blue-500" style={{ width: `${row.workload ? Math.max(3, (row.workload / maxWorkload) * 100) : 0}%` }} />
              </div>
              <span className="font-semibold text-blue-300">{row.workload}</span>
            </div>)}
          </div> : <p className="text-xs text-slate-500">No departments or tickets match these filters.</p>}
        </section>

        <section className="mb-4 rounded-lg border border-amber-800/50 bg-amber-950/20 p-3 text-xs text-amber-200">
          <AlertOctagon className="mr-2 inline h-4 w-4" />Average resolution time is unavailable. {resolutionUnavailable}
        </section>
        <DataTable columns={columns} data={rows} />
      </>}
    </ApiState>
  </AppShell>;
}
