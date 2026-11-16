import { useEffect, useState } from 'react';
import { Search, Bell, Moon, Sun, UserRound, CheckCheck, Check, LoaderCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { notificationApi } from '../../api/resources';
import { errorMessage } from '../../api/client';

function notificationTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Time unavailable' : date.toLocaleString();
}

export function Header({ title, breadcrumb = "Platform > Service Management", onOpenCommandPalette }) {
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [theme, setTheme] = useState(() => localStorage.getItem('smartdesk.theme') || 'dark');
  const [notice, setNotice] = useState('');
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notificationsLoading, setNotificationsLoading] = useState(false);
  const [notificationsError, setNotificationsError] = useState('');
  const [notificationAction, setNotificationAction] = useState('');
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const isAuthenticated = Boolean(user);
  const signOut = async () => {
    try { await logout(); setProfileOpen(false); navigate('/login'); }
    catch (error) { window.dispatchEvent(new CustomEvent('smartdesk:notice', { detail: error.message || 'Unable to sign out. Check the API connection and retry.' })); }
  };
  const loadNotifications = async () => {
    if (!user) return;
    setNotificationsLoading(true);
    setNotificationsError('');
    try {
      const [result, count] = await Promise.all([
        notificationApi.list({ page: 1, page_size: 10 }),
        notificationApi.unreadCount(),
      ]);
      setNotifications(result.items);
      setUnreadCount(count);
    } catch (error) {
      setNotificationsError(errorMessage(error));
    } finally {
      setNotificationsLoading(false);
    }
  };
  const markNotificationRead = async (notification) => {
    if (notification.is_read || notificationAction) return;
    setNotificationAction(String(notification.id));
    setNotificationsError('');
    try {
      const updated = await notificationApi.markRead(notification.id);
      setNotifications((current) => current.map((item) => item.id === updated.id ? updated : item));
      setUnreadCount((current) => Math.max(0, current - 1));
    } catch (error) {
      setNotificationsError(errorMessage(error));
    } finally {
      setNotificationAction('');
    }
  };
  const markAllNotificationsRead = async () => {
    if (!unreadCount || notificationAction) return;
    setNotificationAction('all');
    setNotificationsError('');
    try {
      await notificationApi.markAllRead();
      setNotifications((current) => current.map((item) => ({ ...item, is_read: true })));
      setUnreadCount(0);
    } catch (error) {
      setNotificationsError(errorMessage(error));
    } finally {
      setNotificationAction('');
    }
  };
  useEffect(() => {
    if (!user) {
      setNotifications([]);
      setUnreadCount(0);
      setNotificationsError('');
      return;
    }
    void loadNotifications();
  }, [user?.id]);
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
        <div className="relative">
          <button aria-label={`Notifications${unreadCount ? `, ${unreadCount} unread` : ''}`} aria-expanded={notificationsOpen} aria-controls="smartdesk-notifications-panel" onClick={() => { const open = !notificationsOpen; setNotificationsOpen(open); if (open) void loadNotifications(); }} className="relative rounded-lg border border-[#1e2638] bg-[#181c24] p-2 text-slate-400 transition-colors hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500">
            <Bell className="h-4 w-4" />
            {unreadCount > 0 && <span aria-label={`${unreadCount} unread notifications`} className="absolute -right-1 -top-1 min-w-4 rounded-full border border-[#0f131c] bg-blue-500 px-1 text-center text-[9px] font-bold leading-4 text-white">{unreadCount > 99 ? '99+' : unreadCount}</span>}
          </button>
          {notificationsOpen && <section id="smartdesk-notifications-panel" role="region" aria-label="Notifications" className="absolute right-0 top-12 z-[60] flex max-h-[min(70vh,34rem)] w-80 max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-lg border border-[#1e2638] bg-[#181c24] shadow-2xl sm:w-96">
            <div className="flex items-center justify-between gap-3 border-b border-[#1e2638] p-4"><div><h2 className="text-sm font-semibold text-white">Notifications</h2><p className="mt-1 text-[11px] text-slate-400">{unreadCount} unread</p></div><button type="button" onClick={markAllNotificationsRead} disabled={!unreadCount || notificationAction !== ''} className="inline-flex items-center gap-1 rounded border border-[#30394a] px-2 py-1.5 text-[10px] text-slate-300 hover:bg-[#202634] focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500 disabled:cursor-not-allowed disabled:opacity-40"><CheckCheck className="h-3 w-3" />Mark all read</button></div>
            {notificationsError && <p role="alert" className="border-b border-rose-900/50 bg-rose-950/20 p-3 text-xs text-rose-200">{notificationsError}<button type="button" onClick={() => void loadNotifications()} className="ml-2 underline">Retry</button></p>}
            <div className="overflow-y-auto">
              {notificationsLoading && notifications.length === 0 && <div role="status" className="flex items-center justify-center gap-2 p-7 text-xs text-slate-400"><LoaderCircle className="h-4 w-4 animate-spin" />Loading notifications…</div>}
              {!notificationsLoading && !notificationsError && notifications.length === 0 && <p className="p-7 text-center text-xs text-slate-500">You’re all caught up.</p>}
              {notifications.map((notification) => <article key={notification.id} className={`border-b border-[#1e2638] p-3 ${notification.is_read ? 'bg-transparent' : 'bg-blue-950/10'}`}>
                <div className="flex items-start gap-2"><span aria-hidden="true" className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${notification.is_read ? 'bg-slate-700' : 'bg-blue-400'}`} /><div className="min-w-0 flex-1"><p className="text-xs font-semibold text-slate-100">{notification.title}</p><p className="mt-1 break-words text-xs leading-relaxed text-slate-400">{notification.message}</p><p className="mt-2 text-[10px] text-slate-500">{notificationTime(notification.created_at)}</p></div>{!notification.is_read && <button type="button" aria-label={`Mark notification as read: ${notification.title}`} title="Mark as read" disabled={notificationAction !== ''} onClick={() => void markNotificationRead(notification)} className="rounded p-1 text-slate-500 hover:bg-[#202634] hover:text-emerald-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500 disabled:opacity-40"><Check className="h-3.5 w-3.5" /></button>}</div>
              </article>)}
            </div>
          </section>}
        </div>

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
