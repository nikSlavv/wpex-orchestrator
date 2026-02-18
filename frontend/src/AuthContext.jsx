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
                .catch(() => clearToken())
                .finally(() => setLoading(false));
        } else {
            setLoading(false);
        }
    }, []);

    const login = async (username, password) => {
        const data = await api.login(username, password);
        setToken(data.token);
        setUser({ id: data.id, username: data.username });
        return data;
    };

    const register = async (username, password) => {
        return await api.register(username, password);
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
