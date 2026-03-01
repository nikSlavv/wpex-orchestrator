/**
 * WPEX Orchestrator SaaS — API Client
 * Handles all fetch calls with JWT auth.
 */

const TOKEN_KEY = 'wpex_token';

export function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
}

async function request(url, options = {}) {
    const token = getToken();
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(url, { ...options, headers });

    if (res.status === 401) {
        clearToken();
        window.location.href = '/login';
        throw new Error('Non autenticato');
    }

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Errore API');
    return data;
}

// --- Auth ---
export const api = {
    login: (username, password) =>
        request('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),

    register: (username, password, tenant_id, new_tenant_name, new_tenant_slug) =>
        request('/api/auth/register', { method: 'POST', body: JSON.stringify({ username, password, tenant_id, new_tenant_name, new_tenant_slug }) }),

    getPublicTenants: () =>
        request('/api/auth/public/tenants'),

    logout: () =>
        request('/api/auth/logout', { method: 'POST' }),

    me: () =>
        request('/api/auth/me'),

    // --- Servers (legacy) ---
    getServers: () =>
        request('/api/servers'),

    createServer: (name, udp_port, key_ids, tenant_id) =>
        request('/api/servers', { method: 'POST', body: JSON.stringify({ name, udp_port, key_ids, tenant_id }) }),

    deleteServer: (id) =>
        request(`/api/servers/${id}`, { method: 'DELETE' }),

    startServer: (id) =>
        request(`/api/servers/${id}/start`, { method: 'POST' }),

    stopServer: (id) =>
        request(`/api/servers/${id}/stop`, { method: 'POST' }),

    updateServerKeys: (id, key_ids) =>
        request(`/api/servers/${id}/keys`, { method: 'PUT', body: JSON.stringify({ key_ids }) }),

    getServerLogs: (id) =>
        request(`/api/servers/${id}/logs`),

    // --- Keys ---
    getKeys: () =>
        request('/api/keys'),

    createKey: (alias, key, tenant_id) =>
        request('/api/keys', { method: 'POST', body: JSON.stringify({ alias, key, tenant_id }) }),

    deleteKey: (id) =>
        request(`/api/keys/${id}`, { method: 'DELETE' }),

    // --- Dashboard KPI ---
    getDashboardKPI: () =>
        request('/api/dashboard/kpi'),

    getDashboardAlerts: () =>
        request('/api/dashboard/alerts'),

    getTopologyData: () =>
        request('/api/dashboard/topology'),

    // --- Tenants ---
    getTenants: () =>
        request('/api/tenants'),

    createTenant: (data) =>
        request('/api/tenants', { method: 'POST', body: JSON.stringify(data) }),

    getTenant: (id) =>
        request(`/api/tenants/${id}`),

    updateTenant: (id, data) =>
        request(`/api/tenants/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

    updateTenantStatus: (id, status) =>
        request(`/api/tenants/${id}`, { method: 'PUT', body: JSON.stringify({ status }) }),

    deleteTenant: (id) =>
        request(`/api/tenants/${id}`, { method: 'DELETE' }),

    getSites: (tenantId) =>
        request(`/api/tenants/${tenantId}/sites`),

    createSite: (tenantId, data) =>
        request(`/api/tenants/${tenantId}/sites`, { method: 'POST', body: JSON.stringify(data) }),

    deleteSite: (tenantId, siteId) =>
        request(`/api/tenants/${tenantId}/sites/${siteId}`, { method: 'DELETE' }),

    getTenantUsage: (tenantId) =>
        request(`/api/tenants/${tenantId}/usage`),

    // --- Relay Enhanced ---
    getRelayStats: (id) =>
        request(`/api/relays/${id}/stats`),

    getRelayHealth: (id) =>
        request(`/api/relays/${id}/health`),

    getRelayContainer: (id) =>
        request(`/api/relays/${id}/container`),

    restartRelay: (id) =>
        request(`/api/relays/${id}/restart`, { method: 'POST' }),

    upgradeRelay: (id, image) =>
        request(`/api/relays/${id}/upgrade`, { method: 'POST', body: JSON.stringify({ image }) }),

    pingFromRelay: (id, target) =>
        request(`/api/relays/${id}/diagnostics/ping`, { method: 'POST', body: JSON.stringify({ target }) }),

    tracerouteFromRelay: (id, target) =>
        request(`/api/relays/${id}/diagnostics/traceroute`, { method: 'POST', body: JSON.stringify({ target }) }),

    // --- Audit ---
    getAuditLog: (params = {}) =>
        request(`/api/audit?${new URLSearchParams(params)}`),

    // --- Users (RBAC) ---
    getUsers: () =>
        request('/api/auth/users'),

    updateUserRole: (userId, role) =>
        request(`/api/auth/users/${userId}/role`, { method: 'PUT', body: JSON.stringify({ role }) }),

    updateUserTenant: (userId, tenant_id) =>
        request(`/api/auth/users/${userId}/tenant`, { method: 'PUT', body: JSON.stringify({ tenant_id }) }),

    updateUserStatus: (userId, status) =>
        request(`/api/auth/users/${userId}/status`, { method: 'PUT', body: JSON.stringify({ status }) }),

    // --- Zabbix ---
    getZabbixHosts: () =>
        request('/api/zabbix/hosts'),

    getDockerStats: (hostid) =>
        request(`/api/zabbix/docker/${hostid}`),

    getItemHistory: (itemid, hours = 1, value_type = 0) =>
        request(`/api/zabbix/history/${itemid}?hours=${hours}&value_type=${value_type}`),
};
