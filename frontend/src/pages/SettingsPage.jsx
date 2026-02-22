import { useState, useEffect } from 'react';
import { useAuth } from '../AuthContext';
import { api } from '../api';
import Sidebar from '../components/Sidebar';
import { Settings, Users, Shield, Server, Save, RefreshCw, AlertTriangle, Trash2 } from 'lucide-react';

export default function SettingsPage() {
    const { user } = useAuth();
    const [users, setUsers] = useState([]);
    const [tenants, setTenants] = useState([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(null);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [tab, setTab] = useState('rbac');

    useEffect(() => { loadData(); }, []);

    const loadData = async () => {
        setLoading(true);
        try {
            const [usersData, tenantsData] = await Promise.all([
                api.getUsers(),
                api.getPublicTenants()
            ]);
            setUsers(usersData.users || usersData || []);
            setTenants(tenantsData.tenants || []);
        } catch (err) {
            setError('Impossibile caricare i dati');
        } finally {
            setLoading(false);
        }
    };

    const handleRoleChange = async (userId, newRole) => {
        setSaving(userId);
        setError('');
        setSuccess('');
        try {
            await api.updateUserRole(userId, newRole);
            setUsers(prev => prev.map(u => u.id === userId ? { ...u, role: newRole } : u));
            setSuccess(`Ruolo aggiornato per utente #${userId}`);
            setTimeout(() => setSuccess(''), 3000);
        } catch (err) {
            setError(err.message);
        } finally {
            setSaving(null);
        }
    };

    const handleTenantChange = async (userId, tenantId) => {
        setSaving(userId);
        setError('');
        try {
            await api.updateUserTenant(userId, tenantId ? parseInt(tenantId) : null);
            setUsers(prev => prev.map(u => u.id === userId ? { ...u, tenant_id: tenantId ? parseInt(tenantId) : null } : u));
            setSuccess(`Tenant aggiornato per utente #${userId}`);
            setTimeout(() => setSuccess(''), 3000);
        } catch (err) {
            setError(err.message);
        } finally {
            setSaving(null);
        }
    };

    const handleStatusChange = async (userId, newStatus) => {
        setSaving(userId);
        setError('');
        setSuccess('');
        try {
            await api.updateUserStatus(userId, newStatus);
            setUsers(prev => prev.map(u => u.id === userId ? { ...u, status: newStatus } : u));
            setSuccess(`Stato utente #${userId} aggiornato a ${newStatus}`);
            setTimeout(() => setSuccess(''), 3000);
        } catch (err) {
            setError(err.message);
        } finally {
            setSaving(null);
        }
    };

    const handleDeleteUser = async (userId, username) => {
        if (!window.confirm(`Sei sicuro di voler eliminare definitivamente l'utente ${username}?`)) return;
        setSaving(userId);
        setError('');
        setSuccess('');
        try {
            await api.deleteUser(userId);
            setUsers(prev => prev.filter(u => u.id !== userId));
            setSuccess(`Utente ${username} eliminato con successo`);
            setTimeout(() => setSuccess(''), 3000);
        } catch (err) {
            setError(err.message);
        } finally {
            setSaving(null);
        }
    };

    const roleColors = {
        admin: { bg: 'rgba(239, 68, 68, 0.15)', color: '#f87171', border: 'rgba(239, 68, 68, 0.3)' },
        executive: { bg: 'rgba(124, 106, 239, 0.15)', color: '#9b8afb', border: 'rgba(124, 106, 239, 0.3)' },
        engineer: { bg: 'rgba(52, 211, 153, 0.15)', color: '#34d399', border: 'rgba(52, 211, 153, 0.3)' },
        viewer: { bg: 'rgba(156, 163, 175, 0.15)', color: '#9ca3af', border: 'rgba(156, 163, 175, 0.3)' },
    };

    const statusColors = {
        active: { bg: 'rgba(52, 211, 153, 0.15)', color: '#34d399', border: 'rgba(52, 211, 153, 0.3)' },
        pending: { bg: 'rgba(251, 191, 36, 0.15)', color: '#fbbf24', border: 'rgba(251, 191, 36, 0.3)' },
        disabled: { bg: 'rgba(239, 68, 68, 0.15)', color: '#f87171', border: 'rgba(239, 68, 68, 0.3)' },
    };

    return (
        <div className="app-layout">
            <Sidebar />
            <main className="main-content">
                <div className="page-header">
                    <div>
                        <h1><Settings size={28} /> Settings</h1>
                        <p className="subtitle">Gestione RBAC, sicurezza e configurazione di sistema</p>
                    </div>
                    <button className="btn btn-secondary" onClick={loadData}>
                        <RefreshCw size={16} /> Ricarica
                    </button>
                </div>

                {error && <div className="alert alert-danger"><AlertTriangle size={16} /> {error}</div>}
                {success && <div className="alert alert-success">{success}</div>}

                <div className="tabs" style={{ marginBottom: 24 }}>
                    <button className={`tab ${tab === 'rbac' ? 'active' : ''}`} onClick={() => setTab('rbac')}>
                        <Users size={16} /> Utenti & Ruoli
                    </button>
                    <button className={`tab ${tab === 'security' ? 'active' : ''}`} onClick={() => setTab('security')}>
                        <Shield size={16} /> Sicurezza
                    </button>
                    <button className={`tab ${tab === 'system' ? 'active' : ''}`} onClick={() => setTab('system')}>
                        <Server size={16} /> Sistema
                    </button>
                </div>

                {tab === 'rbac' && (
                    <div className="card">
                        <h2 style={{ marginBottom: 16, fontSize: '1.1rem' }}>
                            <Users size={20} /> Gestione Utenti e Ruoli
                        </h2>
                        {user?.role !== 'admin' && (
                            <div className="alert alert-danger" style={{ marginBottom: 16 }}>
                                <AlertTriangle size={16} /> Solo gli amministratori possono modificare i ruoli globali.
                            </div>
                        )}

                        <div className="card" style={{ background: 'rgba(255,255,255,0.02)', padding: '16px 20px', marginBottom: 20 }}>
                            <h3 style={{ fontSize: '0.95rem', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
                                <Shield size={16} color="var(--accent-purple-light)" /> Gerarchia dei Ruoli
                            </h3>
                            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) minmax(0,1fr)', gap: 12, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                {user?.role === 'admin' && (
                                    <div style={{ background: 'rgba(239, 68, 68, 0.05)', padding: 12, borderRadius: 8, borderLeft: '3px solid #f87171' }}>
                                        <strong style={{ color: '#e8e8f0', display: 'block', marginBottom: 4 }}>Admin</strong>
                                        Accesso completo in lettura e scrittura a tutto il sistema, organizzazioni interne e configurazioni (Globale).
                                    </div>
                                )}
                                <div style={{ background: 'rgba(124, 106, 239, 0.05)', padding: 12, borderRadius: 8, borderLeft: '3px solid #9b8afb' }}>
                                    <strong style={{ color: '#e8e8f0', display: 'block', marginBottom: 4 }}>Executive</strong>
                                    Sola lettura per metriche e dashboard di tutte le organizzazioni. Nessun permesso di modifica (Globale).
                                </div>
                                <div style={{ background: 'rgba(52, 211, 153, 0.05)', padding: 12, borderRadius: 8, borderLeft: '3px solid #34d399' }}>
                                    <strong style={{ color: '#e8e8f0', display: 'block', marginBottom: 4 }}>Engineer</strong>
                                    Gestione completa per la propria organizzazione. Può approvare utenti del proprio tenant (Scopato al Tenant).
                                </div>
                                <div style={{ background: 'rgba(156, 163, 175, 0.05)', padding: 12, borderRadius: 8, borderLeft: '3px solid #9ca3af' }}>
                                    <strong style={{ color: '#e8e8f0', display: 'block', marginBottom: 4 }}>Viewer</strong>
                                    Visione limitata alle risorse della propria organizzazione. Nessuna modifica (Scopato al Tenant).
                                </div>
                            </div>
                        </div>

                        {loading ? (
                            <div style={{ textAlign: 'center', padding: 40 }}>
                                <div className="spinner" />
                            </div>
                        ) : (
                            <table className="data-table">
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Username</th>
                                        <th>Ruolo</th>
                                        <th>Stato</th>
                                        <th>Tenant</th>
                                        <th>Creato il</th>
                                        <th>Azioni</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {users.map(u => (
                                        <tr key={u.id}>
                                            <td>#{u.id}</td>
                                            <td style={{ fontWeight: 600 }}>{u.username}</td>
                                            <td>
                                                <span style={{
                                                    display: 'inline-block',
                                                    padding: '3px 10px',
                                                    borderRadius: 20,
                                                    fontSize: '0.8rem',
                                                    fontWeight: 600,
                                                    background: (roleColors[u.role] || roleColors.engineer).bg,
                                                    color: (roleColors[u.role] || roleColors.engineer).color,
                                                    border: `1px solid ${(roleColors[u.role] || roleColors.engineer).border}`,
                                                }}>
                                                    {u.role || 'engineer'}
                                                </span>
                                            </td>
                                            <td>
                                                <span style={{
                                                    display: 'inline-block',
                                                    padding: '3px 10px',
                                                    borderRadius: 20,
                                                    fontSize: '0.8rem',
                                                    fontWeight: 600,
                                                    background: (statusColors[u.status] || statusColors.pending).bg,
                                                    color: (statusColors[u.status] || statusColors.pending).color,
                                                    border: `1px solid ${(statusColors[u.status] || statusColors.pending).border}`,
                                                }}>
                                                    {u.status || 'pending'}
                                                </span>
                                            </td>
                                            <td>
                                                {u.tenant_id
                                                    ? tenants.find(t => t.id === u.tenant_id)?.name || `Tenant #${u.tenant_id}`
                                                    : '—'
                                                }
                                            </td>
                                            <td style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                                                {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
                                            </td>
                                            <td>
                                                {user?.role === 'admin' && u.id !== user.id ? (
                                                    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                                                        <select
                                                            className="input"
                                                            value={u.role || 'engineer'}
                                                            onChange={e => handleRoleChange(u.id, e.target.value)}
                                                            disabled={saving === u.id}
                                                            style={{ width: 130, padding: '4px 8px', fontSize: '0.82rem' }}
                                                        >
                                                            {user?.role === 'admin' && <option value="admin">Admin</option>}
                                                            <option value="executive">Executive</option>
                                                            <option value="engineer">Engineer</option>
                                                            <option value="viewer">Viewer</option>
                                                        </select>
                                                        {u.status === 'pending' ? (
                                                            <button
                                                                className="btn btn-sm btn-success"
                                                                onClick={() => handleStatusChange(u.id, 'active')}
                                                                disabled={saving === u.id}
                                                                style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                                                            >
                                                                Approva
                                                            </button>
                                                        ) : (
                                                            <button
                                                                className={`btn btn-sm ${u.status === 'disabled' ? 'btn-secondary' : 'btn-danger'}`}
                                                                onClick={() => handleStatusChange(u.id, u.status === 'disabled' ? 'active' : 'disabled')}
                                                                disabled={saving === u.id}
                                                                style={{ padding: '4px 8px', fontSize: '0.75rem', width: 80 }}
                                                            >
                                                                {u.status === 'disabled' ? 'Attiva' : 'Disabilita'}
                                                            </button>
                                                        )}
                                                        <select
                                                            className="input"
                                                            value={u.tenant_id || ''}
                                                            onChange={e => handleTenantChange(u.id, e.target.value)}
                                                            disabled={saving === u.id}
                                                            style={{ width: 140, padding: '4px 8px', fontSize: '0.82rem' }}
                                                        >
                                                            <option value="">Nessun Tenant</option>
                                                            {tenants.map(t => (
                                                                <option key={t.id} value={t.id}>{t.name}</option>
                                                            ))}
                                                        </select>
                                                        {user?.role === 'admin' && (
                                                            <button
                                                                className="btn btn-sm btn-danger"
                                                                onClick={() => handleDeleteUser(u.id, u.username)}
                                                                disabled={saving === u.id}
                                                                title="Elimina Utente"
                                                                style={{ padding: '4px 8px' }}
                                                            >
                                                                <Trash2 size={14} />
                                                            </button>
                                                        )}
                                                        {saving === u.id && <div className="spinner" style={{ width: 16, height: 16 }} />}
                                                    </div>
                                                ) : (
                                                    <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                                                        {u.id === user?.id ? '(Tu)' : '—'}
                                                    </span>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                    {users.length === 0 && (
                                        <tr>
                                            <td colSpan="6" style={{ textAlign: 'center', padding: 32, color: 'var(--text-muted)' }}>
                                                Nessun utente trovato
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        )}
                    </div>
                )}

                {tab === 'security' && (
                    <div className="card">
                        <h2 style={{ marginBottom: 16, fontSize: '1.1rem' }}>
                            <Shield size={20} /> Impostazioni di Sicurezza
                        </h2>
                        <div style={{ display: 'grid', gap: 16 }}>
                            <div className="card" style={{ background: 'rgba(255,255,255,0.02)' }}>
                                <h3 style={{ fontSize: '0.95rem', marginBottom: 8 }}>Autenticazione</h3>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, fontSize: '0.88rem' }}>
                                    <div><strong>Metodo:</strong> JWT Bearer Token</div>
                                    <div><strong>Scadenza token:</strong> 24 ore</div>
                                    <div><strong>Token blacklist:</strong> <span style={{ color: '#34d399' }}>Attiva</span></div>
                                    <div><strong>MFA:</strong> <span style={{ color: '#fbbf24' }}>Non configurata</span></div>
                                </div>
                            </div>
                            <div className="card" style={{ background: 'rgba(255,255,255,0.02)' }}>
                                <h3 style={{ fontSize: '0.95rem', marginBottom: 8 }}>Password Policy</h3>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, fontSize: '0.88rem' }}>
                                    <div><strong>Lunghezza minima:</strong> 6 caratteri</div>
                                    <div><strong>Hashing:</strong> bcrypt (SHA-256)</div>
                                    <div><strong>Tentativi max:</strong> Illimitati</div>
                                    <div><strong>IP Whitelist:</strong> <span style={{ color: '#fbbf24' }}>Non configurata</span></div>
                                </div>
                            </div>
                            <div className="card" style={{ background: 'rgba(255,255,255,0.02)' }}>
                                <h3 style={{ fontSize: '0.95rem', marginBottom: 8 }}>Crittografia</h3>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, fontSize: '0.88rem' }}>
                                    <div><strong>Chiavi VPN:</strong> Crittografate con Fernet</div>
                                    <div><strong>Connessioni DB:</strong> Locale (non TLS)</div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {tab === 'system' && (
                    <div className="card">
                        <h2 style={{ marginBottom: 16, fontSize: '1.1rem' }}>
                            <Server size={20} /> Informazioni di Sistema
                        </h2>
                        <div style={{ display: 'grid', gap: 16 }}>
                            <div className="card" style={{ background: 'rgba(255,255,255,0.02)' }}>
                                <h3 style={{ fontSize: '0.95rem', marginBottom: 8 }}>Backend</h3>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, fontSize: '0.88rem' }}>
                                    <div><strong>Framework:</strong> FastAPI (Python)</div>
                                    <div><strong>Database:</strong> PostgreSQL</div>
                                    <div><strong>Autenticazione:</strong> JWT + RBAC</div>
                                    <div><strong>Container Runtime:</strong> Docker Swarm</div>
                                </div>
                            </div>
                            <div className="card" style={{ background: 'rgba(255,255,255,0.02)' }}>
                                <h3 style={{ fontSize: '0.95rem', marginBottom: 8 }}>Frontend</h3>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, fontSize: '0.88rem' }}>
                                    <div><strong>Framework:</strong> React 18 + Vite</div>
                                    <div><strong>Router:</strong> React Router v6</div>
                                    <div><strong>Icone:</strong> Lucide React</div>
                                    <div><strong>Proxy:</strong> Nginx</div>
                                </div>
                            </div>
                            <div className="card" style={{ background: 'rgba(255,255,255,0.02)' }}>
                                <h3 style={{ fontSize: '0.95rem', marginBottom: 8 }}>WPEX Relay</h3>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, fontSize: '0.88rem' }}>
                                    <div><strong>Linguaggio:</strong> Go 1.21</div>
                                    <div><strong>Protocollo:</strong> WireGuard</div>
                                    <div><strong>Stats API:</strong> HTTP :8080</div>
                                    <div><strong>Rete:</strong> Docker Overlay</div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}
