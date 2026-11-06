
export function StatusBadge({ status }) {
  const norm = String(status || '').toLowerCase().replace(/\s+/g, '-');

  const map = {
    'open': 'bg-blue-500/10 text-blue-400 border-blue-500/30',
    'in-progress': 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    'resolved': 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    'closed': 'bg-slate-500/10 text-slate-400 border-slate-500/30',
    'optimal': 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    'high': 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    'overloaded': 'bg-rose-500/10 text-rose-400 border-rose-500/30',
    'verified': 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    'chained': 'bg-purple-500/10 text-purple-400 border-purple-500/30',
  };

  const badgeStyle = map[norm] || 'bg-slate-800 text-slate-300 border-slate-700';

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${badgeStyle}`}>
      <span className="w-1.5 h-1.5 rounded-full mr-1.5 bg-current opacity-80" />
      {status}
    </span>
  );
}
