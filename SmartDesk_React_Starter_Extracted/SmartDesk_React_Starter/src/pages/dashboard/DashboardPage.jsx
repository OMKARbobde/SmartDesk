import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, AlertTriangle, CheckCircle2, Clock, Sparkles, ArrowRight } from 'lucide-react';
import { AppShell } from '../../components/layout/AppShell';
import { ApiState } from '../../components/ui/ApiState';
import { KpiCard } from '../../components/ui/KpiCard';
import { PrimaryButton } from '../../components/ui/PrimaryButton';
import { ticketApi } from '../../api/resources';

export function DashboardPage() {
  const navigate = useNavigate();
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const load = async () => {
    setLoading(true); setError('');
    try { setTickets(await ticketApi.listAll()); }
    catch (requestError) { setError(requestError.message || 'Could not load tickets.'); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const counts = useMemo(() => ({
    open: tickets.filter((ticket) => ticket.raw.status === 'OPEN').length,
    progress: tickets.filter((ticket) => ticket.raw.status === 'IN_PROGRESS').length,
    resolved: tickets.filter((ticket) => ticket.raw.status === 'RESOLVED').length,
    critical: tickets.filter((ticket) => ticket.raw.priority === 'CRITICAL').length,
  }), [tickets]);
  const demand = useMemo(() => {
    const groups = new Map();
    tickets.forEach((ticket) => {
      if (!ticket.departmentId) return;
      const row = groups.get(ticket.departmentId) || { id: ticket.departmentId, dept: ticket.dept, count: 0 };
      if (['OPEN', 'IN_PROGRESS'].includes(ticket.raw.status)) row.count += 1;
      groups.set(ticket.departmentId, row);
    });
    return [...groups.values()].sort((a, b) => a.dept.localeCompare(b.dept));
  }, [tickets]);
  return <AppShell title="Executive Operations Center" breadcrumb="Platform > Service Management > Overview">
    <div className="mb-4 rounded-lg border border-purple-800/50 bg-purple-950/20 p-4 sm:flex sm:items-center sm:justify-between">
      <div className="flex items-center gap-3"><div className="flex h-9 w-9 items-center justify-center rounded-lg border border-purple-700 bg-purple-900/60 text-purple-300"><Sparkles className="h-5 w-5" /></div><div><div className="flex flex-wrap items-center gap-2"><span className="text-sm font-semibold text-white">AI ticket analysis</span><span className="rounded border border-amber-600/50 bg-amber-900/20 px-2 py-0.5 text-[10px] font-mono text-amber-300">Telemetry unavailable</span></div><p className="mt-0.5 text-xs text-slate-400">Live telemetry and anomaly detection are not connected.</p></div></div>
      <PrimaryButton variant="ai" size="sm" className="mt-3 sm:mt-0" onClick={() => navigate('/ai-analysis')}>Open AI analysis <ArrowRight className="ml-1 h-3.5 w-3.5" /></PrimaryButton>
    </div>
    <ApiState loading={loading} error={error} onRetry={load}>
      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-5">
        <KpiCard onClick={() => navigate('/tickets')} title="Total Visible Tickets" value={tickets.length} delta="View tickets" subtext="Tickets visible to your account" icon={Activity} />
        <KpiCard onClick={() => navigate('/tickets?status=OPEN')} title="Open Tickets" value={counts.open} delta="Needs attention" subtext="Across visible departments" icon={Clock} isNegativeDelta />
        <KpiCard onClick={() => navigate('/tickets?status=IN_PROGRESS')} title="In Progress" value={counts.progress} delta="Active queue" subtext="Visible active tickets" icon={Activity} />
        <KpiCard onClick={() => navigate('/tickets?status=RESOLVED')} title="Resolved" value={counts.resolved} delta="Ticket status" subtext="No SLA metric available" icon={CheckCircle2} />
        <KpiCard onClick={() => navigate('/tickets?priority=CRITICAL')} title="Critical Incidents" value={counts.critical} delta="Review critical" subtext="Visible critical tickets" icon={AlertTriangle} isNegativeDelta />
      </div>
      <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-lg border border-[#1e2638] bg-[#181c24] p-5 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between"><div><h3 className="text-sm font-semibold text-white">Ticket Volume & Resolution Velocity</h3><p className="text-xs text-slate-400">Daily time-series data is not exposed by the current API.</p></div><span className="text-xs font-medium text-amber-300">Unavailable</span></div>
          <div className="grid h-48 place-items-center rounded border border-dashed border-[#273247] text-center"><div><p className="text-sm text-slate-300">No time-series data available</p><p className="mt-1 text-xs text-slate-500">This chart will appear when the backend provides daily ticket history.</p></div></div>
          <div className="mt-4 border-t border-[#1e2638] pt-3 text-xs text-slate-500">No illustrative or sample values are displayed.</div>
        </div>
        <div className="rounded-lg border border-[#1e2638] bg-[#181c24] p-5"><h3 className="mb-1 text-sm font-semibold text-white">Department Workload</h3><p className="mb-4 text-xs text-slate-400">Open and in-progress visible tickets</p>{demand.length ? <div className="space-y-3">{demand.map((item) => <button key={item.id} onClick={() => navigate(`/tickets?department=${item.id}&status=OPEN,IN_PROGRESS`)} className="block w-full text-left hover:opacity-80"><div className="mb-1 flex justify-between text-xs"><span className="text-slate-300">{item.dept}</span><span className="text-slate-400">{item.count} active</span></div><div className="h-1.5 w-full overflow-hidden rounded-full bg-[#0f131c]"><div className="h-full bg-blue-500" style={{ width: `${Math.min(100, Math.round(item.count / Math.max(...demand.map((entry) => entry.count), 1) * 100))}%` }} /></div></button>)}</div> : <p className="text-xs text-slate-500">No visible tickets are associated with a department.</p>}</div>
      </div>
    </ApiState>
  </AppShell>;
}
