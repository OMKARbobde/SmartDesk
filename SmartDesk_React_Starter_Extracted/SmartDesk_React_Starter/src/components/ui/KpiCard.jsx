import { ArrowUpRight, ArrowDownRight } from 'lucide-react';

export function KpiCard({ title, value, delta, subtext, icon: Icon, isNegativeDelta = false, onClick }) {
  return (
    <div role={onClick ? 'button' : undefined} tabIndex={onClick ? 0 : undefined} onClick={onClick} onKeyDown={(event) => { if (onClick && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); onClick(); } }} className={`bg-[#181c24] border border-[#1e2638] rounded-lg p-5 flex flex-col justify-between hover:border-slate-700/70 transition-colors ${onClick ? 'cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500' : ''}`}>
      <div className="flex items-center justify-between text-slate-400 mb-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</span>
        {Icon && (
          <div className="w-8 h-8 rounded-md bg-[#202634] flex items-center justify-center text-slate-300">
            <Icon className="w-4 h-4 text-blue-400" />
          </div>
        )}
      </div>
      <div className="flex items-baseline gap-3 my-1">
        <span className="text-3xl font-extrabold tracking-tight text-white">{value}</span>
        {delta && (
          <span className={`inline-flex items-center text-xs font-semibold ${isNegativeDelta ? 'text-rose-400' : 'text-emerald-400'}`}>
            {isNegativeDelta ? <ArrowDownRight className="w-3.5 h-3.5 mr-0.5" /> : <ArrowUpRight className="w-3.5 h-3.5 mr-0.5" />}
            {delta}
          </span>
        )}
      </div>
      {subtext && <p className="text-xs text-slate-500 mt-1">{subtext}</p>}
    </div>
  );
}
