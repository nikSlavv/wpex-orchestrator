import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import { api } from '../api';
import {
    Server, RefreshCw, Play, Square, Trash2, Plus, Activity,
    Wifi, ArrowUpRight, ChevronRight, Search
} from 'lucide-react';

export default function NetworkView() {
    const [servers, setServers] = useState([]);
    const [kpi, setKpi] = useState(null);
    const [search, setSearch] = useState('');
    const [loading, setLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);
    const [newName, setNewName] = useState('');
    const [newPort, setNewPort] = useState('');

    const loadData = async () => {
        try {
            const [s, k] = await Promise.all([api.getServers(), api.getDashboardKPI()]);
            setServers(s.servers || []);
            setKpi(k);
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    };

    useEffect(() => { loadData(); }, []);

    const filteredServers = servers.filter(s =>
        s.name.toLowerCase().includes(search.toLowerCase())
    );

    const handleCreate = async () => {
        if (!newName.trim()) return;
        try {
            await api.createServer(newName, parseInt(newPort) || 0, []);
            setShowCreate(false);
            setNewName('');
            setNewPort('');
            loadData();
        } catch (e) { alert(e.message); }
    };

    const handleStart = async (id) => {
        try { await api.startServer(id); loadData(); } catch (e) { alert(e.message); }
    };
    const handleStop = async (id) => {
        try { await api.stopServer(id); loadData(); } catch (e) { alert(e.message); }
    };
    const handleDelete = async (id) => {
        if (!confirm('Eliminare questo relay?')) return;
        try { await api.deleteServer(id); loadData(); } catch (e) { alert(e.message); }
    };

    return (
        <div className="page">
            <Sidebar />
            <div className="main-content">
                <div className="page-header">
                    <h1 className="page-title"><Server size={26} /> Network Engineer</h1>
                    <div style={{ display: 'flex', gap: 8 }}>
                        <div style={{ position: 'relative' }}>
                            <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                            <input className="input" placeholder="Cerca relay..." value={search}
                                onChange={e => setSearch(e.target.value)}
                                style={{ paddingLeft: 36, width: 220 }} />
                        </div>
                        <button className="btn btn-primary" onClick={() => setShowCreate(!showCreate)}>
                            <Plus size={16} /> Nuovo Relay
                        </button>
                        <button className="btn btn-sm" onClick={loadData}>
                            <RefreshCw size={14} />
                        </button>
                    </div>
                </div>

                {/* Create Form */}
                {showCreate && (
                    <div className="card" style={{ marginBottom: 20, animation: 'fadeInUp 0.3s ease-out' }}>
                        <h3 className="card-title"><Plus size={18} /> Crea Nuovo Relay</h3>
                        <div className="form-row" style={{ marginTop: 12 }}>
                            <div className="form-group">
                                <label>Nome</label>
                                <input className="input" value={newName} onChange={e => setNewName(e.target.value)} placeholder="relay-eu-01" />
                            </div>
                            <div className="form-group">
                                <label>Porta UDP</label>
                                <input className="input" type="number" value={newPort} onChange={e => setNewPort(e.target.value)} placeholder="51820" />
                            </div>
                            <div className="form-group" style={{ justifyContent: 'flex-end' }}>
                                <button className="btn btn-primary" onClick={handleCreate}>Crea</button>
                            </div>
                        </div>
                    </div>
                )}

                {loading ? (
                    <div className="loading-screen"><div className="spinner" /></div>
                ) : (
                    <div className="card">
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Relay</th>
                                    <th>Status</th>
                                    <th>Porta UDP</th>
                                    <th>Web Port</th>
                                    <th>Health</th>
                                    <th>Peers</th>
                                    <th>Azioni</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredServers.map(s => {
                                    const relayKpi = kpi?.relays?.find(r => r.name === s.name);
                                    return (
                                        <tr key={s.id}>
                                            <td>
                                                <Link to={`/relays/${s.id}`} style={{ color: 'var(--accent-purple-light)', textDecoration: 'none', fontWeight: 600 }}>
                                                    {s.name}
                                                </Link>
                                            </td>
                                            <td>
                                                <span className="badge badge-green" style={
                                                    s.status === 'running' ? {} :
                                                        s.status === 'exited' ? { background: 'rgba(248,113,113,0.12)', color: 'var(--accent-red)', borderColor: 'rgba(248,113,113,0.2)' } :
                                                            { background: 'rgba(251,191,36,0.12)', color: 'var(--accent-amber)', borderColor: 'rgba(251,191,36,0.2)' }
                                                }>
                                                    <span className={`status-dot ${s.status || 'not_created'}`} /> {s.status || 'N/A'}
                                                </span>
                                            </td>
                                            <td>{s.port}</td>
                                            <td>{s.web_port}</td>
                                            <td>
                                                {relayKpi ? (
                                                    <span style={{ color: relayKpi.health >= 80 ? 'var(--accent-green)' : relayKpi.health >= 50 ? 'var(--accent-amber)' : 'var(--accent-red)', fontWeight: 600 }}>
                                                        {relayKpi.health}%
                                                    </span>
                                                ) : '—'}
                                            </td>
                                            <td>{relayKpi ? relayKpi.peers_count : '—'}</td>
                                            <td>
                                                <div style={{ display: 'flex', gap: 4 }}>
                                                    {s.status !== 'running' && (
                                                        <button className="btn btn-sm" onClick={() => handleStart(s.id)} title="Avvia">
                                                            <Play size={12} />
                                                        </button>
                                                    )}
                                                    {s.status === 'running' && (
                                                        <button className="btn btn-sm" onClick={() => handleStop(s.id)} title="Ferma">
                                                            <Square size={12} />
                                                        </button>
                                                    )}
                                                    <Link to={`/relays/${s.id}`} className="btn btn-sm" title="Dettagli">
                                                        <ChevronRight size={12} />
                                                    </Link>
                                                    <button className="btn btn-sm btn-danger" onClick={() => handleDelete(s.id)} title="Elimina">
                                                        <Trash2 size={12} />
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                        {filteredServers.length === 0 && (
                            <div className="empty-state">
                                <Server size={48} />
                                <h3>Nessun relay trovato</h3>
                                <p>Crea il tuo primo relay per iniziare</p>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
