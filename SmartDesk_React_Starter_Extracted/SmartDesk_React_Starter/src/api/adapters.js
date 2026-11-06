export const ROLE_LABELS = { ADMIN: 'Admin', AGENT: 'Support Agent', EMPLOYEE: 'Employee' };
export const STATUS_LABELS = { OPEN: 'Open', IN_PROGRESS: 'In Progress', RESOLVED: 'Resolved', CLOSED: 'Closed' };
export const STATUS_VALUES = Object.fromEntries(Object.entries(STATUS_LABELS).map(([value, label]) => [label, value]));
export const PRIORITY_LABELS = { LOW: 'Low', MEDIUM: 'Medium', HIGH: 'High', CRITICAL: 'Critical' };
export const ASSIGNMENT_LABELS = { ASSIGNED: 'Assigned', ACCEPTED: 'Accepted', COMPLETED: 'Completed', REASSIGNED: 'Reassigned' };
export const SENTIMENT_LABELS = { POSITIVE: 'Positive', NEUTRAL: 'Neutral', NEGATIVE: 'Negative' };

export function displayEnum(mapping, value) {
  return mapping[value] || value || '—';
}

function displayName(user) {
  return user?.display_name || '—';
}

export function adaptTicket(ticket) {
  return {
    pk: ticket.id,
    id: ticket.ticket_id,
    publicId: ticket.ticket_id,
    title: ticket.title,
    description: ticket.description,
    dept: ticket.department?.name || 'Unassigned',
    departmentId: ticket.department?.id ?? null,
    departmentCode: ticket.department?.code ?? null,
    requester: displayName(ticket.requester),
    assignee: displayName(ticket.assignee) === '—' ? 'Unassigned' : displayName(ticket.assignee),
    assignmentId: ticket.assignment_id,
    priority: ticket.priority,
    status: displayEnum(STATUS_LABELS, ticket.status),
    createdAt: ticket.created_at,
    updatedAt: ticket.updated_at,
    date: ticket.created_at ? new Date(ticket.created_at).toLocaleString() : '—',
    raw: ticket,
  };
}

export function adaptEmployee(profile) {
  return {
    id: profile.id,
    userId: profile.user_id,
    employeeId: profile.employee_id,
    name: profile.display_name,
    email: profile.email,
    role: displayEnum(ROLE_LABELS, profile.role),
    designation: profile.designation,
    departmentId: profile.department?.id,
    dept: profile.department?.name || '—',
    phoneNumber: profile.phone_number || '',
    isAvailable: profile.is_available,
    joinedAt: profile.joined_at,
    activeAssignmentCount: profile.active_assignment_count ?? 0,
    raw: profile,
  };
}

export function adaptAssignment(assignment) {
  return {
    id: assignment.id,
    ticketPk: assignment.ticket_id,
    ticketPublicId: assignment.public_ticket_id,
    employeeProfileId: assignment.assigned_to.employee_profile_id,
    employeeId: assignment.assigned_to.employee_id,
    assignee: assignment.assigned_to.display_name,
    assignedBy: assignment.assigned_by?.display_name || '—',
    status: displayEnum(ASSIGNMENT_LABELS, assignment.status),
    statusValue: assignment.status,
    assignedAt: assignment.assigned_at,
    remarks: assignment.remarks || '',
    raw: assignment,
  };
}

export function adaptAnalysis(analysis) {
  return {
    ...analysis,
    priorityLabel: displayEnum(PRIORITY_LABELS, analysis.predicted_priority),
    sentimentLabel: displayEnum(SENTIMENT_LABELS, analysis.sentiment),
    analyzedAt: analysis.analyzed_at ? new Date(analysis.analyzed_at).toLocaleString() : '—',
  };
}
