/**
 * WPEX Orchestrator — API Client
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

    register: (username, password) =>
        request('/api/auth/register', { method: 'POST', body: JSON.stringify({ username, password }) }),

    logout: () =>
        request('/api/auth/logout', { method: 'POST' }),

    me: () =>
        request('/api/auth/me'),

    // --- Servers ---
    getServers: () =>
        request('/api/servers'),

    createServer: (name, udp_port, key_ids) =>
        request('/api/servers', { method: 'POST', body: JSON.stringify({ name, udp_port, key_ids }) }),

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

    createKey: (alias, key) =>
        request('/api/keys', { method: 'POST', body: JSON.stringify({ alias, key }) }),

    deleteKey: (id) =>
        request(`/api/keys/${id}`, { method: 'DELETE' }),
};
