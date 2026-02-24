import { createContext, useContext, useState, useEffect } from 'react';
import { api, getToken, setToken, clearToken } from './api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const token = getToken();
        if (token) {
            api.me()
                .then(data => setUser(data))
                .catch((e) => {
                    if (e.message === 'Non autenticato') clearToken();
                    // On 500 errors, we intentionally do NOT clear the token.
                    // React will naturally route to Login since user is null, 
                    // but the user only needs to refresh again to re-enter.
                })
                .finally(() => setLoading(false));
        } else {
            setLoading(false);
        }
    }, []);

    const login = async (username, password) => {
        const data = await api.login(username, password);
        setToken(data.token);
        // If pending or disabled, don't fetch /me (middleware would block anyway)
        if (data.status && data.status !== 'active') {
            setUser({ id: null, username, status: data.status, role: 'viewer', tenant_id: null });
        } else {
            const me = await api.me();
            setUser(me);
        }
        return data;
    };

    const register = async (username, password, tenant_id, new_tenant_name, new_tenant_slug) => {
        return await api.register(username, password, tenant_id, new_tenant_name, new_tenant_slug);
    };

    const logout = async () => {
        try { await api.logout(); } catch { }
        clearToken();
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, register, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth must be inside AuthProvider');
    return ctx;
}
