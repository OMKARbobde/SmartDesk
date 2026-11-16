import { useEffect, useState } from 'react';
import { Building2, Pencil, Plus } from 'lucide-react';
import { AppShell } from '../../components/layout/AppShell';
import { ApiState } from '../../components/ui/ApiState';
import { DataTable } from '../../components/ui/DataTable';
import { Drawer } from '../../components/ui/Drawer';
import { PrimaryButton } from '../../components/ui/PrimaryButton';
import { departmentApi } from '../../api/resources';
import { errorMessage } from '../../api/client';

const emptyDraft = { name: '', code: '', description: '', is_active: true };

export function DepartmentManagementPage() {
  const [departments, setDepartments] = useState([]);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [actionError, setActionError] = useState('');
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState(null);
  const [draft, setDraft] = useState(emptyDraft);
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState(null);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      setDepartments(await departmentApi.list({ includeInactive }));
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [includeInactive]);

  const startCreate = () => {
    setEditing(null);
    setDraft(emptyDraft);
    setCreating(true);
    setNotice('');
    setActionError('');
  };

  const startEdit = (department) => {
    setEditing(department);
    setCreating(false);
    setDraft({
      name: department.name,
      code: department.code,
      description: department.description || '',
      is_active: department.is_active,
    });
    setNotice('');
    setActionError('');
  };

  const save = async (event) => {
    event.preventDefault();
    setSaving(true);
    setActionError('');
    try {
      const payload = { ...draft, name: draft.name.trim(), code: draft.code.trim() };
      if (editing) await departmentApi.update(editing.id, payload);
      else await departmentApi.create(payload);
      setEditing(null);
      setCreating(false);
      setNotice(editing ? 'Department updated.' : 'Department created.');
      await load();
    } catch (requestError) {
      setActionError(errorMessage(requestError));
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async (department) => {
    setBusyId(department.id);
    setActionError('');
    setNotice('');
    try {
      await departmentApi.update(department.id, { is_active: !department.is_active });
      setNotice(department.is_active ? 'Department deactivated.' : 'Department activated.');
      await load();
    } catch (requestError) {
      setActionError(errorMessage(requestError));
    } finally {
      setBusyId(null);
    }
  };

  const columns = [
    { header: 'Department', accessor: 'name', render: (row) => <div><p className="font-semibold text-white">{row.name}</p><p className="mt-1 text-xs text-slate-400">{row.description || 'No description'}</p></div> },
    { header: 'Code', accessor: 'code', cellClassName: 'font-mono text-xs text-slate-300' },
    { header: 'Status', render: (row) => <span className={`rounded border px-2 py-1 text-[10px] font-semibold uppercase ${row.is_active ? 'border-emerald-800 bg-emerald-950/30 text-emerald-300' : 'border-slate-700 bg-slate-900 text-slate-400'}`}>{row.is_active ? 'Active' : 'Inactive'}</span> },
    { header: 'Actions', render: (row) => <div className="flex flex-wrap gap-2"><PrimaryButton variant="secondary" size="sm" icon={Pencil} onClick={() => startEdit(row)} aria-label={`Edit ${row.name}`}>Edit</PrimaryButton><button type="button" disabled={busyId === row.id} onClick={() => toggleActive(row)} aria-label={`${row.is_active ? 'Deactivate' : 'Activate'} ${row.name}`} className="rounded border border-[#30394a] px-2.5 py-1.5 text-xs text-slate-300 hover:bg-[#202634] focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500 disabled:opacity-50">{row.is_active ? 'Deactivate' : 'Activate'}</button></div> },
  ];

  return <AppShell title="Department Management" breadcrumb="Platform > Administration > Departments">
    <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
      <div className="flex items-start gap-3"><div className="rounded-lg border border-blue-800/60 bg-blue-950/30 p-2 text-blue-300"><Building2 className="h-5 w-5" /></div><div><h2 className="text-lg font-semibold text-white">Departments</h2><p className="mt-1 text-xs text-slate-400">Manage department names, codes, descriptions and availability.</p></div></div>
      <PrimaryButton icon={Plus} onClick={startCreate}>Create Department</PrimaryButton>
    </div>
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[#1e2638] bg-[#181c24] p-3">
      <p className="text-xs text-slate-400">Deactivating a department preserves tickets and employee references.</p>
      <label className="flex items-center gap-2 text-xs text-slate-300"><input aria-label="Include inactive departments" type="checkbox" checked={includeInactive} onChange={(event) => setIncludeInactive(event.target.checked)} className="rounded border-slate-700 bg-slate-900 text-blue-600 focus:ring-blue-500/20" />Include inactive</label>
    </div>
    {notice && <p role="status" className="mb-3 text-xs text-emerald-300">{notice}</p>}
      {error && <p role="alert" className="mb-3 rounded border border-rose-800/60 bg-rose-950/20 p-3 text-xs text-rose-200">{error}</p>}
      {actionError && <p role="alert" className="mb-3 rounded border border-rose-800/60 bg-rose-950/20 p-3 text-xs text-rose-200">{actionError}</p>}
    <ApiState loading={loading} error={error} onRetry={load}>
      {departments.length ? <DataTable columns={columns} data={departments} /> : <div className="rounded-lg border border-[#1e2638] bg-[#181c24] p-8 text-center text-sm text-slate-400">No departments match this view.</div>}
    </ApiState>

    <Drawer isOpen={creating || Boolean(editing)} onClose={() => { setEditing(null); setCreating(false); setDraft(emptyDraft); }} title={editing ? 'Edit Department' : 'Create Department'} subtitle="Department changes apply to future selection; existing references are preserved." width="max-w-lg">
      <form onSubmit={save} className="space-y-4">
        <label className="block text-xs text-slate-400">Name<input required maxLength={100} value={draft.name} onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))} className="mt-1 w-full rounded border border-[#1e2638] bg-[#181c24] p-2 text-sm text-white" /></label>
        <label className="block text-xs text-slate-400">Code<input required maxLength={10} value={draft.code} onChange={(event) => setDraft((current) => ({ ...current, code: event.target.value }))} className="mt-1 w-full rounded border border-[#1e2638] bg-[#181c24] p-2 font-mono text-sm text-white" /></label>
        <label className="block text-xs text-slate-400">Description<textarea maxLength={10000} rows={4} value={draft.description} onChange={(event) => setDraft((current) => ({ ...current, description: event.target.value }))} className="mt-1 w-full rounded border border-[#1e2638] bg-[#181c24] p-2 text-sm text-white" /></label>
        <label className="flex items-center gap-2 text-xs text-slate-300"><input type="checkbox" checked={draft.is_active} onChange={(event) => setDraft((current) => ({ ...current, is_active: event.target.checked }))} />Active</label>
        {actionError && <p role="alert" className="text-xs text-rose-300">{actionError}</p>}
        <div className="flex justify-end gap-2"><PrimaryButton type="button" variant="secondary" onClick={() => { setEditing(null); setCreating(false); setDraft(emptyDraft); }}>Cancel</PrimaryButton><PrimaryButton type="submit" disabled={saving}>{saving ? 'Saving…' : editing ? 'Save Department' : 'Create Department'}</PrimaryButton></div>
      </form>
    </Drawer>
  </AppShell>;
}
