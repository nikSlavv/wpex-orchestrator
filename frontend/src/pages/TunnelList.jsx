import { useState, useEffect } from 'react';
import Sidebar from '../components/Sidebar';
import { api } from '../api';
import { Link2, Plus, Trash2, RefreshCw, Eye, ArrowRight, Info, Copy, Check } from 'lucide-react';
import { useAuth } from '../AuthContext';

export default function TunnelList() {
    const { user } = useAuth();
    const canMutate = !['viewer', 'executive'].includes(user?.role);
    const [tunnels, setTunnels] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);
    const [tenants, setTenants] = useState([]);
    const [servers, setServers] = useState([]);
    const [statusFilter, setStatusFilter] = useState('');
    const [form, setForm] = useState({ tenant_id: '', site_a_id: '', site_b_id: '', relay_id: '' });
    const [tenantSites, setTenantSites] = useState([]);
    const [viewConfig, setViewConfig] = useState(null);
    const [copiedConfig, setCopiedConfig] = useState(false);

    const loadData = async () => {
        try {
            const params = {};
            if (statusFilter) params.status = statusFilter;
            const data = await api.getTunnels(params);
            setTunnels(data.tunnels || []);
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    };

    useEffect(() => { loadData(); }, [statusFilter]);

    const loadFormData = async () => {
        const [t, s] = await Promise.all([api.getTenants(), api.getServers()]);
        setTenants(t.tenants || []);
        setServers(s.servers || []);
    };

    const handleTenantSelect = async (tenantId) => {
        setForm({ ...form, tenant_id: tenantId });
        if (tenantId) {
            const sites = await api.getSites(tenantId);
            setTenantSites(sites.sites || []);
        }
    };

    const handleCreate = async () => {
        try {
            await api.createTunnel({
                tenant_id: parseInt(form.tenant_id),
                site_a_id: parseInt(form.site_a_id),
                site_b_id: parseInt(form.site_b_id),
                relay_id: parseInt(form.relay_id),
            });
            setShowCreate(false);
            loadData();
        } catch (e) { alert(e.message); }
    };

    const handleDelete = async (id) => {
        if (!confirm('Eliminare il tunnel?')) return;
        try { await api.deleteTunnel(id); loadData(); } catch (e) { alert(e.message); }
    };

    const statusColor = (status) => {
        if (status === 'active') return 'badge-green';
        if (status === 'degraded') return '';
        return '';
    };

    const copyToClipboard = async (text) => {
        try {
            if (navigator?.clipboard?.writeText) {
                await navigator.clipboard.writeText(text);
            } else {
                const textArea = document.createElement("textarea");
                textArea.value = text;
                textArea.style.position = "fixed";
                textArea.style.left = "-999999px";
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
            }
            setCopiedConfig(true);
            setTimeout(() => setCopiedConfig(false), 2000);
        } catch (err) {
            alert("Impossibile copiare il testo, selezionalo manualmente.");
        }
    };

    return (
        <div className="page">
            <Sidebar />
            <div className="main-content">
                <div className="page-header">
                    <h1 className="page-title"><Link2 size={26} /> P2P Routing</h1>
                    <div style={{ display: 'flex', gap: 8 }}>
                        <select className="select" style={{ width: 140 }} value={statusFilter}
                            onChange={e => setStatusFilter(e.target.value)}>
                            <option value="">Tutti</option>
                            <option value="active">Attivi</option>
                            <option value="pending">Pending</option>
                            <option value="down">Down</option>
                        </select>
                        {canMutate && (
                            <button className="btn btn-primary" onClick={() => { setShowCreate(!showCreate); if (!showCreate) loadFormData(); }}>
                                <Plus size={16} /> Nuovo Tunnel
                            </button>
                        )}
                        <button className="btn btn-sm" onClick={loadData}><RefreshCw size={14} /></button>
                    </div>
                </div>

                <div className="card" style={{ marginBottom: 20, backgroundColor: 'rgba(52, 211, 153, 0.05)', borderColor: 'var(--accent-green)', padding: 16 }}>
                    <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                        <Info size={20} color="var(--accent-green)" style={{ flexShrink: 0, marginTop: 2 }} />
                        <div>
                            <h4 style={{ margin: '0 0 6px 0', color: 'var(--text-primary)', fontSize: '0.95rem' }}>Mappatura Organica (AllowedIPs)</h4>
                            <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.85rem', lineHeight: 1.5 }}>
                                I tunnel WPEX sono astrazioni logiche. WPEX non inietta regole di blocco traffico centralizzate sul Relay (il traffico è ruotato liberamente tra peer validi).
                                Crea un "Tunnel P2P" per documentare il collegamento tra due sedi e generare automaticamente lo script di configurazione <code>JSON / AllowedIPs</code> da caricare sui rispettivi router Mikrotik Edge.
                            </p>
                        </div>
                    </div>
                </div>

                {showCreate && canMutate && (
                    <div className="card" style={{ marginBottom: 20 }}>
                        <h3 className="card-title"><Plus size={18} /> Crea Tunnel</h3>
                        <div className="form-row" style={{ marginTop: 12 }}>
                            <div className="form-group">
                                <label>Tenant</label>
                                <select className="select" value={form.tenant_id} onChange={e => handleTenantSelect(e.target.value)}>
                                    <option value="">Seleziona...</option>
                                    {tenants.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                                </select>
                            </div>
                            <div className="form-group">
                                <label>Relay</label>
                                <select className="select" value={form.relay_id} onChange={e => setForm({ ...form, relay_id: e.target.value })}>
                                    <option value="">Seleziona...</option>
                                    {servers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                                </select>
                            </div>
                        </div>
                        <div className="form-row" style={{ marginTop: 12 }}>
                            <div className="form-group">
                                <label>Site A</label>
                                <select className="select" value={form.site_a_id} onChange={e => setForm({ ...form, site_a_id: e.target.value })}>
                                    <option value="">Seleziona...</option>
                                    {tenantSites.map(s => <option key={s.id} value={s.id}>{s.name} ({s.region})</option>)}
                                </select>
                            </div>
                            <div className="form-group">
                                <label>Site B</label>
                                <select className="select" value={form.site_b_id} onChange={e => setForm({ ...form, site_b_id: e.target.value })}>
                                    <option value="">Seleziona...</option>
                                    {tenantSites.filter(s => s.id !== parseInt(form.site_a_id)).map(s => <option key={s.id} value={s.id}>{s.name} ({s.region})</option>)}
                                </select>
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
                                    <th>ID</th>
                                    <th>Tenant</th>
                                    <th>Site A</th>
                                    <th></th>
                                    <th>Site B</th>
                                    <th>Relay</th>
                                    <th>Status</th>
                                    <th>Versione</th>
                                    <th></th>
                                </tr>
                            </thead>
                            <tbody>
                                {tunnels.map(t => (
                                    <tr key={t.id}>
                                        <td>#{t.id}</td>
                                        <td>{t.tenant || '—'}</td>
                                        <td>
                                            <div style={{ fontWeight: 500 }}>{t.site_a?.name}</div>
                                            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{t.site_a?.region}</div>
                                        </td>
                                        <td><ArrowRight size={14} style={{ color: 'var(--text-muted)' }} /></td>
                                        <td>
                                            <div style={{ fontWeight: 500 }}>{t.site_b?.name}</div>
                                            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{t.site_b?.region}</div>
                                        </td>
                                        <td>{t.relay || '—'}</td>
                                        <td><span className={`badge ${statusColor(t.status)}`}>{t.status}</span></td>
                                        <td>v{t.config_version}</td>
                                        <td>
                                            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                                                <button className="btn btn-sm btn-secondary" onClick={() => setViewConfig(t)} title="Visualizza Script Configurazione">
                                                    <Eye size={12} style={{ marginRight: 4 }} /> Payload JSON
                                                </button>
                                                {canMutate && (
                                                    <button className="btn btn-sm btn-danger" onClick={() => handleDelete(t.id)}>
                                                        <Trash2 size={12} />
                                                    </button>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        {tunnels.length === 0 && (
                            <div className="empty-state">
                                <Link2 size={48} />
                                <h3>Nessuna rotta P2P configurata</h3>
                                <p>Crea regole di instradamento per generare i configuration payload dei Mikrotik</p>
                            </div>
                        )}
                    </div>
                )}
                {viewConfig && (
                    <div style={{
                        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                        backgroundColor: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(2px)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
                    }}>
                        <div className="card" style={{ width: 600, maxWidth: '90%', maxHeight: '85vh', display: 'flex', flexDirection: 'column' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                                <div>
                                    <h3 style={{ margin: 0, fontSize: '1.2rem' }}>Configurazione di Instradamento </h3>
                                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 4 }}>
                                        {viewConfig.site_a?.name} &harr; {viewConfig.site_b?.name} (Relay: {viewConfig.relay})
                                    </div>
                                </div>
                                <div style={{ display: 'flex', gap: 8 }}>
                                    <button
                                        className={`btn btn-sm ${copiedConfig ? 'btn-success' : 'btn-secondary'}`}
                                        onClick={() => copyToClipboard(JSON.stringify(viewConfig.config, null, 2))}
                                    >
                                        {copiedConfig ? <Check size={14} /> : <Copy size={14} />}
                                        {copiedConfig ? 'Copiato!' : 'Copia'}
                                    </button>
                                    <button className="btn btn-sm" onClick={() => setViewConfig(null)}>Chiudi</button>
                                </div>
                            </div>
                            <div style={{
                                backgroundColor: '#1e1e1e', color: '#d4d4d4',
                                padding: 16, borderRadius: 6, overflowY: 'auto', flex: 1,
                                fontSize: '0.85rem', fontFamily: 'monospace', whiteSpace: 'pre-wrap'
                            }}>
                                {JSON.stringify(viewConfig.config, null, 2)}
                            </div>
                            <div style={{ marginTop: 12, fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
                                <Info size={14} />
                                Incolla le subnet e le chiavi pubbliche mostrate qui sopra nei rispettivi router di Sede.
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
