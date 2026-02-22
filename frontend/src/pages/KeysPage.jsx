import { useState, useEffect } from 'react';
import Sidebar from '../components/Sidebar';
import { api } from '../api';
import { Key, Plus, Trash2, RefreshCw, Copy, Check } from 'lucide-react';
import { useAuth } from '../AuthContext';

export default function KeysPage() {
    const { user } = useAuth();
    const canMutate = !['viewer', 'executive'].includes(user?.role);
    const [keys, setKeys] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);
    const [alias, setAlias] = useState('');
    const [keyValue, setKeyValue] = useState('');
    const [copiedKey, setCopiedKey] = useState(null);
    const [tenants, setTenants] = useState([]);
    const [selectedTenant, setSelectedTenant] = useState('');

    const loadData = async () => {
        try {
            const [data, tList] = await Promise.all([
                api.getKeys(),
                user?.role === 'admin' ? api.getTenants() : Promise.resolve([])
            ]);
            setKeys(data.keys || []);
            if (user?.role === 'admin') setTenants(tList.tenants || tList || []);
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    };

    useEffect(() => { loadData(); }, []);

    const handleCreate = async () => {
        if (!alias || !keyValue) return;
        const tenantIdToSend = user?.role === 'admin' ? selectedTenant || null : user?.tenant_id;
        try {
            await api.createKey(alias, keyValue, tenantIdToSend);
            setShowCreate(false);
            setAlias('');
            setKeyValue('');
            setSelectedTenant('');
            loadData();
        } catch (e) { alert(e.message); }
    };

    const handleDelete = async (id) => {
        if (!confirm('Eliminare questa chiave?')) return;
        try { await api.deleteKey(id); loadData(); } catch (e) { alert(e.message); }
    };

    const copyKey = async (id, key) => {
        try {
            if (navigator?.clipboard?.writeText) {
                await navigator.clipboard.writeText(key);
            } else {
                // Fallback approach if running without secure context (http://ip)
                const textArea = document.createElement("textarea");
                textArea.value = key;
                textArea.style.position = "fixed";
                textArea.style.left = "-999999px";
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
            }
            setCopiedKey(id);
            setTimeout(() => setCopiedKey(null), 2000);
        } catch (err) {
            console.error("Copia fallita:", err);
            alert("Il tuo browser blocca la copia automatica. Seleziona il testo manualmente.");
        }
    };

    return (
        <div className="page">
            <Sidebar />
            <div className="main-content">
                <div className="page-header">
                    <h1 className="page-title"><Key size={26} /> Chiavi di Accesso</h1>
                    <div style={{ display: 'flex', gap: 8 }}>
                        {canMutate && (
                            <button className="btn btn-primary" onClick={() => setShowCreate(!showCreate)}>
                                <Plus size={16} /> Nuova Chiave
                            </button>
                        )}
                        <button className="btn btn-sm" onClick={loadData}><RefreshCw size={14} /></button>
                    </div>
                </div>

                {showCreate && canMutate && (
                    <div className="card" style={{ marginBottom: 20 }}>
                        <h3 className="card-title"><Plus size={18} /> Crea Chiave</h3>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 12 }}>
                            <div className="form-group">
                                <label>Alias</label>
                                <input className="input" value={alias} onChange={e => setAlias(e.target.value)} placeholder="client-roma-01" />
                            </div>
                            <div className="form-group">
                                <label>Chiave (WireGuard Public Key)</label>
                                <input className="input" value={keyValue} onChange={e => setKeyValue(e.target.value)} placeholder="Incolla la chiave pubblica..." />
                            </div>
                            {user?.role === 'admin' && (
                                <div className="form-group">
                                    <label>Tenant Proprietario (Opzionale)</label>
                                    <select className="input" value={selectedTenant} onChange={e => setSelectedTenant(e.target.value)}>
                                        <option value="">Nessuno (Globale)</option>
                                        {tenants.map(t => (
                                            <option key={t.id} value={t.id}>{t.name}</option>
                                        ))}
                                    </select>
                                </div>
                            )}
                            <div style={{ marginTop: 16, display: 'flex', gap: 8, justifyContent: 'flex-start' }}>
                                <button className="btn btn-primary" onClick={handleCreate}>Crea</button>
                                <button className="btn btn-secondary" onClick={() => setShowCreate(false)}>Annulla</button>
                            </div>
                        </div>
                    </div>
                )}

                {loading ? (
                    <div className="loading-screen"><div className="spinner" /></div>
                ) : (
                    <div className="card">
                        <div style={{ marginBottom: 16, padding: '12px 16px', background: 'rgba(124, 106, 239, 0.08)', borderLeft: '3px solid var(--accent-purple)', borderRadius: 4, display: 'flex', gap: 12, alignItems: 'center' }}>
                            <div style={{ color: 'var(--accent-purple-light)' }}>
                                <Key size={18} />
                            </div>
                            <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                                Passa il mouse sulla chiave per rivelare il valore. <strong>Clicca per copiarla</strong> negli appunti.
                            </div>
                        </div>
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>ID</th><th>Alias</th><th>Chiave</th><th>Azioni</th>
                                </tr>
                            </thead>
                            <tbody>
                                {keys.map(k => (
                                    <tr key={k.id}>
                                        <td>#{k.id}</td>
                                        <td style={{ fontWeight: 600 }}>{k.alias}</td>
                                        <td>
                                            <div className="secret-group">
                                                <span
                                                    className="secret"
                                                    onClick={() => copyKey(k.id, k.key)}
                                                >
                                                    {k.key}
                                                </span>
                                                {copiedKey === k.id ? (
                                                    <span style={{
                                                        position: 'absolute', top: -30, left: '50%', transform: 'translateX(-50%)',
                                                        background: 'var(--bg-card)', color: 'var(--accent-green)',
                                                        fontSize: '0.75rem', padding: '4px 8px', borderRadius: 4, whiteSpace: 'nowrap',
                                                        border: '1px solid var(--border-subtle)', animation: 'fadeInUp 0.15s ease-out',
                                                        zIndex: 10, boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
                                                    }}>
                                                        Copiata! <Check size={10} style={{ display: 'inline', marginLeft: 2 }} />
                                                    </span>
                                                ) : (
                                                    <span className="hover-msg">
                                                        Clicca per copiare
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                        <td>
                                            <div style={{ display: 'flex', gap: 4 }}>
                                                {canMutate && (
                                                    <button className="btn btn-sm btn-danger" onClick={() => handleDelete(k.id)}>
                                                        <Trash2 size={12} />
                                                    </button>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        {keys.length === 0 && (
                            <div className="empty-state">
                                <Key size={48} />
                                <h3>Nessuna chiave</h3>
                                <p>Aggiungi chiavi WireGuard per i relay</p>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
