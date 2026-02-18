import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { api } from '../api';
import {
    LayoutDashboard, Plus, Play, Square, Trash2, Monitor, Key,
    LogOut, User, ChevronDown, ChevronUp, Database, Server
} from 'lucide-react';

export default function Dashboard() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [tab, setTab] = useState('servers');
    const [servers, setServers] = useState([]);
    const [keys, setKeys] = useState([]);
    const [hostIp, setHostIp] = useState('');
    const [loading, setLoading] = useState(true);

    // New server form
    const [showNewServer, setShowNewServer] = useState(false);
    const [newName, setNewName] = useState('');
    const [newPort, setNewPort] = useState(40000);
    const [newKeyIds, setNewKeyIds] = useState([]);

    // New key form
    const [newAlias, setNewAlias] = useState('');
    const [newKeyVal, setNewKeyVal] = useState('');

    // Expanded states
    const [expandedKeys, setExpandedKeys] = useState({});
    const [expandedLogs, setExpandedLogs] = useState({});
    const [serverLogs, setServerLogs] = useState({});

    const refresh = useCallback(async () => {
        try {
            const [srvData, keyData] = await Promise.all([api.getServers(), api.getKeys()]);
            setServers(srvData.servers);
            setHostIp(srvData.host_ip);
            setKeys(keyData.keys);
        } catch { } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { refresh(); }, [refresh]);

    const handleCreateServer = async (e) => {
        e.preventDefault();
        if (!newName || !newKeyIds.length) return;
        try {
            await api.createServer(newName, newPort, newKeyIds);
            setNewName(''); setNewPort(40000); setNewKeyIds([]); setShowNewServer(false);
            refresh();
        } catch { }
    };

    const handleDeleteServer = async (id) => {
        if (!confirm('Eliminare questo server?')) return;
        await api.deleteServer(id);
        refresh();
    };

    const handleAction = async (id, action) => {
        if (action === 'start') await api.startServer(id);
        if (action === 'stop') await api.stopServer(id);
        refresh();
    };

    const toggleLogs = async (srv) => {
        const key = srv.id;
        if (expandedLogs[key]) {
            setExpandedLogs(p => ({ ...p, [key]: false }));
        } else {
            const data = await api.getServerLogs(key);
            setServerLogs(p => ({ ...p, [key]: data.logs }));
            setExpandedLogs(p => ({ ...p, [key]: true }));
        }
    };

    const handleUpdateKeys = async (serverId, keyIds) => {
        await api.updateServerKeys(serverId, keyIds);
        refresh();
    };

    const handleCreateKey = async (e) => {
        e.preventDefault();
        if (!newAlias || !newKeyVal) return;
        await api.createKey(newAlias, newKeyVal);
        setNewAlias(''); setNewKeyVal('');
        refresh();
    };

    const handleDeleteKey = async (id) => {
        await api.deleteKey(id);
        refresh();
    };

    const toggleKeyId = (id) => {
        setNewKeyIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
    };

    const handleLogout = async () => {
        await logout();
        navigate('/');
    };

    if (loading) return <div className="loading-screen"><div className="spinner" /></div>;

    return (
        <div className="page">
            {/* Sidebar */}
            <nav className="sidebar">
                <div className="sidebar-brand">
                    <LayoutDashboard size={22} /> WPEX Orchestrator
                </div>

                <div className="tabs" style={{ flexDirection: 'column', background: 'transparent', padding: 0 }}>
                    <button className={`tab ${tab === 'servers' ? 'active' : ''}`} onClick={() => setTab('servers')}
                        style={{ textAlign: 'left', display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Server size={16} /> Server & Istanze
                    </button>
                    <button className={`tab ${tab === 'keys' ? 'active' : ''}`} onClick={() => setTab('keys')}
                        style={{ textAlign: 'left', display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Database size={16} /> Database Chiavi
                    </button>
                </div>

                <div className="sidebar-user">
                    <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <User size={16} /> {user?.username}
                    </span>
                    <button className="btn btn-sm" onClick={handleLogout} title="Logout">
                        <LogOut size={14} />
                    </button>
                </div>
            </nav>

            {/* Main */}
            <div className="main-content">
                <div className="page-header">
                    <h1 className="page-title">
                        {tab === 'servers' ? <><Server size={24} /> Server & Istanze</> : <><Database size={24} /> Chiavi Globali</>}
                    </h1>
                    <span className="badge">Host: <code style={{ marginLeft: 4 }}>{hostIp}</code></span>
                </div>

                {/* ═══ SERVERS TAB ═══ */}
                {tab === 'servers' && (
                    <>
                        {/* New Server Expander */}
                        <div className="expander">
                            <div className="expander-header" onClick={() => setShowNewServer(!showNewServer)}>
                                <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                    <Plus size={16} /> Aggiungi Nuovo Server
                                </span>
                                {showNewServer ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                            </div>
                            {showNewServer && (
                                <div className="expander-body">
                                    <form onSubmit={handleCreateServer}>
                                        <div className="form-row">
                                            <div className="form-group">
                                                <label>Nome Server</label>
                                                <input className="input" value={newName} onChange={e => setNewName(e.target.value)} placeholder="es. alpha" />
                                            </div>
                                            <div className="form-group">
                                                <label>Porta UDP</label>
                                                <input className="input" type="number" value={newPort} onChange={e => setNewPort(+e.target.value)} />
                                            </div>
                                        </div>
                                        <div className="form-group" style={{ marginTop: 12 }}>
                                            <label>Chiavi</label>
                                            <div className="checkbox-list">
                                                {keys.length === 0 && <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Nessuna chiave — creane una prima</span>}
                                                {keys.map(k => (
                                                    <label key={k.id} className="checkbox-item">
                                                        <input type="checkbox" checked={newKeyIds.includes(k.id)} onChange={() => toggleKeyId(k.id)} />
                                                        {k.alias}
                                                    </label>
                                                ))}
                                            </div>
                                        </div>
                                        <button className="btn btn-primary" type="submit" style={{ marginTop: 12 }}>
                                            <Plus size={14} /> Crea Server
                                        </button>
                                    </form>
                                </div>
                            )}
                        </div>

                        {/* Server List */}
                        {servers.length === 0 && (
                            <div className="card" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 40 }}>
                                Nessun server attivo. Crea il primo!
                            </div>
                        )}

                        {servers.map((srv, i) => (
                            <div key={srv.id} className="card server-card" style={{ marginBottom: 16, animationDelay: `${i * 0.08}s` }}>
                                <div className="card-header">
                                    <div className="card-title">
                                        <span className={`status-dot ${srv.status}`} />
                                        wpex-{srv.name}
                                    </div>
                                    <div className="status-label" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                        <span className="badge">UDP: {srv.udp_port}</span>
                                        <span className="badge badge-blue">Web: {srv.web_port}</span>
                                    </div>
                                </div>

                                <div className="server-actions">
                                    <button className="btn btn-sm" onClick={() => handleAction(srv.id, 'start')} disabled={srv.status === 'running'}>
                                        <Play size={14} /> Start
                                    </button>
                                    <button className="btn btn-sm" onClick={() => handleAction(srv.id, 'stop')} disabled={srv.status !== 'running'}>
                                        <Square size={14} /> Stop
                                    </button>
                                    <button className="btn btn-sm" onClick={() => navigate(`/server/${srv.name}`)}>
                                        <Monitor size={14} /> Console
                                    </button>
                                    <button className="btn btn-sm btn-danger" onClick={() => handleDeleteServer(srv.id)}>
                                        <Trash2 size={14} /> Delete
                                    </button>
                                </div>

                                {/* Key Management */}
                                <div className="collapsible-header" onClick={() => setExpandedKeys(p => ({ ...p, [srv.id]: !p[srv.id] }))}>
                                    <span><Key size={14} style={{ marginRight: 6 }} /> Chiavi ({srv.keys.length})</span>
                                    {expandedKeys[srv.id] ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                                </div>
                                <div className={`collapsible-content ${expandedKeys[srv.id] ? 'open' : ''}`}>
                                    <div className="checkbox-list" style={{ marginBottom: 8 }}>
                                        {keys.map(k => (
                                            <label key={k.id} className="checkbox-item">
                                                <input
                                                    type="checkbox"
                                                    checked={srv.keys.some(sk => sk.id === k.id)}
                                                    onChange={() => {
                                                        const current = srv.keys.map(sk => sk.id);
                                                        const updated = current.includes(k.id)
                                                            ? current.filter(x => x !== k.id)
                                                            : [...current, k.id];
                                                        handleUpdateKeys(srv.id, updated);
                                                    }}
                                                />
                                                {k.alias}
                                            </label>
                                        ))}
                                    </div>
                                </div>

                                {/* Logs */}
                                <div className="collapsible-header" onClick={() => toggleLogs(srv)}>
                                    <span>Logs</span>
                                    {expandedLogs[srv.id] ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                                </div>
                                {expandedLogs[srv.id] && (
                                    <div className="code-block">{serverLogs[srv.id] || 'Caricamento...'}</div>
                                )}
                            </div>
                        ))}
                    </>
                )}

                {/* ═══ KEYS TAB ═══ */}
                {tab === 'keys' && (
                    <>
                        <div className="card" style={{ marginBottom: 24 }}>
                            <form onSubmit={handleCreateKey}>
                                <div className="form-row">
                                    <div className="form-group">
                                        <label>Nome / Alias</label>
                                        <input className="input" value={newAlias} onChange={e => setNewAlias(e.target.value)} placeholder="es. chiave-principale" />
                                    </div>
                                    <div className="form-group">
                                        <label>Chiave</label>
                                        <input className="input" type="password" value={newKeyVal} onChange={e => setNewKeyVal(e.target.value)} placeholder="Il valore della chiave" />
                                    </div>
                                </div>
                                <button className="btn btn-primary" type="submit" style={{ marginTop: 12 }}>
                                    <Plus size={14} /> Aggiungi Chiave
                                </button>
                            </form>
                        </div>

                        {keys.length === 0 && (
                            <div className="card" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 40 }}>
                                Nessuna chiave presente.
                            </div>
                        )}

                        {keys.map((k, i) => (
                            <div key={k.id} className="card" style={{ marginBottom: 12, display: 'flex', alignItems: 'center', justifyContent: 'space-between', animationDelay: `${i * 0.05}s`, animation: 'fadeInUp 0.3s ease-out both' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                    <Key size={16} style={{ color: 'var(--accent-purple-light)' }} />
                                    <strong>{k.alias}</strong>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                                    <span className="secret">{k.key}</span>
                                    <button className="btn btn-sm btn-danger" onClick={() => handleDeleteKey(k.id)}>
                                        <Trash2 size={14} />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </>
                )}
            </div>
        </div>
    );
}
