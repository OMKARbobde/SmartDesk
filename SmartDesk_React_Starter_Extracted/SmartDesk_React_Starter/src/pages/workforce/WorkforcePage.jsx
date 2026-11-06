import { useEffect, useMemo, useState } from 'react';
import { AlertCircle, Clock, Search, Users, Zap } from 'lucide-react';
import { AppShell } from '../../components/layout/AppShell';
import { ApiState } from '../../components/ui/ApiState';
import { DataTable } from '../../components/ui/DataTable';
import { Drawer } from '../../components/ui/Drawer';
import { KpiCard } from '../../components/ui/KpiCard';
import { PrimaryButton } from '../../components/ui/PrimaryButton';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { assignmentApi, departmentApi, employeeApi, ticketApi } from '../../api/resources';
import { errorMessage } from '../../api/client';
import { useAuth } from '../../context/AuthContext';

const CURRENT_ASSIGNMENTS = ['ASSIGNED', 'ACCEPTED'];

export function WorkforcePage() {
  const { user } = useAuth();
  const isDirectoryRole = ['ADMIN', 'AGENT'].includes(user?.role);
  const isAdmin = user?.role === 'ADMIN';
  const [employees, setEmployees] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [search, setSearch] = useState('');
  const [department, setDepartment] = useState('');
  const [selected, setSelected] = useState(null);
  const [ticketPk, setTicketPk] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [reloadVersion, setReloadVersion] = useState(0);
  const [profileDraft, setProfileDraft] = useState(null);
  const [phoneDraft, setPhoneDraft] = useState('');

  const load = async () => {
    setLoading(true); setError('');
    try {
      const employeeRequest = isDirectoryRole
        ? employeeApi.listAll({ search: search.trim(), department })
        : user?.employee_profile_id ? employeeApi.get(user.employee_profile_id).then((employee) => [employee]) : Promise.resolve([]);
      const [employeeRows, ticketRows, assignmentRows, departmentRows] = await Promise.all([
        employeeRequest, ticketApi.listAll(), assignmentApi.listAll(), departmentApi.list(),
      ]);
      setEmployees(employeeRows); setTickets(ticketRows); setAssignments(assignmentRows); setDepartments(departmentRows);
    } catch (requestError) { setError(errorMessage(requestError)); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [isDirectoryRole, user?.employee_profile_id, search, department, reloadVersion]);

  const activeCount = assignments.filter((assignment) => CURRENT_ASSIGNMENTS.includes(assignment.statusValue)).length;
  const availableCount = employees.filter((employee) => employee.isAvailable).length;
  const columns = [
    { header: 'Employee & Role', accessor: 'name', render: (row) => <div><div className="font-semibold text-white">{row.name}</div><div className="text-xs text-slate-400">{row.designation} · {row.role}</div></div> },
    { header: 'Department', accessor: 'dept' },
    { header: 'Active assignments', accessor: 'activeAssignmentCount' },
    { header: 'Availability', render: (row) => <StatusBadge status={row.isAvailable ? 'Available' : 'Unavailable'} /> },
    { header: 'Employee ID', accessor: 'employeeId', cellClassName: 'font-mono text-xs text-slate-400' },
  ];
  const selectedAssignments = useMemo(() => selected ? assignments.filter((item) => item.employeeProfileId === selected.id) : [], [assignments, selected]);
  const selectedTickets = useMemo(() => tickets.filter((ticket) => ticket.assignmentId == null), [tickets]);

  const selectEmployee = async (employee) => {
    setSelected(employee); setProfileDraft({ designation: employee.designation, department_id: employee.departmentId, is_available: employee.isAvailable });
    setPhoneDraft(employee.phoneNumber); setMessage(''); setError(''); setTicketPk('');
    try { setSelected(await employeeApi.get(employee.id)); }
    catch (requestError) { setError(errorMessage(requestError)); }
  };

  const updateProfile = async (event) => {
    event.preventDefault(); if (!selected) return;
    setSaving(true); setError(''); setMessage('');
    const changes = isAdmin
      ? { ...profileDraft, department_id: profileDraft.department_id ? Number(profileDraft.department_id) : null }
      : { phone_number: phoneDraft };
    try {
      const updated = await employeeApi.update(selected.id, changes);
      setSelected(updated); setProfileDraft({ designation: updated.designation, department_id: updated.departmentId, is_available: updated.isAvailable });
      setPhoneDraft(updated.phoneNumber); setEmployees((current) => current.map((row) => row.id === updated.id ? updated : row));
      setMessage('Employee profile updated.');
    } catch (requestError) { setError(errorMessage(requestError)); }
    finally { setSaving(false); }
  };

  const assignTicket = async (event) => {
    event.preventDefault(); if (!selected || !ticketPk) return;
    setSaving(true); setError(''); setMessage('');
    try {
      await assignmentApi.create(Number(ticketPk), selected.id);
      setMessage(`Ticket assignment saved for ${selected.name}.`);
      setReloadVersion((version) => version + 1);
    } catch (requestError) { setError(errorMessage(requestError)); }
    finally { setSaving(false); }
  };

  const changeAssignmentStatus = async (assignment, nextStatus) => {
    setSaving(true); setError(''); setMessage('');
    try {
      const updatedAssignment = await assignmentApi.update(assignment.id, { status: nextStatus });
      const wasCurrent = CURRENT_ASSIGNMENTS.includes(assignment.statusValue);
      const isCurrent = CURRENT_ASSIGNMENTS.includes(updatedAssignment.statusValue);
      if (wasCurrent !== isCurrent) {
        setSelected((current) => current ? {
          ...current,
          activeAssignmentCount: Math.max(0, (current.activeAssignmentCount || 0) + (isCurrent ? 1 : -1)),
        } : current);
      }
      setReloadVersion((version) => version + 1);
    } catch (requestError) { setError(errorMessage(requestError)); }
    finally { setSaving(false); }
  };

  return <AppShell title="Employee Directory & Workload" breadcrumb="Platform > Workforce > Allocation">
    <div className="mb-4 rounded-lg border border-amber-800/50 bg-amber-950/20 p-3 text-xs text-amber-200">Live employee and assignment data. Capacity targets, CSAT, and staffing analytics are not available from the current API.</div>
    <ApiState loading={loading} error={error} onRetry={load}>
      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-4"><KpiCard title={isDirectoryRole ? 'Listed Employees' : 'Your Profile'} value={employees.length} delta="Live directory" subtext={isDirectoryRole ? 'Current API result' : 'Authenticated account'} icon={Users} /><KpiCard title="Available Employees" value={isDirectoryRole ? availableCount : (employees[0]?.isAvailable ? 1 : 0)} delta="Profile availability" subtext="Existing availability field" icon={Zap} /><KpiCard title="Current Assignments" value={activeCount} delta="Assigned or accepted" subtext="From assignment records" icon={AlertCircle} /><KpiCard title="Capacity / CSAT" value="Unavailable" delta="Not provided" subtext="No backend fields or API" icon={Clock} /></div>
      {isDirectoryRole && <div className="mb-4 flex flex-col gap-3 sm:flex-row"><label className="relative flex-1"><Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><input aria-label="Search employees" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search people, roles, departments" className="w-full rounded-lg border border-[#1e2638] bg-[#181c24] py-2 pl-9 pr-3 text-sm text-white" /></label><select aria-label="Filter employee department" value={department} onChange={(event) => setDepartment(event.target.value)} className="rounded-lg border border-[#1e2638] bg-[#181c24] px-3 py-2 text-sm text-slate-300"><option value="">All departments</option>{departments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></div>}
      {isDirectoryRole ? <DataTable columns={columns} data={employees} onRowClick={selectEmployee} /> : employees.length ? <DataTable columns={columns} data={employees} onRowClick={selectEmployee} /> : <p className="rounded-lg border border-[#1e2638] bg-[#181c24] p-5 text-sm text-slate-400">No employee profile is linked to this account.</p>}
    </ApiState>
    <Drawer isOpen={Boolean(selected)} onClose={() => { setSelected(null); setError(''); setMessage(''); }} title={selected?.name || ''} subtitle="Employee profile and assignment history">
      {selected && <div className="space-y-5">
        <div className="rounded-lg border border-[#1e2638] bg-[#181c24] p-4"><p className="text-white">{selected.designation} · {selected.role}</p><p className="text-xs text-slate-400">{selected.dept} · {selected.employeeId}</p><p className="mt-3 text-sm text-slate-200">{selected.activeAssignmentCount} current assignments</p><p className="mt-1 text-xs text-slate-400">Availability: {selected.isAvailable ? 'Available' : 'Unavailable'}</p><p className="mt-2 text-xs text-slate-500">CSAT and capacity targets are unavailable.</p></div>
        {isAdmin && profileDraft && <form onSubmit={updateProfile} className="space-y-3 rounded-lg border border-[#1e2638] bg-[#181c24] p-4"><h3 className="text-sm font-semibold text-white">Workforce profile</h3><label className="block text-xs text-slate-400">Designation<input value={profileDraft.designation} onChange={(event) => setProfileDraft({ ...profileDraft, designation: event.target.value })} className="mt-1 w-full rounded border border-[#1e2638] bg-[#0f131c] p-2 text-white" /></label><label className="block text-xs text-slate-400">Department<select value={profileDraft.department_id || ''} onChange={(event) => setProfileDraft({ ...profileDraft, department_id: event.target.value })} className="mt-1 w-full rounded border border-[#1e2638] bg-[#0f131c] p-2 text-white"><option value="">Choose department</option>{departments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label className="flex items-center gap-2 text-xs text-slate-300"><input type="checkbox" checked={profileDraft.is_available} onChange={(event) => setProfileDraft({ ...profileDraft, is_available: event.target.checked })} />Available for assignments</label><PrimaryButton type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save profile'}</PrimaryButton></form>}
        {!isAdmin && user?.role === 'EMPLOYEE' && <form onSubmit={updateProfile} className="space-y-3 rounded-lg border border-[#1e2638] bg-[#181c24] p-4"><label className="block text-xs text-slate-400">Phone number<input maxLength={15} value={phoneDraft} onChange={(event) => setPhoneDraft(event.target.value)} className="mt-1 w-full rounded border border-[#1e2638] bg-[#0f131c] p-2 text-white" /></label><PrimaryButton type="submit" disabled={saving}>{saving ? 'Saving…' : 'Update phone'}</PrimaryButton></form>}
        {isDirectoryRole && selected.isAvailable && <form onSubmit={assignTicket} className="space-y-3 rounded-lg border border-[#1e2638] bg-[#181c24] p-4"><label className="block text-xs text-slate-400">Assign or reassign ticket<select required value={ticketPk} onChange={(event) => setTicketPk(event.target.value)} className="mt-1 block w-full rounded border border-[#1e2638] bg-[#0f131c] p-2 text-white"><option value="">Choose a visible ticket</option>{tickets.map((ticket) => <option key={ticket.pk} value={ticket.pk}>{ticket.id} — {ticket.title}{ticket.assignmentId ? ' (currently assigned)' : ' (unassigned)'}</option>)}</select></label><PrimaryButton type="submit" disabled={saving || !ticketPk}>{saving ? 'Assigning…' : 'Assign ticket'}</PrimaryButton></form>}
        <section><h3 className="mb-2 text-sm font-semibold text-white">Assignment history</h3>{selectedAssignments.length ? <div className="space-y-2">{selectedAssignments.map((assignment) => <div key={assignment.id} className="rounded border border-[#1e2638] bg-[#0f131c] p-3"><div className="flex items-center justify-between gap-2"><span className="font-mono text-xs text-blue-300">{assignment.ticketPublicId}</span><StatusBadge status={assignment.status} /></div><p className="mt-1 text-xs text-slate-400">Assigned by {assignment.assignedBy} · {new Date(assignment.assignedAt).toLocaleString()}</p>{assignment.remarks && <p className="mt-1 text-xs text-slate-300">{assignment.remarks}</p>}{CURRENT_ASSIGNMENTS.includes(assignment.statusValue) && <div className="mt-2 flex gap-2">{assignment.statusValue === 'ASSIGNED' && (user?.role === 'EMPLOYEE' || isDirectoryRole) && <button type="button" disabled={saving} onClick={() => changeAssignmentStatus(assignment, 'ACCEPTED')} className="rounded border border-blue-700 px-2 py-1 text-xs text-blue-200 disabled:opacity-50">Accept</button>}{assignment.statusValue === 'ACCEPTED' && (user?.role === 'EMPLOYEE' || isDirectoryRole) && <button type="button" disabled={saving} onClick={() => changeAssignmentStatus(assignment, 'COMPLETED')} className="rounded border border-emerald-700 px-2 py-1 text-xs text-emerald-200 disabled:opacity-50">Complete</button>}</div>}</div>)}</div> : <p className="text-xs text-slate-500">No assignment history is available for this employee.</p>}</section>
        {error && <p role="alert" className="text-xs text-rose-300">{error}</p>}{message && <p role="status" className="text-xs text-emerald-300">{message}</p>}
      </div>}
    </Drawer>
  </AppShell>;
}
