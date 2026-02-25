import { useState, useEffect } from 'react';
import Sidebar from '../components/Sidebar';
import { api } from '../api';
import {
    Users, Plus, Trash2, RefreshCw, Settings, ChevronDown, ChevronRight,
    MapPin, Link2, AlertTriangle, Key
} from 'lucide-react';
import { useAuth } from '../AuthContext';
import { useDialog } from '../contexts/DialogContext';

export default function TenantsPage() {
    const { user } = useAuth();
    const { alert, confirm, prompt } = useDialog();
    const isAdmin = user?.role === 'admin';
    const canManageSites = !['viewer', 'executive'].includes(user?.role);
    const [tenants, setTenants] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);
    const [expanded, setExpanded] = useState(null);
    const [tenantDetail, setTenantDetail] = useState(null);
    const [form, setForm] = useState({ name: '', slug: '', max_bandwidth_mbps: 100 });
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
            setForm({ name: '', slug: '', max_bandwidth_mbps: 100 });
            loadData();
        } catch (e) { alert(e.message, { title: 'Errore Creazione' }); }
    };

    const handleDelete = async (id) => {
        const ok = await confirm('Eliminare questo tenant e tutti i dati associati?', { danger: true });
        if (!ok) return;
        try { await api.deleteTenant(id); loadData(); } catch (e) { alert(e.message); }
    };

    const handleApprove = async (id) => {
        const ok = await confirm('Approvare questo tenant e attivarlo?');
        if (!ok) return;
        try { await api.updateTenantStatus(id, 'active'); loadData(); } catch (e) { alert(e.message); }
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
        } catch (e) { alert(e.message, { title: 'Errore' }); }
    };

    const handleDeleteSite = async (tenantId, siteId) => {
        try { await api.deleteSite(tenantId, siteId); handleExpand(tenantId); loadData(); } catch (e) { alert(e.message); }
    };

    const handleSetSlug = async (id, currentName) => {
        const newSlug = await prompt(`Inserisci lo slug per ${currentName}:`, {
            title: 'Imposta Slug',
            placeholder: 'es: nome-azienda'
        });
        if (newSlug) {
            try {
                await api.updateTenant(id, { slug: newSlug });
                loadData();
            } catch (e) {
                alert(e.message, { title: 'Errore' });
            }
        }
    };

    return (
        <div className="page">
            <Sidebar />
            <div className="main-content">
                <div className="page-header">
                    <h1 className="page-title"><Users size={26} /> Tenant Management</h1>
                    <div style={{ display: 'flex', gap: 8 }}>
                        {isAdmin && (
                            <button className="btn btn-primary" onClick={() => setShowCreate(!showCreate)}>
                                <Plus size={16} /> Nuovo Tenant
                            </button>
                        )}
                        <button className="btn btn-sm" onClick={loadData}><RefreshCw size={14} /></button>
                    </div>
                </div>

                {showCreate && isAdmin && (
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
                                        {t.slug ? (
                                            <span className="badge">{t.slug}</span>
                                        ) : (
                                            isAdmin && <button className="btn btn-sm" style={{ padding: '2px 8px', fontSize: '0.75rem' }} onClick={(e) => { e.stopPropagation(); handleSetSlug(t.id, t.name); }}>+ Aggiungi Slug</button>
                                        )}
                                        {t.status === 'pending' && <span className="badge" style={{ background: 'rgba(234,179,8,0.12)', color: 'var(--accent-yellow)' }}>In Attesa</span>}
                                        {t.status !== 'pending' && !t.is_active && <span className="badge" style={{ background: 'rgba(248,113,113,0.12)', color: 'var(--accent-red)' }}>Inattivo</span>}
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                                        <div style={{ textAlign: 'right' }}>
                                        </div>
                                        <div style={{ fontSize: '0.82rem' }}>
                                            <Key size={12} style={{ marginRight: 4 }} /> {t.site_count} chiavi
                                        </div>
                                        {isAdmin && t.status === 'pending' && (
                                            <button className="btn btn-sm btn-primary" onClick={(e) => { e.stopPropagation(); handleApprove(t.id); }}>
                                                Approva
                                            </button>
                                        )}
                                        {isAdmin && (
                                            <button className="btn btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); handleDelete(t.id); }}>
                                                <Trash2 size={12} />
                                            </button>
                                        )}
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
                                                <div className="kpi-label">Chiavi</div>
                                                <div className="kpi-value blue">{tenantDetail.usage?.sites_count || 0}</div>
                                            </div>
                                        </div>

                                        {/* Keys (Mapped as Sites backend-side) */}
                                        <div className="section-header">
                                            <h4 className="section-title"><Key size={16} /> Chiavi ({tenantDetail.sites?.length || 0})</h4>
                                        </div>

                                        {showSiteCreate === t.id && canManageSites && (
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
                                            <div className="table-responsive">
                                                <table className="data-table">
                                                    <thead>
                                                        <tr>
                                                            <th style={{ width: '40%' }}>Alias</th>
                                                            <th style={{ width: '60%' }}>ID</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {tenantDetail.sites.map(s => (
                                                            <tr key={s.id}>
                                                                <td style={{ fontWeight: 600 }}>{s.alias}</td>
                                                                <td><span className="badge">#{s.id}</span></td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        ) : (
                                            <div className="empty-state" style={{ padding: 16 }}>
                                                <p>Nessuna chiave presente</p>
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
