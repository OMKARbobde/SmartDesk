import { useEffect, useState } from 'react';
import { Search, Bell, Moon, Sun, UserRound } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export function Header({ title, breadcrumb = "Platform > Service Management", onOpenCommandPalette }) {
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [theme, setTheme] = useState(() => localStorage.getItem('smartdesk.theme') || 'dark');
  const [notice, setNotice] = useState('');
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const isAuthenticated = Boolean(user);
  const signOut = async () => {
    try { await logout(); setProfileOpen(false); navigate('/login'); }
    catch (error) { window.dispatchEvent(new CustomEvent('smartdesk:notice', { detail: error.message || 'Unable to sign out. Check the API connection and retry.' })); }
  };
  useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem('smartdesk.theme', theme); }, [theme]);
  useEffect(() => { const onNotice = (event) => { setNotice(event.detail); window.setTimeout(() => setNotice(''), 4000); }; window.addEventListener('smartdesk:notice', onNotice); return () => window.removeEventListener('smartdesk:notice', onNotice); }, []);
  useEffect(() => { const closeMenus = (event) => { if (event.key === 'Escape') { setNotificationsOpen(false); setProfileOpen(false); } }; window.addEventListener('keydown', closeMenus); return () => window.removeEventListener('keydown', closeMenus); }, []);
  return (
    <header className="h-16 bg-[#0f131c] border-b border-[#1e2638] flex items-center justify-between px-6 sticky top-0 z-20">
      <div className="min-w-0">
        <span className="hidden sm:block truncate text-xs text-slate-400 font-medium">{breadcrumb}</span>
        <h1 className="truncate text-sm sm:text-lg font-bold text-white leading-tight">{title}</h1>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        {/* Search / Command Trigger */}
        <button
          onClick={(event) => { event.currentTarget.focus(); onOpenCommandPalette(); }}
          aria-label="Open global search"
          className="flex h-9 w-9 sm:w-64 items-center justify-center sm:justify-start gap-3 px-2 sm:px-3 py-1.5 rounded-lg bg-[#181c24] border border-[#1e2638] text-xs text-slate-400 hover:text-slate-200 hover:border-slate-700 text-left transition-colors"
        >
          <Search className="w-3.5 h-3.5 text-slate-400" />
          <span className="hidden sm:inline">Search records, incidents...</span>
          <kbd className="hidden sm:inline ml-auto font-mono text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded border border-slate-700">⌘K</kbd>
        </button>

        {/* Kafka live sync indicator */}
        <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-950/30 border border-emerald-800/40 text-[11px] text-emerald-400">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span>Session API</span>
        </div>

        {/* Notifications */}
        <div className="relative"><button aria-label="Notifications" aria-expanded={notificationsOpen} onClick={() => setNotificationsOpen(!notificationsOpen)} className="relative p-2 rounded-lg bg-[#181c24] border border-[#1e2638] text-slate-400 hover:text-white transition-colors">
          <Bell className="w-4 h-4" />
        </button>{notificationsOpen && <div role="region" aria-label="Notifications" className="absolute right-0 top-12 z-50 w-72 rounded-lg border border-[#1e2638] bg-[#181c24] p-4 shadow-xl"><h2 className="text-sm font-semibold text-white">Notifications unavailable</h2><p className="mt-2 text-xs text-slate-400">There is no notifications API connected.</p></div>}</div>

        {/* Theme mode icon */}
        <button aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`} title="Toggle theme" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} className="p-2 rounded-lg bg-[#181c24] border border-[#1e2638] text-slate-400 hover:text-white transition-colors">
          {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>
        <div className="relative"><button aria-label="User menu" aria-expanded={profileOpen} onClick={() => setProfileOpen(!profileOpen)} className="rounded-lg border border-[#1e2638] bg-[#181c24] p-2 text-slate-300 hover:text-white"><UserRound className="h-4 w-4" /></button>{profileOpen && <div className="absolute right-0 top-12 z-50 w-52 rounded-lg border border-[#1e2638] bg-[#181c24] p-3 shadow-xl"><p className="text-xs font-semibold text-white">{user?.display_name || user?.username || 'SmartDesk user'}</p><p className="mb-3 text-[10px] text-slate-400">{user?.role || 'No active session'}</p>{isAuthenticated ? <button onClick={signOut} className="w-full rounded px-2 py-1.5 text-left text-xs text-rose-300 hover:bg-[#202634]">Sign out</button> : <button onClick={() => { setProfileOpen(false); navigate('/login'); }} className="w-full rounded px-2 py-1.5 text-left text-xs text-blue-300 hover:bg-[#202634]">Sign in</button>}</div>}</div>
      </div>
      {notice && <div role="status" className="absolute right-6 top-16 z-50 rounded-lg border border-amber-700 bg-[#181c24] px-4 py-3 text-xs text-amber-200 shadow-xl">{notice}</div>}
      {notificationsOpen && <button className="fixed inset-0 z-10 cursor-default" aria-label="Close notifications" onClick={() => setNotificationsOpen(false)} />}
    </header>
  );
}
