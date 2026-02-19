import { useState, useEffect } from 'react';
import Sidebar from '../components/Sidebar';
import { api } from '../api';
import {
    Users, Plus, Trash2, RefreshCw, Settings, ChevronDown, ChevronRight,
    MapPin, Link2, AlertTriangle
} from 'lucide-react';

export default function TenantsPage() {
    const [tenants, setTenants] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);
    const [expanded, setExpanded] = useState(null);
    const [tenantDetail, setTenantDetail] = useState(null);
    const [form, setForm] = useState({ name: '', slug: '', max_tunnels: 10, max_bandwidth_mbps: 100 });
    const [siteForm, setSiteForm] = useState({ name: '', region: '', public_ip: '', subnet: '' });
    const [showSiteCreate, setShowSiteCreate] = useState(null);

    const loadData = async () => {
        try {
            const data = await api.getTenants();
            setTenants(data.tenants || []);
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    };

    useEffect(() => { loadData(); }, []);

    const handleCreate = async () => {
        try {
            await api.createTenant(form);
            setShowCreate(false);
            setForm({ name: '', slug: '', max_tunnels: 10, max_bandwidth_mbps: 100 });
            loadData();
        } catch (e) { alert(e.message); }
    };

    const handleDelete = async (id) => {
        if (!confirm('Eliminare questo tenant e tutti i dati associati?')) return;
        try { await api.deleteTenant(id); loadData(); } catch (e) { alert(e.message); }
    };

    const handleExpand = async (id) => {
        if (expanded === id) { setExpanded(null); return; }
        try {
            const data = await api.getTenant(id);
            setTenantDetail(data);
            setExpanded(id);
        } catch (e) { console.error(e); }
    };

    const handleCreateSite = async (tenantId) => {
        try {
            await api.createSite(tenantId, siteForm);
            setSiteForm({ name: '', region: '', public_ip: '', subnet: '' });
            setShowSiteCreate(null);
            handleExpand(tenantId);
            loadData();
        } catch (e) { alert(e.message); }
    };

    const handleDeleteSite = async (tenantId, siteId) => {
        try { await api.deleteSite(tenantId, siteId); handleExpand(tenantId); loadData(); } catch (e) { alert(e.message); }
    };

    return (
        <div className="page">
            <Sidebar />
            <div className="main-content">
                <div className="page-header">
                    <h1 className="page-title"><Users size={26} /> Tenant Management</h1>
                    <div style={{ display: 'flex', gap: 8 }}>
                        <button className="btn btn-primary" onClick={() => setShowCreate(!showCreate)}>
                            <Plus size={16} /> Nuovo Tenant
                        </button>
                        <button className="btn btn-sm" onClick={loadData}><RefreshCw size={14} /></button>
                    </div>
                </div>

                {showCreate && (
                    <div className="card" style={{ marginBottom: 20 }}>
                        <h3 className="card-title"><Plus size={18} /> Crea Tenant</h3>
                        <div className="form-row" style={{ marginTop: 12 }}>
                            <div className="form-group">
                                <label>Nome</label>
                                <input className="input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Acme Corp" />
                            </div>
                            <div className="form-group">
                                <label>Slug</label>
                                <input className="input" value={form.slug} onChange={e => setForm({ ...form, slug: e.target.value })} placeholder="acme-corp" />
                            </div>
                        </div>
                        <div className="form-row" style={{ marginTop: 12 }}>
                            <div className="form-group">
                                <label>Max Tunnel</label>
                                <input className="input" type="number" value={form.max_tunnels} onChange={e => setForm({ ...form, max_tunnels: parseInt(e.target.value) })} />
                            </div>
                            <div className="form-group">
                                <label>Max Bandwidth (Mbps)</label>
                                <input className="input" type="number" value={form.max_bandwidth_mbps} onChange={e => setForm({ ...form, max_bandwidth_mbps: parseInt(e.target.value) })} />
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
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                        {tenants.map(t => (
                            <div key={t.id} className="expander">
                                <div className="expander-header" onClick={() => handleExpand(t.id)}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                        {expanded === t.id ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                                        <span style={{ fontWeight: 600 }}>{t.name}</span>
                                        <span className="badge">{t.slug}</span>
                                        {!t.is_active && <span className="badge" style={{ background: 'rgba(248,113,113,0.12)', color: 'var(--accent-red)' }}>Inattivo</span>}
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                                        <div style={{ textAlign: 'right' }}>
                                            <div style={{ fontSize: '0.82rem' }}>
                                                <Link2 size={12} style={{ marginRight: 4 }} /> {t.tunnel_count}/{t.max_tunnels} tunnel
                                            </div>
                                            <div className="progress-bar" style={{ width: 80, marginTop: 4 }}>
                                                <div className={`progress-fill ${t.tunnel_usage_pct >= 80 ? 'red' : t.tunnel_usage_pct >= 50 ? 'amber' : 'green'}`}
                                                    style={{ width: `${t.tunnel_usage_pct}%` }} />
                                            </div>
                                        </div>
                                        <div style={{ fontSize: '0.82rem' }}>
                                            <MapPin size={12} style={{ marginRight: 4 }} /> {t.site_count} siti
                                        </div>
                                        <button className="btn btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); handleDelete(t.id); }}>
                                            <Trash2 size={12} />
                                        </button>
                                    </div>
                                </div>

                                {expanded === t.id && tenantDetail && (
                                    <div className="expander-body">
                                        <div className="grid-2" style={{ marginBottom: 16 }}>
                                            <div>
                                                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>API Key</div>
                                                <span className="secret">{tenantDetail.api_key || 'N/A'}</span>
                                            </div>
                                            <div>
                                                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>SLA Target</div>
                                                <div>{tenantDetail.sla_target}%</div>
                                            </div>
                                        </div>

                                        {/* Usage */}
                                        <div className="section-header">
                                            <h4 className="section-title"><AlertTriangle size={16} /> Utilizzo Risorse</h4>
                                        </div>
                                        <div className="kpi-grid" style={{ marginBottom: 16 }}>
                                            <div className="kpi-card">
                                                <div className="kpi-label">Tunnel</div>
                                                <div className="kpi-value">{tenantDetail.usage?.tunnels_used}/{tenantDetail.usage?.tunnels_limit}</div>
                                                <div className="progress-bar" style={{ marginTop: 8 }}>
                                                    <div className={`progress-fill ${tenantDetail.usage?.tunnels_pct >= 80 ? 'red' : 'green'}`}
                                                        style={{ width: `${tenantDetail.usage?.tunnels_pct || 0}%` }} />
                                                </div>
                                            </div>
                                            <div className="kpi-card">
                                                <div className="kpi-label">Siti</div>
                                                <div className="kpi-value blue">{tenantDetail.usage?.sites_count || 0}</div>
                                            </div>
                                        </div>

                                        {/* Sites */}
                                        <div className="section-header">
                                            <h4 className="section-title"><MapPin size={16} /> Siti</h4>
                                            <button className="btn btn-sm" onClick={() => setShowSiteCreate(showSiteCreate === t.id ? null : t.id)}>
                                                <Plus size={14} /> Aggiungi Site
                                            </button>
                                        </div>

                                        {showSiteCreate === t.id && (
                                            <div className="card" style={{ marginBottom: 12 }}>
                                                <div className="form-row">
                                                    <div className="form-group">
                                                        <label>Nome</label>
                                                        <input className="input" value={siteForm.name} onChange={e => setSiteForm({ ...siteForm, name: e.target.value })} placeholder="Milano HQ" />
                                                    </div>
                                                    <div className="form-group">
                                                        <label>Regione</label>
                                                        <input className="input" value={siteForm.region} onChange={e => setSiteForm({ ...siteForm, region: e.target.value })} placeholder="eu-south-1" />
                                                    </div>
                                                    <div className="form-group">
                                                        <label>IP Pubblico</label>
                                                        <input className="input" value={siteForm.public_ip} onChange={e => setSiteForm({ ...siteForm, public_ip: e.target.value })} placeholder="1.2.3.4" />
                                                    </div>
                                                    <div className="form-group" style={{ justifyContent: 'flex-end' }}>
                                                        <button className="btn btn-primary btn-sm" onClick={() => handleCreateSite(t.id)}>Crea</button>
                                                    </div>
                                                </div>
                                            </div>
                                        )}

                                        {tenantDetail.sites?.length > 0 ? (
                                            <table className="data-table">
                                                <thead>
                                                    <tr>
                                                        <th>Nome</th><th>Regione</th><th>IP</th><th>Subnet</th><th></th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {tenantDetail.sites.map(s => (
                                                        <tr key={s.id}>
                                                            <td style={{ fontWeight: 600 }}>{s.name}</td>
                                                            <td>{s.region || '—'}</td>
                                                            <td><code>{s.public_ip || '—'}</code></td>
                                                            <td><code>{s.subnet || '—'}</code></td>
                                                            <td>
                                                                <button className="btn btn-sm btn-danger" onClick={() => handleDeleteSite(t.id, s.id)}>
                                                                    <Trash2 size={12} />
                                                                </button>
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        ) : (
                                            <div className="empty-state" style={{ padding: 16 }}>
                                                <p>Nessun site configurato</p>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        ))}

                        {tenants.length === 0 && (
                            <div className="empty-state">
                                <Users size={48} />
                                <h3>Nessun Tenant</h3>
                                <p>Crea il primo tenant per iniziare</p>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
