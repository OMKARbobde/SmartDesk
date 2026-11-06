
export function PriorityBadge({ priority }) {
  const p = String(priority || '').toUpperCase();

  const map = {
    'CRITICAL': 'bg-rose-500/15 text-rose-400 border-rose-500/30 font-semibold',
    'HIGH': 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    'MEDIUM': 'bg-blue-500/15 text-blue-400 border-blue-500/30',
    'LOW': 'bg-slate-500/15 text-slate-400 border-slate-500/30'
  };

  const style = map[p] || 'bg-slate-800 text-slate-300 border-slate-700';

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs border ${style}`}>
      {priority}
    </span>
  );
}
