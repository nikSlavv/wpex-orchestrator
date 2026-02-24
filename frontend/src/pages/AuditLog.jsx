import { useState, useEffect } from 'react';
import Sidebar from '../components/Sidebar';
import { api } from '../api';
import { FileText, RefreshCw, Filter, ChevronLeft, ChevronRight } from 'lucide-react';

export default function AuditLog() {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [actionFilter, setActionFilter] = useState('');
    const [entityFilter, setEntityFilter] = useState('');

    const loadData = async () => {
        setLoading(true);
        try {
            const params = { page, per_page: 30 };
            if (actionFilter) params.action = actionFilter;
            if (entityFilter) params.entity_type = entityFilter;
            const data = await api.getAuditLog(params);
            setLogs(data.logs || []);
            setTotalPages(data.total_pages || 1);
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    };

    useEffect(() => { loadData(); }, [page, actionFilter, entityFilter]);

    const actionColor = (action) => {
        if (action?.includes('delete') || action?.includes('remove')) return 'var(--accent-red)';
        if (action?.includes('create') || action?.includes('add')) return 'var(--accent-green)';
        if (action?.includes('update') || action?.includes('modify')) return 'var(--accent-amber)';
        return 'var(--text-secondary)';
    };

    return (
        <div className="page">
            <Sidebar />
            <div className="main-content">
                <div className="page-header">
                    <h1 className="page-title"><FileText size={26} /> Audit Log</h1>
                    <div style={{ display: 'flex', gap: 8 }}>
                        <input className="input" placeholder="Filtra azione..." value={actionFilter}
                            onChange={e => { setActionFilter(e.target.value); setPage(1); }}
                            style={{ width: 160 }} />
                        <select className="select" value={entityFilter}
                            onChange={e => { setEntityFilter(e.target.value); setPage(1); }}>
                            <option value="">Tutte le entità</option>
                            <option value="relay">Relay</option>
                            <option value="tenant">Tenant</option>
                            <option value="site">Site</option>
                            <option value="user">User</option>
                        </select>
                        <button className="btn btn-sm" onClick={loadData}><RefreshCw size={14} /></button>
                    </div>
                </div>

                <div className="card">
                    {loading ? (
                        <div className="loading-screen" style={{ minHeight: 200 }}><div className="spinner" /></div>
                    ) : (
                        <>
                            <div className="table-responsive">
                                <table className="data-table">
                                    <thead>
                                        <tr>
                                            <th>Data</th>
                                            <th>Utente</th>
                                            <th>Azione</th>
                                            <th>Entità</th>
                                            <th>ID</th>
                                            <th>IP</th>
                                            <th>Dettagli</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {logs.map(l => (
                                            <tr key={l.id}>
                                                <td style={{ fontSize: '0.82rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                                                    {l.created_at ? new Date(l.created_at).toLocaleString('it-IT') : '—'}
                                                </td>
                                                <td style={{ fontWeight: 500 }}>{l.username || '—'}</td>
                                                <td>
                                                    <span style={{ color: actionColor(l.action), fontWeight: 500 }}>
                                                        {l.action}
                                                    </span>
                                                </td>
                                                <td><span className="badge">{l.entity_type || '—'}</span></td>
                                                <td>#{l.entity_id || '—'}</td>
                                                <td style={{ fontFamily: 'monospace', fontSize: '0.82rem' }}>{l.ip_address || '—'}</td>
                                                <td>
                                                    {l.details ? (
                                                        <details>
                                                            <summary style={{ cursor: 'pointer', fontSize: '0.82rem', color: 'var(--accent-purple-light)' }}>
                                                                Mostra
                                                            </summary>
                                                            <div className="code-block" style={{ marginTop: 4, maxHeight: 120 }}>
                                                                {JSON.stringify(l.details, null, 2)}
                                                            </div>
                                                        </details>
                                                    ) : '—'}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>

                            {logs.length === 0 && (
                                <div className="empty-state">
                                    <FileText size={48} />
                                    <h3>Nessun log</h3>
                                </div>
                            )}

                            {/* Pagination */}
                            {totalPages > 1 && (
                                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, marginTop: 16, padding: 16 }}>
                                    <button className="btn btn-sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
                                        <ChevronLeft size={14} /> Precedente
                                    </button>
                                    <span style={{ fontSize: '0.88rem', color: 'var(--text-muted)' }}>
                                        Pagina {page} di {totalPages}
                                    </span>
                                    <button className="btn btn-sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>
                                        Successiva <ChevronRight size={14} />
                                    </button>
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
