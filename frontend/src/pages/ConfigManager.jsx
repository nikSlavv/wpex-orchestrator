import { useState, useEffect } from 'react';
import Sidebar from '../components/Sidebar';
import { api } from '../api';
import { Settings, History, RotateCcw, RefreshCw, ChevronDown, ChevronRight } from 'lucide-react';

export default function ConfigManager() {
    const [tunnels, setTunnels] = useState([]);
    const [loading, setLoading] = useState(true);
    const [expanded, setExpanded] = useState(null);
    const [history, setHistory] = useState([]);

    const loadData = async () => {
        try {
            const data = await api.getTunnels();
            setTunnels(data.tunnels || []);
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    };

    useEffect(() => { loadData(); }, []);

    const loadHistory = async (tunnelId) => {
        if (expanded === tunnelId) { setExpanded(null); return; }
        try {
            const data = await api.getConfigHistory(tunnelId);
            setHistory(data.versions || []);
            setExpanded(tunnelId);
        } catch (e) { console.error(e); }
    };

    const handleRollback = async (tunnelId, version) => {
        if (!confirm(`Rollback alla versione ${version}?`)) return;
        try {
            await api.rollbackConfig(tunnelId, version);
            loadHistory(tunnelId);
            loadData();
        } catch (e) { alert(e.message); }
    };

    return (
        <div className="page">
            <Sidebar />
            <div className="main-content">
                <div className="page-header">
                    <h1 className="page-title"><Settings size={26} /> Config Manager</h1>
                    <button className="btn btn-sm" onClick={loadData}><RefreshCw size={14} /></button>
                </div>

                {loading ? (
                    <div className="loading-screen"><div className="spinner" /></div>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                        {tunnels.map(t => (
                            <div key={t.id} className="expander">
                                <div className="expander-header" onClick={() => loadHistory(t.id)}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                        {expanded === t.id ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                                        <span style={{ fontWeight: 600 }}>Tunnel #{t.id}</span>
                                        <span className="badge">{t.site_a?.name} → {t.site_b?.name}</span>
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                        <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>v{t.config_version}</span>
                                        <span className={`badge ${t.status === 'active' ? 'badge-green' : ''}`}>{t.status}</span>
                                    </div>
                                </div>

                                {expanded === t.id && (
                                    <div className="expander-body">
                                        <h4 className="section-title" style={{ marginTop: 0, marginBottom: 12 }}>
                                            <History size={16} /> Storico Configurazioni
                                        </h4>
                                        {history.length > 0 ? (
                                            <table className="data-table">
                                                <thead>
                                                    <tr>
                                                        <th>Versione</th><th>Creata da</th><th>Data</th><th>Diff</th><th></th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {history.map(v => (
                                                        <tr key={v.id}>
                                                            <td><span className="badge">v{v.version}</span></td>
                                                            <td>{v.created_by || '—'}</td>
                                                            <td style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                                                                {v.created_at ? new Date(v.created_at).toLocaleString('it-IT') : '—'}
                                                            </td>
                                                            <td>
                                                                {v.diff ? (
                                                                    <details>
                                                                        <summary style={{ cursor: 'pointer', fontSize: '0.82rem', color: 'var(--accent-purple-light)' }}>
                                                                            Mostra diff
                                                                        </summary>
                                                                        <div className="config-diff" style={{ marginTop: 8, maxHeight: 200, overflowY: 'auto' }}>
                                                                            <pre style={{ margin: 0 }}>{JSON.stringify(v.diff, null, 2)}</pre>
                                                                        </div>
                                                                    </details>
                                                                ) : '—'}
                                                            </td>
                                                            <td>
                                                                {v.version < (history[0]?.version || 1) && (
                                                                    <button className="btn btn-sm" onClick={() => handleRollback(t.id, v.version)}
                                                                        title={`Rollback a v${v.version}`}>
                                                                        <RotateCcw size={12} /> Rollback
                                                                    </button>
                                                                )}
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        ) : (
                                            <div className="empty-state" style={{ padding: 16 }}>
                                                <p>Nessuna versione precedente</p>
                                            </div>
                                        )}

                                        {/* Current Config */}
                                        <h4 className="section-title" style={{ marginBottom: 8 }}>
                                            <Settings size={16} /> Config Attuale
                                        </h4>
                                        <div className="config-diff">
                                            <pre style={{ margin: 0 }}>
                                                {history.length > 0 ? JSON.stringify(history[0]?.config || {}, null, 2) : '{}'}
                                            </pre>
                                        </div>
                                    </div>
                                )}
                            </div>
                        ))}

                        {tunnels.length === 0 && (
                            <div className="empty-state">
                                <Settings size={48} />
                                <h3>Nessuna configurazione</h3>
                                <p>Crea tunnel per gestire le configurazioni</p>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
