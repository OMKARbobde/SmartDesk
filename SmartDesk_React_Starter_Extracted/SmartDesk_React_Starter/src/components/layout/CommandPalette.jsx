import { useState, useEffect, useRef } from 'react';
import { Search, Ticket, Users, Sparkles, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export function CommandPalette({ isOpen, onClose }) {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();
  const panelRef = useRef(null);
  const inputRef = useRef(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') { e.stopPropagation(); onCloseRef.current(); return; }
      if (e.key !== 'Tab' || !panelRef.current) return;
      const controls = [...panelRef.current.querySelectorAll('input:not([disabled]), button:not([disabled])')];
      const first = controls[0]; const last = controls[controls.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
    };
    if (!isOpen) return undefined;
    const returnFocus = document.activeElement;
    window.requestAnimationFrame(() => inputRef.current?.focus());
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      if (returnFocus?.isConnected) returnFocus.focus();
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const quickNav = [
    { label: 'Executive Operations Dashboard', path: '/', icon: Ticket },
    { label: 'Incident SD-4092: AWS Route53 Outage', path: '/tickets', icon: Ticket },
    { label: 'Run AI Predictive Incident Triage', path: '/ai-analysis', icon: Sparkles },
    { label: 'Workforce Capacity & Shifts', path: '/workforce', icon: Users },
    { label: 'Department Analytics', path: '/analytics', icon: Ticket },
    { label: 'Settings & RBAC', path: '/settings', icon: Users },
    { label: 'Sign in', path: '/login', icon: Users },
  ];

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-start justify-center pt-24 px-4" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <div ref={panelRef} role="dialog" aria-modal="true" aria-label="Command palette" className="bg-[#181c24] border border-[#1e2638] rounded-xl shadow-2xl w-full max-w-xl overflow-hidden">
        <div className="p-3 border-b border-[#1e2638] flex items-center gap-3">
          <Search className="w-4 h-4 text-slate-400" />
          <input
            ref={inputRef}
            type="text"
            aria-label="Search destinations"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command or jump to screen..."
            className="w-full bg-transparent text-sm text-white placeholder-slate-500 focus:outline-none"
          />
          <button aria-label="Close command palette" onClick={onClose} className="rounded p-1 text-slate-400 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500"><X className="w-4 h-4" /></button>
        </div>
        <div className="p-2 space-y-1">
          <span className="text-[10px] font-semibold text-slate-500 uppercase px-3 py-1">Quick Navigation</span>
          {quickNav.filter((item) => item.label.toLowerCase().includes(query.toLowerCase())).map((item, idx) => {
            const Icon = item.icon;
            return (
              <button
                key={item.path}
                onClick={() => {
                  navigate(item.path);
                  onClose();
                }}
                className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-300 hover:bg-[#202634] hover:text-white text-left transition-colors"
              >
                <Icon className="w-4 h-4 text-blue-400" />
                <span>{item.label}</span>
              </button>
            );
          })}
          {query && quickNav.every((item) => !item.label.toLowerCase().includes(query.toLowerCase())) && <p className="px-3 py-4 text-xs text-slate-500">No matching destinations.</p>}
        </div>
      </div>
    </div>
  );
}
