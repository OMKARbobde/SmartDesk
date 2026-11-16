export const EVENT_LABELS = {
  TICKET_CREATED: 'Ticket created',
  TICKET_UPDATED: 'Ticket updated',
  TICKET_STATUS_CHANGED: 'Ticket status changed',
  TICKET_PRIORITY_CHANGED: 'Ticket priority changed',
  TICKET_BULK_STATUS_CHANGED: 'Bulk status change',
  TICKET_BULK_PRIORITY_CHANGED: 'Bulk priority change',
  ASSIGNMENT_CREATED: 'Assignment created',
  ASSIGNMENT_REASSIGNED: 'Assignment reassigned',
  ASSIGNMENT_ACCEPTED: 'Assignment accepted',
  ASSIGNMENT_COMPLETED: 'Assignment completed',
  TICKET_ARCHIVED: 'Ticket archived',
  TICKET_RESTORED: 'Ticket restored',
  DEPARTMENT_CREATED: 'Department created',
  DEPARTMENT_UPDATED: 'Department updated',
  DEPARTMENT_ACTIVATED: 'Department activated',
  DEPARTMENT_DEACTIVATED: 'Department deactivated',
};

export function describeDetails(event) {
  const { details = {}, target_user: targetUser } = event;
  if (event.event_type?.startsWith('DEPARTMENT_')) {
    const department = `Department #${details.department_id}`;
    if (event.event_type === 'DEPARTMENT_CREATED') {
      const fields = (details.changed_fields || []).map((field) => field.replaceAll('_', ' '));
      return `${department} · ${fields.join(', ')} · ${details.is_active ? 'Active' : 'Inactive'}`;
    }
    if (event.event_type === 'DEPARTMENT_UPDATED') {
      const fields = (details.changed_fields || []).map((field) => field.replaceAll('_', ' '));
      return `${department} · Updated: ${fields.join(', ')}`;
    }
    return `${department} · ${details.from ? 'Active' : 'Inactive'} → ${details.to ? 'Active' : 'Inactive'}`;
  }
  if (Array.isArray(details.changed_fields)) {
    const names = details.changed_fields.map((field) => field.replaceAll('_', ' '));
    const department = details.changes?.department_id;
    return department
      ? `${names.join(', ')} · department ${department.from ?? 'none'} → ${department.to ?? 'none'}`
      : names.join(', ');
  }
  if ('from' in details && 'to' in details) return `${details.from} → ${details.to}`;
  if (details.assignment_status) return `${details.assignment_status} · ${targetUser?.display_name || 'Assignee unavailable'}`;
  if (details.assigned_to_profile_id) return `Assigned to ${targetUser?.display_name || 'employee'} · profile #${details.assigned_to_profile_id}`;
  if (details.previous_assignee_user_id) return `Reassigned from user #${details.previous_assignee_user_id} to ${targetUser?.display_name || 'new assignee'}`;
  if (details.status || details.priority) return [details.status, details.priority].filter(Boolean).join(' · ');
  return '—';
}
