import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../AuthContext';
import {
    ArrowLeft, Monitor, Settings, Play, Square, Key,
    ChevronDown, ChevronUp, LogOut, User, LayoutDashboard, RefreshCw
} from 'lucide-react';

export default function ServerView() {
    const { name } = useParams();
    const navigate = useNavigate();
    const { user, logout } = useAuth();
    const canMutate = !['viewer', 'executive'].includes(user?.role);
    const [server, setServer] = useState(null);
    const [allKeys, setAllKeys] = useState([]);
    const [logs, setLogs] = useState('');
    const [showLogs, setShowLogs] = useState(false);
    const [showKeys, setShowKeys] = useState(false);
    const [loading, setLoading] = useState(true);

    const refresh = async () => {
        try {
            const [srvData, keyData] = await Promise.all([api.getServers(), api.getKeys()]);
            const found = srvData.servers.find(s => s.name === name);
            setServer(found || null);
            setAllKeys(keyData.keys);
        } catch { } finally {
            setLoading(false);
        }
    };

    useEffect(() => { refresh(); }, [name]);

    const handleAction = async (action) => {
        if (!server) return;
        if (action === 'start') await api.startServer(server.id);
        if (action === 'stop') await api.stopServer(server.id);
        refresh();
    };

    const toggleLogs = async () => {
        if (showLogs) {
            setShowLogs(false);
        } else {
            const data = await api.getServerLogs(server.id);
            setLogs(data.logs);
            setShowLogs(true);
        }
    };

    const handleUpdateKeys = async (keyId, checked) => {
        const current = server.keys.map(k => k.id);
        const updated = checked ? [...current, keyId] : current.filter(x => x !== keyId);
        await api.updateServerKeys(server.id, updated);
        refresh();
    };

    const handleLogout = async () => {
        await logout();
        navigate('/');
    };

    if (loading) return <div className="loading-screen"><div className="spinner" /></div>;

    if (!server) return (
        <div className="page" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
            <div className="card" style={{ textAlign: 'center', padding: 40 }}>
                <h2>Server "{name}" non trovato</h2>
                <button className="btn" onClick={() => navigate('/dashboard')} style={{ marginTop: 16 }}>
                    <ArrowLeft size={14} /> Torna alla Dashboard
                </button>
            </div>
        </div>
    );

    const guiUrl = `/wpex-${name}/`;

    return (
        <div className="page">
            {/* Sidebar */}
            <nav className="sidebar">
                <div className="sidebar-brand">
                    <LayoutDashboard size={22} /> WPEX Orchestrator
                </div>

                <button className="btn btn-full" onClick={() => navigate('/dashboard')} style={{ marginBottom: 16 }}>
                    <ArrowLeft size={14} /> Dashboard
                </button>

                <div className="card" style={{ padding: 16, marginBottom: 16 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                        <span className={`status-dot ${server.status}`} />
                        <strong>wpex-{server.name}</strong>
                    </div>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        <span className="badge">UDP: {server.udp_port}</span>
                        <span className="badge badge-blue">Web: {server.web_port}</span>
                    </div>
                </div>

                {canMutate && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        <button className="btn btn-sm btn-full" onClick={() => handleAction('start')} disabled={server.status === 'running'}>
                            <Play size={14} /> Start
                        </button>
                        <button className="btn btn-sm btn-full" onClick={() => handleAction('stop')} disabled={server.status !== 'running'}>
                            <Square size={14} /> Stop
                        </button>
                        <button className="btn btn-sm btn-full" onClick={refresh}>
                            <RefreshCw size={14} /> Refresh
                        </button>
                    </div>
                )}
                {!canMutate && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        <button className="btn btn-sm btn-full" onClick={refresh}>
                            <RefreshCw size={14} /> Refresh
                        </button>
                    </div>
                )}

                <div className="sidebar-user">
                    <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <User size={16} /> {user?.username}
                    </span>
                    <button className="btn btn-sm" onClick={handleLogout}>
                        <LogOut size={14} />
                    </button>
                </div>
            </nav>

            {/* Main content */}
            <div className="main-content">
                <div className="page-header">
                    <h1 className="page-title">
                        <Monitor size={24} /> Monitor: {name}
                    </h1>
                    <span className={`badge ${server.status === 'running' ? 'badge-green' : ''}`}>
                        {server.status.toUpperCase()}
                    </span>
                </div>

                {/* GUI iframe */}
                <div className="card" style={{ padding: 0, overflow: 'hidden', marginBottom: 24 }}>
                    <iframe
                        src={guiUrl}
                        style={{ width: '100%', height: 550, border: 'none', background: '#111' }}
                        title={`WPEX ${name} GUI`}
                    />
                </div>

                {/* Controls row */}
                <div className="grid-2">
                    {/* Key Management */}
                    <div className="card">
                        <div className="collapsible-header" onClick={() => setShowKeys(!showKeys)}>
                            <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <Key size={16} /> Chiavi Autorizzate ({server.keys.length})
                            </span>
                            {showKeys ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        </div>
                        <div className={`collapsible-content ${showKeys ? 'open' : ''}`}>
                            <div className="checkbox-list">
                                {allKeys.map(k => (
                                    <label key={k.id} className="checkbox-item" style={{ opacity: canMutate ? 1 : 0.7 }}>
                                        <input
                                            type="checkbox"
                                            checked={server.keys.some(sk => sk.id === k.id)}
                                            onChange={e => handleUpdateKeys(k.id, e.target.checked)}
                                            disabled={!canMutate}
                                        />
                                        {k.alias} {server.keys.some(sk => sk.id === k.id) && !canMutate && '(Attiva)'}
                                    </label>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Logs */}
                    <div className="card">
                        <div className="collapsible-header" onClick={toggleLogs}>
                            <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <Settings size={16} /> Logs
                            </span>
                            {showLogs ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        </div>
                        {showLogs && <div className="code-block">{logs}</div>}
                    </div>
                </div>
            </div>
        </div>
    );
}
