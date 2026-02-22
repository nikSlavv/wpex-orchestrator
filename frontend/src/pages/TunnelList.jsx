import { useState, useEffect } from 'react';
import Sidebar from '../components/Sidebar';
import { api } from '../api';
import { Link2, Plus, Trash2, RefreshCw, Filter, Settings, ArrowRight } from 'lucide-react';
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

    return (
        <div className="page">
            <Sidebar />
            <div className="main-content">
                <div className="page-header">
                    <h1 className="page-title"><Link2 size={26} /> Tunnels</h1>
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
                                            <div style={{ display: 'flex', gap: 4 }}>
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
                                <h3>Nessun tunnel</h3>
                                <p>Crea tunnel tra siti di un tenant</p>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
