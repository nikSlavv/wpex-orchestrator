import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import { api } from '../api';
import {
    Server, RefreshCw, Play, Square, Trash2, Plus, Activity,
    Wifi, ArrowUpRight, ChevronRight, Search, Key
} from 'lucide-react';
import { useAuth } from '../AuthContext';

export default function NetworkView() {
    const { user } = useAuth();
    const canMutate = !['viewer', 'executive'].includes(user?.role);
    const [servers, setServers] = useState([]);
    const [kpi, setKpi] = useState(null);
    const [search, setSearch] = useState('');
    const [loading, setLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);
    const [newName, setNewName] = useState('');
    const [newPort, setNewPort] = useState('');
    const [availableKeys, setAvailableKeys] = useState([]);
    const [selectedKeyIds, setSelectedKeyIds] = useState([]);
    const [tenants, setTenants] = useState([]);
    const [selectedTenant, setSelectedTenant] = useState('');

    const loadData = async () => {
        try {
            const [s, k, keys, tList] = await Promise.all([
                api.getServers(),
                api.getDashboardKPI(),
                api.getKeys().catch(() => ({ keys: [] })),
                user?.role === 'admin' ? api.getTenants() : Promise.resolve([])
            ]);
            setServers(s.servers || []);
            setKpi(k);
            setAvailableKeys(keys.keys || keys || []);
            if (user?.role === 'admin') setTenants(tList.tenants || tList || []);
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    };

    useEffect(() => { loadData(); }, []);

    const filteredServers = servers.filter(s =>
        s.name.toLowerCase().includes(search.toLowerCase())
    );

    const toggleKey = (keyId) => {
        setSelectedKeyIds(prev =>
            prev.includes(keyId) ? prev.filter(id => id !== keyId) : [...prev, keyId]
        );
    };

    const handleCreate = async () => {
        if (!newName.trim()) return;
        const tenantIdToSend = user?.role === 'admin' ? selectedTenant || null : user?.tenant_id;
        try {
            await api.createServer(newName, parseInt(newPort) || 0, selectedKeyIds, tenantIdToSend);
            setShowCreate(false);
            setNewName('');
            setNewPort('');
            setSelectedKeyIds([]);
            setSelectedTenant('');
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
                        {canMutate && (
                            <button className="btn btn-primary" onClick={() => setShowCreate(!showCreate)}>
                                <Plus size={16} /> Nuovo Relay
                            </button>
                        )}
                        <button className="btn btn-sm" onClick={loadData}>
                            <RefreshCw size={14} />
                        </button>
                    </div>
                </div>

                {/* Create Form */}
                {showCreate && canMutate && (
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
                        </div>
                        <div style={{ marginTop: 12 }}>
                            <label style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8, fontSize: '0.88rem', fontWeight: 600 }}>
                                <Key size={14} /> Chiavi Autorizzate
                            </label>
                            {availableKeys.length === 0 ? (
                                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', margin: 0 }}>
                                    Nessuna chiave disponibile — creale dalla pagina <Link to="/keys" style={{ color: 'var(--accent-purple-light)' }}>Chiavi</Link>
                                </p>
                            ) : (
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                                    {availableKeys.map(k => (
                                        <div key={k.id} onClick={() => toggleKey(k.id)}
                                            style={{
                                                display: 'flex', alignItems: 'center', gap: 6,
                                                padding: '6px 12px', borderRadius: 8, cursor: 'pointer',
                                                fontSize: '0.84rem', fontWeight: 500, transition: 'all 0.2s',
                                                background: selectedKeyIds.includes(k.id)
                                                    ? 'rgba(124,106,239,0.2)' : 'rgba(255,255,255,0.04)',
                                                border: `1px solid ${selectedKeyIds.includes(k.id)
                                                    ? 'rgba(124,106,239,0.5)' : 'rgba(255,255,255,0.08)'}`,
                                                color: selectedKeyIds.includes(k.id) ? '#9b8afb' : 'var(--text-secondary)',
                                                userSelect: 'none',
                                            }}>
                                            <Key size={12} />
                                            {k.alias || k.name || k.label || `Chiave #${k.id}`}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                        {user?.role === 'admin' && (
                            <div className="form-group" style={{ marginTop: 16 }}>
                                <label>Tenant Proprietario (Opzionale)</label>
                                <select className="input" value={selectedTenant} onChange={e => setSelectedTenant(e.target.value)}>
                                    <option value="">Nessuno (Globale)</option>
                                    {tenants.map(t => (
                                        <option key={t.id} value={t.id}>{t.name}</option>
                                    ))}
                                </select>
                            </div>
                        )}
                        <div style={{ marginTop: 16, display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                            <button className="btn btn-secondary" onClick={() => { setShowCreate(false); setSelectedKeyIds([]); setSelectedTenant(''); }}>Annulla</button>
                            <button className="btn btn-primary" onClick={handleCreate}>
                                <Plus size={14} /> Crea Relay
                            </button>
                        </div>
                    </div>
                )}

                {loading ? (
                    <div className="loading-screen"><div className="spinner" /></div>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
                        {(() => {
                            if (user?.role !== 'admin') {
                                return renderServerTable(filteredServers, kpi, canMutate, handleStart, handleStop, handleDelete);
                            }

                            // Group filteredServers by tenant_id for Admin
                            const groupedServers = filteredServers.reduce((acc, s) => {
                                const tId = s.tenant_id || 0;
                                if (!acc[tId]) acc[tId] = [];
                                acc[tId].push(s);
                                return acc;
                            }, {});

                            return Object.keys(groupedServers).map(tId => {
                                const gServers = groupedServers[tId];
                                const tName = tId == 0 ? "Globale / Nessun Tenant" : (tenants.find(t => t.id == tId)?.name || `Tenant #${tId}`);
                                return (
                                    <div key={tId} className="card">
                                        <h3 className="card-title" style={{ marginBottom: 16 }}>{tName}</h3>
                                        {renderServerTable(gServers, kpi, canMutate, handleStart, handleStop, handleDelete)}
                                    </div>
                                );
                            });
                        })()}

                        {filteredServers.length === 0 && (
                            <div className="empty-state card">
                                <Server size={48} />
                                <h3>Nessun relay trovato</h3>
                                <p>Nessun relay corrisponde ai criteri di ricerca attuali.</p>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}

function renderServerTable(servers, kpi, canMutate, handleStart, handleStop, handleDelete) {
    if (servers.length === 0) return <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Nessun relay in questa organizzazione.</p>;
    return (
        <table className="data-table">
            <thead>
                <tr>
                    <th style={{ width: '25%' }}>Relay</th>
                    <th style={{ width: '15%' }}>Status</th>
                    <th style={{ width: '15%' }}>Porta UDP</th>
                    <th style={{ width: '10%' }}>Health</th>
                    <th style={{ width: '10%' }}>Peers</th>
                    <th style={{ width: '25%' }}>Azioni</th>
                </tr>
            </thead>
            <tbody>
                {servers.map(s => {
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
                            <td>{s.udp_port}</td>
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
                                    {canMutate && s.status !== 'running' && (
                                        <button className="btn btn-sm" onClick={() => handleStart(s.id)} title="Avvia">
                                            <Play size={12} />
                                        </button>
                                    )}
                                    {canMutate && s.status === 'running' && (
                                        <button className="btn btn-sm" onClick={() => handleStop(s.id)} title="Ferma">
                                            <Square size={12} />
                                        </button>
                                    )}
                                    <Link to={`/relays/${s.id}`} className="btn btn-sm" title="Dettagli">
                                        <ChevronRight size={12} />
                                    </Link>
                                    {canMutate && (
                                        <button className="btn btn-sm btn-danger" onClick={() => handleDelete(s.id)} title="Elimina">
                                            <Trash2 size={12} />
                                        </button>
                                    )}
                                </div>
                            </td>
                        </tr>
                    );
                })}
            </tbody>
        </table>
    );
}
