import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  LayoutDashboard,
  Ticket,
  Sparkles,
  Users,
  BarChart3,
  Settings,
  Layers,
  ShieldCheck,
  MoreVertical
} from 'lucide-react';

const navItems = [
  { section: 'OPERATIONS', items: [
    { label: 'Dashboard', path: '/', icon: LayoutDashboard },
    { label: 'Tickets', path: '/tickets', icon: Ticket },
    { label: 'AI Analysis', path: '/ai-analysis', icon: Sparkles, badge: 'AI', badgeColor: 'bg-purple-900/60 text-purple-300 border border-purple-700' },
  ]},
  { section: 'ENTERPRISE STAFF & METRICS', items: [
    { label: 'Employee Directory', path: '/workforce', icon: Users },
    { label: 'Department Analytics', path: '/analytics', icon: BarChart3 },
  ]},
  { section: 'ADMINISTRATION', items: [
    { label: 'Settings & RBAC', path: '/settings', icon: Settings },
  ]}
];

export function Sidebar() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const isAuthenticated = Boolean(user);
  const signOut = async () => {
    try { await logout(); navigate('/login'); }
    catch (error) { window.dispatchEvent(new CustomEvent('smartdesk:notice', { detail: error.message || 'Unable to sign out. Retry when the API is available.' })); }
  };
  return (
    <aside className="w-full md:w-64 bg-[#0a0e16] border-t md:border-t-0 md:border-r border-[#1e2638] flex md:flex-col h-14 md:h-screen fixed left-0 bottom-0 md:top-0 md:bottom-auto select-none z-30">
      {/* Brand Monogram */}
      <div className="hidden md:flex h-16 items-center justify-between px-5 border-b border-[#1e2638]">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold shadow-md shadow-blue-500/20">
            <Layers className="w-4 h-4" />
          </div>
          <span className="font-bold text-base tracking-tight text-white">SmartDesk</span>
        </div>
        <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-blue-400 border border-slate-700">v4.2</span>
      </div>

      {/* Nav List */}
      <div className="flex-1 overflow-x-auto md:overflow-y-auto md:px-3 md:py-4 md:space-y-6 flex md:block items-center justify-around">
        {navItems.map((group, idx) => (
          <div key={idx} className="contents md:block">
            <div className="hidden md:block px-3 mb-2 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              {group.section}
            </div>
            <nav className="flex md:block md:space-y-1 gap-1">
              {group.items.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    aria-label={item.label}
                    className={({ isActive }) => `
                      flex items-center justify-center md:justify-between px-3 py-2 rounded-lg text-sm font-medium transition-colors
                      ${isActive
                        ? 'bg-[#181c24] text-white border-l-2 border-blue-500'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-[#181c24]/50'}
                    `}
                  >
                    <div className="flex items-center gap-2.5">
                      <Icon className="w-4 h-4" />
                      <span className="hidden md:inline">{item.label}</span>
                    </div>
                    {item.badge && <span className="hidden md:inline">
                      <span className={`text-[11px] font-semibold px-2 py-0.2 rounded-full ${item.badgeColor || 'bg-slate-800 text-slate-300'}`}>
                        {item.badge}
                      </span>
                    </span>}
                  </NavLink>
                );
              })}
            </nav>
          </div>
        ))}
      </div>

      {/* Pinned User Footer */}
      <div className="hidden md:block p-3 border-t border-[#1e2638] bg-[#0f131c]">
        <div className="flex items-center justify-between p-2 rounded-lg bg-[#181c24] border border-[#1e2638]">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-8 h-8 rounded-full bg-blue-700 text-white font-semibold flex items-center justify-center text-xs ring-1 ring-blue-400">
              {(user?.display_name || user?.username || 'U').split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()}
            </div>
            <div className="truncate">
              <div className="text-xs font-medium text-white truncate">{user?.display_name || user?.username}</div>
              <div className="text-[10px] text-slate-400 truncate">{user?.role}</div>
            </div>
          </div>
          <button aria-label={isAuthenticated ? 'Sign out' : 'Sign in'} title={isAuthenticated ? 'Sign out' : 'Sign in'} onClick={isAuthenticated ? signOut : () => navigate('/login')} className="rounded p-1 text-slate-400 hover:text-white"><MoreVertical className="w-4 h-4" /></button>
        </div>
      </div>
    </aside>
  );
}
