import { apiRequest } from './client.js';
import { adaptAssignment, adaptEmployee, adaptTicket } from './adapters.js';

function queryString(values) {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') params.set(key, String(value));
  });
  const query = params.toString();
  return query ? `?${query}` : '';
}

export const authApi = {
  me: async () => (await apiRequest('/auth/me/'))?.data?.user,
};

export const departmentApi = {
  list: async ({ includeInactive = false } = {}) => {
    const payload = await apiRequest(`/departments/${queryString(includeInactive ? { include_inactive: 'true' } : {})}`);
    return payload.data;
  },
};

export const ticketApi = {
  list: async (filters = {}) => {
    const payload = await apiRequest(`/tickets/${queryString(filters)}`);
    return { items: payload.data.map(adaptTicket), pagination: payload.meta?.pagination };
  },
  get: async (pk) => adaptTicket((await apiRequest(`/tickets/${pk}/`)).data),
  listAll: async (filters = {}) => {
    const all = [];
    let page = 1;
    let totalPages = 1;
    do {
      const result = await ticketApi.list({ ...filters, page, page_size: 100 });
      all.push(...result.items);
      totalPages = result.pagination?.total_pages || 0;
      page += 1;
    } while (page <= totalPages);
    return all;
  },
  create: async (payload) => adaptTicket((await apiRequest('/tickets/', { method: 'POST', body: payload })).data),
  update: async (pk, changes, expectedUpdatedAt) => adaptTicket((await apiRequest(`/tickets/${pk}/`, {
    method: 'PATCH', body: { ...changes, expected_updated_at: expectedUpdatedAt },
  })).data),
  bulk: async (ticketIds, action, value) => {
    const payload = await apiRequest('/tickets/bulk/', {
      method: 'POST', body: { ticket_ids: ticketIds, action, value },
    });
    return payload.data.map(adaptTicket);
  },
};

export const employeeApi = {
  list: async (filters = {}) => {
    const payload = await apiRequest(`/employees/${queryString(filters)}`);
    return { items: payload.data.map(adaptEmployee), pagination: payload.meta?.pagination };
  },
  listAll: async (filters = {}) => {
    const all = [];
    let page = 1;
    let totalPages = 1;
    do {
      const result = await employeeApi.list({ ...filters, page, page_size: 100 });
      all.push(...result.items);
      totalPages = result.pagination?.total_pages || 0;
      page += 1;
    } while (page <= totalPages);
    return all;
  },
  get: async (id) => adaptEmployee((await apiRequest(`/employees/${id}/`)).data),
  update: async (id, changes) => adaptEmployee((await apiRequest(`/employees/${id}/`, { method: 'PATCH', body: changes })).data),
};

export const assignmentApi = {
  list: async (filters = {}) => {
    const payload = await apiRequest(`/assignments/${queryString(filters)}`);
    return { items: payload.data.map(adaptAssignment), pagination: payload.meta?.pagination };
  },
  listAll: async (filters = {}) => {
    const all = [];
    let page = 1;
    let totalPages = 1;
    do {
      const result = await assignmentApi.list({ ...filters, page, page_size: 100 });
      all.push(...result.items);
      totalPages = result.pagination?.total_pages || 0;
      page += 1;
    } while (page <= totalPages);
    return all;
  },
  create: async (ticketPk, employeeProfileId, remarks = '') => adaptAssignment((await apiRequest(`/tickets/${ticketPk}/assignments/`, {
    method: 'POST', body: { employee_profile_id: employeeProfileId, remarks },
  })).data),
  update: async (id, changes) => adaptAssignment((await apiRequest(`/assignments/${id}/`, { method: 'PATCH', body: changes })).data),
};

export const aiApi = {
  analyze: async (ticketPk) => (await apiRequest(`/ai/analyze/${ticketPk}/`, { method: 'POST', body: {} })).data,
};

export const analyticsApi = {
  departments: async (filters = {}) => (await apiRequest(`/analytics/departments/${queryString(filters)}`)).data,
};

export const auditApi = {
  list: async (filters = {}) => {
    const payload = await apiRequest(`/audit-logs/${queryString(filters)}`);
    return { items: payload.data, pagination: payload.meta?.pagination };
  },
};
