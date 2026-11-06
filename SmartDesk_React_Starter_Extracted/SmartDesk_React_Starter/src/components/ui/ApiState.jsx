import { useEffect, useState } from 'react';

export function ApiState({ loading, error, onRetry, children }) {
  const [hasLoaded, setHasLoaded] = useState(false);
  useEffect(() => {
    if (!loading && !error) setHasLoaded(true);
  }, [loading, error]);

  if (loading && !hasLoaded) return <div role="status" className="mb-4 rounded-lg border border-[#1e2638] bg-[#181c24] p-4 text-sm text-slate-300">Loading live SmartDesk data…</div>;
  if (error) return <div role="alert" className="mb-4 rounded-lg border border-rose-800/60 bg-rose-950/20 p-4 text-sm text-rose-200"><p>{error}</p>{onRetry && <button type="button" onClick={onRetry} className="mt-3 rounded border border-rose-700 px-3 py-1.5 text-xs hover:bg-rose-900/40">Retry request</button>}</div>;
  return <>
    {loading && <div role="status" className="mb-4 rounded-lg border border-[#1e2638] bg-[#181c24] p-3 text-xs text-slate-400">Refreshing live SmartDesk data…</div>}
    {children || null}
  </>;
}
