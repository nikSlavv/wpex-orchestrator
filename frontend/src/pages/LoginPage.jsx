import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { api } from '../api';
import { Lock, ArrowLeft, Users } from 'lucide-react';

export default function LoginPage() {
    const { login, register } = useAuth();
    const navigate = useNavigate();
    const [tab, setTab] = useState('login');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [loading, setLoading] = useState(false);

    // Login form
    const [loginUser, setLoginUser] = useState('');
    const [loginPass, setLoginPass] = useState('');

    // Register form
    const [regUser, setRegUser] = useState('');
    const [regPass, setRegPass] = useState('');
    const [regConfirm, setRegConfirm] = useState('');
    const [regTenant, setRegTenant] = useState('');
    const [isNewOrg, setIsNewOrg] = useState(false);
    const [regNewTenantName, setRegNewTenantName] = useState('');
    const [regNewTenantSlug, setRegNewTenantSlug] = useState('');
    const [tenants, setTenants] = useState([]);

    useEffect(() => {
        if (tab === 'register' && tenants.length === 0) {
            loadTenants();
        }
    }, [tab]);

    const loadTenants = async () => {
        try {
            const data = await api.getPublicTenants();
            setTenants(data.tenants || []);
            if (data.tenants?.length > 0) setRegTenant(data.tenants[0].id);
        } catch (err) {
            console.error('Failed to load tenants', err);
        }
    };

    const handleLogin = async (e) => {
        e.preventDefault();
        setError('');
        if (!loginUser || !loginPass) return setError('Inserisci username e password');
        setLoading(true);
        try {
            await login(loginUser, loginPass);
            navigate('/dashboard');
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleRegister = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');
        if (!regUser || !regPass) return setError('Compila username e password');
        if (!isNewOrg && !regTenant) return setError('Seleziona un\'organizzazione');
        if (isNewOrg && (!regNewTenantName || !regNewTenantSlug)) return setError('Specifica il nome e lo slug per la nuova organizzazione');
        if (regPass !== regConfirm) return setError('Le password non coincidono');
        setLoading(true);
        try {
            await register(
                regUser,
                regPass,
                isNewOrg ? null : parseInt(regTenant),
                isNewOrg ? regNewTenantName : null,
                isNewOrg ? regNewTenantSlug : null
            );
            setSuccess('Registrazione completata! Il tuo account (e la tua organizzazione se richiesta) è in attesa di approvazione.');
            setTab('login');
            setLoginUser(regUser);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-page">
            <div className="login-card card">
                <h1><Lock size={22} /> WPEX Login</h1>
                <p className="subtitle">Accedi alla dashboard di gestione</p>

                <div className="tabs">
                    <button className={`tab ${tab === 'login' ? 'active' : ''}`} onClick={() => { setTab('login'); setError(''); }}>
                        Accedi
                    </button>
                    <button className={`tab ${tab === 'register' ? 'active' : ''}`} onClick={() => { setTab('register'); setError(''); }}>
                        Registrati
                    </button>
                </div>

                {tab === 'login' ? (
                    <form onSubmit={handleLogin}>
                        <div className="form-group">
                            <label>Username</label>
                            <input className="input" value={loginUser} onChange={e => setLoginUser(e.target.value)} placeholder="Il tuo username" autoFocus />
                        </div>
                        <div className="form-group">
                            <label>Password</label>
                            <input className="input" type="password" value={loginPass} onChange={e => setLoginPass(e.target.value)} placeholder="La tua password" />
                        </div>
                        {error && <div className="error-msg">{error}</div>}
                        {success && <div className="success-msg">{success}</div>}
                        <button className="btn btn-primary btn-full" type="submit" disabled={loading}>
                            {loading ? 'Accesso...' : 'Entra'}
                        </button>
                    </form>
                ) : (
                    <form onSubmit={handleRegister}>
                        <div className="form-group">
                            <label>Username</label>
                            <input className="input" value={regUser} onChange={e => setRegUser(e.target.value)} placeholder="Scegli un username" autoFocus />
                        </div>

                        <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                            <input
                                type="checkbox"
                                id="isNewOrg"
                                checked={isNewOrg}
                                onChange={(e) => {
                                    setIsNewOrg(e.target.checked);
                                    if (e.target.checked) setRegTenant('');
                                }}
                            />
                            <label htmlFor="isNewOrg" style={{ margin: 0, cursor: 'pointer', fontSize: '0.9rem' }}>
                                Vuoi registrare una nuova organizzazione?
                            </label>
                        </div>

                        {!isNewOrg ? (
                            <div className="form-group">
                                <label>Scegli un'organizzazione esistente</label>
                                <div style={{ position: 'relative' }}>
                                    <select
                                        className="input"
                                        value={regTenant}
                                        onChange={e => setRegTenant(e.target.value)}
                                        style={{ paddingLeft: 38 }}
                                    >
                                        <option value="" disabled>Seleziona un tenant...</option>
                                        {tenants.map(t => (
                                            <option key={t.id} value={t.id}>{t.name}</option>
                                        ))}
                                    </select>
                                    <Users size={18} style={{ position: 'absolute', left: 12, top: 12, color: 'var(--text-muted)' }} />
                                </div>
                            </div>
                        ) : (
                            <div style={{ display: 'flex', gap: 12 }}>
                                <div className="form-group" style={{ flex: 1 }}>
                                    <label>Nome Azienda</label>
                                    <input
                                        className="input"
                                        value={regNewTenantName}
                                        onChange={e => {
                                            setRegNewTenantName(e.target.value);
                                            setRegNewTenantSlug(e.target.value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)+/g, ''));
                                        }}
                                        placeholder="Nome"
                                    />
                                </div>
                                <div className="form-group" style={{ flex: 1 }}>
                                    <label>Slug Azienda</label>
                                    <input
                                        className="input"
                                        value={regNewTenantSlug}
                                        onChange={e => setRegNewTenantSlug(e.target.value)}
                                        placeholder="slug-azienda"
                                    />
                                </div>
                            </div>
                        )}

                        <div className="form-group">
                            <label>Password</label>
                            <input className="input" type="password" value={regPass} onChange={e => setRegPass(e.target.value)} placeholder="Scegli una password" />
                        </div>
                        <div className="form-group">
                            <label>Conferma Password</label>
                            <input className="input" type="password" value={regConfirm} onChange={e => setRegConfirm(e.target.value)} placeholder="Ripeti la password" />
                        </div>
                        {error && <div className="error-msg">{error}</div>}
                        <button className="btn btn-primary btn-full" type="submit" disabled={loading}>
                            {loading ? 'Creazione...' : 'Crea Account'}
                        </button>
                    </form>
                )}

                <div style={{ textAlign: 'center', marginTop: 16 }}>
                    <Link to="/" style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                        <ArrowLeft size={14} /> Torna alla home
                    </Link>
                </div>
            </div>
        </div>
    );
}
