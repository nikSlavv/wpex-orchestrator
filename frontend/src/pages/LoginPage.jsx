import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { Lock, ArrowLeft } from 'lucide-react';

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
        if (!regUser || !regPass) return setError('Compila tutti i campi');
        if (regPass !== regConfirm) return setError('Le password non coincidono');
        setLoading(true);
        try {
            await register(regUser, regPass);
            setSuccess('Account creato! Puoi ora accedere.');
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
