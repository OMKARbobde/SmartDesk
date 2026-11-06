import { useState } from 'react';
import { AppShell } from '../../components/layout/AppShell';
import { KpiCard } from '../../components/ui/KpiCard';
import { PrimaryButton } from '../../components/ui/PrimaryButton';
import { ShieldCheck, Key, Lock, Users, Save, Plus, Trash2, RotateCw } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { AuditLogPanel } from './AuditLogPanel';

const resources = ['Ticket Management & Triage', 'AI Predictive Engine Rules', 'Employee Directory & Capacity', 'Tenant Security Keys & KMS'];
const defaultRoles = {
  Admin: Object.fromEntries(resources.map((resource) => [resource, { View: true, Create: true, Edit: true, Delete: true }])),
  Manager: Object.fromEntries(resources.map((resource, index) => [resource, { View: true, Create: index < 2, Edit: index < 3, Delete: false }])),
  Agent: Object.fromEntries(resources.map((resource) => [resource, { View: true, Create: false, Edit: false, Delete: false }])),
};
const read = (key, fallback) => { try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; } };

export function SettingsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'ADMIN';
  const [roles, setRoles] = useState(() => read('smartdesk.settings.roles', defaultRoles));
  const [selectedRole, setSelectedRole] = useState('Manager');
  const [idleTimeout, setIdleTimeout] = useState(() => localStorage.getItem('smartdesk.settings.idle') || '30');
  const [rateLimit, setRateLimit] = useState(() => localStorage.getItem('smartdesk.settings.rate') || '120');
  const [webhooks, setWebhooks] = useState(() => localStorage.getItem('smartdesk.settings.webhooks') === 'true');
  const [token, setToken] = useState('demo-token••••••••');
  const [message, setMessage] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);
  const save = () => { localStorage.setItem('smartdesk.settings.roles', JSON.stringify(roles)); localStorage.setItem('smartdesk.settings.idle', idleTimeout); localStorage.setItem('smartdesk.settings.rate', rateLimit); localStorage.setItem('smartdesk.settings.webhooks', String(webhooks)); setMessage('Demo preferences saved in this browser.'); };
  const togglePermission = (resource, permission) => setRoles((current) => ({ ...current, [selectedRole]: { ...current[selectedRole], [resource]: { ...current[selectedRole][resource], [permission]: !current[selectedRole][resource][permission] } } }));
  const addRole = () => { const name = window.prompt('New role name'); if (!name?.trim()) return; if (roles[name.trim()]) { setMessage('That role already exists.'); return; } setRoles((current) => ({ ...current, [name.trim()]: Object.fromEntries(resources.map((resource) => [resource, { View: false, Create: false, Edit: false, Delete: false }])) })); setSelectedRole(name.trim()); setMessage(`Role “${name.trim()}” added. Save changes to persist.`); };
  const deleteRole = () => { if (!confirmDelete) { setConfirmDelete(true); return; } setRoles((current) => { const next = { ...current }; delete next[selectedRole]; return next; }); setSelectedRole(Object.keys(roles).find((role) => role !== selectedRole) || ''); setConfirmDelete(false); setMessage('Role deleted. Save changes to persist.'); };
  const rotateToken = () => { setToken(`demo-${Math.random().toString(36).slice(2, 10)}••••`); setMessage('Demo token rotated locally; no API credential was changed.'); };
  const roleNames = Object.keys(roles);
  return <AppShell title="Enterprise Settings & Role-Based Access Control" breadcrumb="Platform > Settings > RBAC & Security">
    <div className="flex flex-wrap items-center justify-between gap-3 mb-6"><div><span className="text-xs text-emerald-400 font-mono">DEMO SETTINGS • Browser-local preferences</span><h2 className="text-xl font-bold text-white">Enterprise Access Governance</h2></div><PrimaryButton icon={Save} onClick={save}>Save Changes</PrimaryButton></div>
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6"><KpiCard title="Access Pool" value={`${roleNames.length} Roles`} subtext="Sample roles" icon={Users} /><KpiCard title="Least Privilege" value="Demo" subtext="No live policy evaluation" icon={ShieldCheck} /><KpiCard title="Idle Invalidation" value={`${idleTimeout}m`} subtext="Local preference only" icon={Lock} /><KpiCard title="Audit Access" value={isAdmin ? 'ADMIN' : 'Restricted'} subtext="Live read-only records below" icon={Key} /></div>
    <section className="mb-6 rounded-lg border border-[#1e2638] bg-[#181c24] p-5"><div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><h3 className="text-sm font-semibold text-white">Role permissions</h3><p className="mt-1 text-xs text-slate-400">Changes are stored locally after Save Changes.</p></div><div className="flex gap-2"><select aria-label="Select role" value={selectedRole} onChange={(event) => { setSelectedRole(event.target.value); setConfirmDelete(false); }} className="rounded border border-[#1e2638] bg-[#0f131c] px-3 py-2 text-sm text-white">{roleNames.map((role) => <option key={role}>{role}</option>)}</select><PrimaryButton icon={Plus} size="sm" onClick={addRole}>Add Role</PrimaryButton>{!['Admin','Manager','Agent'].includes(selectedRole) && <PrimaryButton variant="danger" size="sm" icon={Trash2} onClick={deleteRole}>{confirmDelete ? 'Confirm delete' : 'Delete role'}</PrimaryButton>}</div></div>
      <div className="divide-y divide-[#1e2638] text-xs">{resources.map((resource) => <div key={resource} className="flex flex-wrap items-center justify-between gap-3 py-3"><span className="text-slate-200 font-medium">{resource}</span><div className="flex flex-wrap gap-4">{['View','Create','Edit','Delete'].map((permission) => <label key={permission} className="flex items-center gap-1.5 text-slate-300"><input type="checkbox" checked={Boolean(roles[selectedRole]?.[resource]?.[permission])} onChange={() => togglePermission(resource, permission)} />{permission}</label>)}</div></div>)}</div></section>
    <section className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-2"><div className="rounded-lg border border-[#1e2638] bg-[#181c24] p-5"><h3 className="mb-4 text-sm font-semibold text-white">Security & API preferences</h3><label className="mb-4 block text-xs text-slate-400">Idle timeout (minutes)<select value={idleTimeout} onChange={(event) => setIdleTimeout(event.target.value)} className="mt-1 block w-full rounded border border-[#1e2638] bg-[#0f131c] p-2 text-white"><option value="15">15</option><option value="30">30</option><option value="60">60</option></select></label><label className="mb-4 block text-xs text-slate-400">Demo API rate limit (requests/min)<input type="number" min="1" max="10000" value={rateLimit} onChange={(event) => setRateLimit(String(Math.min(10000, Math.max(1, Number(event.target.value) || 1))))} className="mt-1 block w-full rounded border border-[#1e2638] bg-[#0f131c] p-2 text-white" /></label><div className="mb-4 flex items-center justify-between text-xs text-slate-300"><span>Webhook delivery (demo preference)</span><input aria-label="Webhook delivery demo preference" type="checkbox" checked={webhooks} onChange={() => setWebhooks(!webhooks)} /></div><div className="flex flex-wrap items-center gap-2"><code className="rounded bg-[#0f131c] p-2 text-xs text-emerald-300">{token}</code><PrimaryButton variant="secondary" size="sm" icon={RotateCw} onClick={rotateToken}>Rotate demo token</PrimaryButton></div><p className="mt-2 text-[11px] text-slate-500">No API, key management, or webhook service is connected.</p></div>
      <div>{isAdmin ? <AuditLogPanel /> : <div className="rounded-lg border border-[#1e2638] bg-[#181c24] p-5"><h3 className="text-sm font-semibold text-white">Audit log</h3><p className="mt-2 text-xs text-slate-400">Audit records are restricted to ADMIN users.</p></div>}</div></section>
    {message && <p role="status" className="mb-4 text-xs text-emerald-300">{message}</p>}
  </AppShell>;
}
