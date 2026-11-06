import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { CheckCircle2, Cpu, Play, RotateCw, Sparkles } from 'lucide-react';
import { AppShell } from '../../components/layout/AppShell';
import { ApiState } from '../../components/ui/ApiState';
import { KpiCard } from '../../components/ui/KpiCard';
import { PrimaryButton } from '../../components/ui/PrimaryButton';
import { adaptAnalysis } from '../../api/adapters';
import { errorMessage } from '../../api/client';
import { aiApi, ticketApi } from '../../api/resources';

export function AIAnalysisPage() {
  const [searchParams] = useSearchParams();
  const [tickets, setTickets] = useState([]);
  const [ticketPk, setTicketPk] = useState(searchParams.get('ticket') || '');
  const [loadingTickets, setLoadingTickets] = useState(true);
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState('');
  const [loadError, setLoadError] = useState('');

  const loadTickets = async () => {
    setLoadingTickets(true); setLoadError('');
    try {
      const rows = await ticketApi.listAll();
      setTickets(rows);
      setTicketPk((current) => rows.some((ticket) => String(ticket.pk) === String(current)) ? String(current) : String(rows[0]?.pk || ''));
    } catch (requestError) { setLoadError(errorMessage(requestError)); }
    finally { setLoadingTickets(false); }
  };
  useEffect(() => { loadTickets(); }, []);

  const selected = tickets.find((ticket) => String(ticket.pk) === String(ticketPk));
  const runAnalysis = async () => {
    if (!selected) return;
    setLoading(true); setError(''); setAnalysis(null);
    try { setAnalysis(adaptAnalysis(await aiApi.analyze(selected.pk))); }
    catch (requestError) { setError(errorMessage(requestError)); }
    finally { setLoading(false); }
  };

  return <AppShell title="AI Ticket Analysis & Predictive Triage" breadcrumb="Platform > Service Management > AI Analysis">
    <div className="mb-4 rounded-lg border border-purple-800/50 bg-purple-950/20 p-3 text-xs text-purple-200"><Sparkles className="mr-2 inline h-4 w-4" />Connected to SmartDesk's deterministic ticket-analysis service. External AI inference, telemetry, and runbook execution are not connected.</div>
    <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-4"><KpiCard title="Weekly Automated Triage" value="Demo" delta="Unavailable" subtext="No aggregate analytics API" icon={Cpu} /><KpiCard title="Triage Latency Avg" value="Demo" delta="Unavailable" subtext="Not measured by backend" icon={Sparkles} /><KpiCard title="FCR Resolution Lift" value="Demo" delta="Unavailable" subtext="Not measured by backend" icon={CheckCircle2} /><KpiCard title="Routing Precision" value="Demo" delta="Unavailable" subtext="Not measured by backend" icon={CheckCircle2} /></div>
    <ApiState loading={loadingTickets} error={loadError} onRetry={loadTickets}>
      {tickets.length === 0 ? <p className="rounded-lg border border-[#1e2638] bg-[#181c24] p-5 text-sm text-slate-400">No visible tickets are available for analysis.</p> : <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section className="rounded-lg border border-[#1e2638] bg-[#181c24] p-5">
          <label className="mb-2 block text-sm font-semibold text-white">Ticket to analyze<select aria-label="Ticket to analyze" value={ticketPk} onChange={(event) => { setTicketPk(event.target.value); setAnalysis(null); setError(''); }} className="mt-2 block w-full rounded-lg border border-[#1e2638] bg-[#0a0e16] p-2 text-sm text-white">{tickets.map((ticket) => <option key={ticket.pk} value={ticket.pk}>{ticket.id} — {ticket.title}</option>)}</select></label>
          <div className="mb-4 h-48 overflow-y-auto rounded border border-[#1e2638] bg-[#0a0e16] p-3 font-mono text-xs text-slate-300"><p className="text-slate-500">Ticket {selected?.id || ''} • {selected?.dept || 'No department'}</p><p className="mt-3 whitespace-pre-wrap">{selected?.description || 'No description provided.'}</p></div>
          <PrimaryButton variant="ai" icon={loading ? RotateCw : Sparkles} size="sm" disabled={loading || !selected} onClick={runAnalysis}>{loading ? 'Analyzing ticket…' : 'Analyze ticket'}</PrimaryButton>
          {error && <p role="alert" className="mt-3 text-xs text-rose-300">{error}</p>}
          {analysis && <div role="status" className="mt-4 rounded border border-emerald-800/60 bg-emerald-950/20 p-3 text-xs text-emerald-200"><strong>Analysis saved • {analysis.analyzedAt}</strong><p className="mt-2">Suggested response: {analysis.suggested_response || '—'}</p></div>}
        </section>
        <section className="rounded-lg border border-[#1e2638] bg-[#181c24] p-5">
          <div className="mb-4 flex items-center justify-between"><h3 className="text-sm font-semibold text-white">Ticket Analysis Result</h3><span className="rounded border border-purple-500/30 bg-purple-500/10 px-2 py-0.5 text-xs text-purple-300">Persisted service result</span></div>
          <div className="space-y-4">
            <div className="rounded border border-[#1e2638] bg-[#0f131c] p-3"><span className="text-xs text-slate-400">Predicted priority</span><div className="text-2xl font-bold text-white">{analysis?.priorityLabel || 'Run analysis'}</div></div>
            <div className="rounded border border-[#1e2638] bg-[#0f131c] p-3"><span className="text-xs text-slate-400">Predicted category</span><div className="text-sm font-medium text-white">{analysis?.predicted_category || '—'}</div></div>
            <div className="rounded border border-[#1e2638] bg-[#0f131c] p-3"><span className="text-xs text-slate-400">Sentiment</span><div className="text-sm font-medium text-white">{analysis?.sentimentLabel || '—'}</div></div>
            <div className="rounded border border-[#1e2638] bg-[#0f131c] p-3"><span className="text-xs text-slate-400">Heuristic confidence score</span><div className="text-sm font-medium text-white">{analysis ? `${(Number(analysis.confidence_score) * 100).toFixed(0)}%` : '—'}</div></div>
            <div className="rounded border border-amber-800/50 bg-amber-950/20 p-3 text-xs text-amber-200">Runbook dispatch is unavailable because no automation endpoint is connected.</div>
            <PrimaryButton icon={Play} className="w-full" disabled title="No runbook dispatch API is available">Runbook dispatch unavailable</PrimaryButton>
          </div>
        </section>
      </div>}
    </ApiState>
  </AppShell>;
}
