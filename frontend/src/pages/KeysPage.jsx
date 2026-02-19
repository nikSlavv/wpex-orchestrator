import { useState, useEffect } from 'react';
import Sidebar from '../components/Sidebar';
import { api } from '../api';
import { Key, Plus, Trash2, RefreshCw, Eye, EyeOff, Copy } from 'lucide-react';

export default function KeysPage() {
    const [keys, setKeys] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);
    const [alias, setAlias] = useState('');
    const [keyValue, setKeyValue] = useState('');
    const [revealedKeys, setRevealedKeys] = useState(new Set());

    const loadData = async () => {
        try {
            const data = await api.getKeys();
            setKeys(data.keys || []);
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    };

    useEffect(() => { loadData(); }, []);

    const handleCreate = async () => {
        if (!alias || !keyValue) return;
        try {
            await api.createKey(alias, keyValue);
            setShowCreate(false);
            setAlias('');
            setKeyValue('');
            loadData();
        } catch (e) { alert(e.message); }
    };

    const handleDelete = async (id) => {
        if (!confirm('Eliminare questa chiave?')) return;
        try { await api.deleteKey(id); loadData(); } catch (e) { alert(e.message); }
    };

    const toggleReveal = (id) => {
        const s = new Set(revealedKeys);
        s.has(id) ? s.delete(id) : s.add(id);
        setRevealedKeys(s);
    };

    const copyKey = (key) => {
        navigator.clipboard.writeText(key);
    };

    return (
        <div className="page">
            <Sidebar />
            <div className="main-content">
                <div className="page-header">
                    <h1 className="page-title"><Key size={26} /> Chiavi di Accesso</h1>
                    <div style={{ display: 'flex', gap: 8 }}>
                        <button className="btn btn-primary" onClick={() => setShowCreate(!showCreate)}>
                            <Plus size={16} /> Nuova Chiave
                        </button>
                        <button className="btn btn-sm" onClick={loadData}><RefreshCw size={14} /></button>
                    </div>
                </div>

                {showCreate && (
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
                            <button className="btn btn-primary" onClick={handleCreate}>Crea</button>
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
                                    <th>ID</th><th>Alias</th><th>Chiave</th><th>Azioni</th>
                                </tr>
                            </thead>
                            <tbody>
                                {keys.map(k => (
                                    <tr key={k.id}>
                                        <td>#{k.id}</td>
                                        <td style={{ fontWeight: 600 }}>{k.alias}</td>
                                        <td>
                                            <code style={{ fontSize: '0.8rem', color: revealedKeys.has(k.id) ? 'var(--text-secondary)' : 'transparent', background: revealedKeys.has(k.id) ? 'transparent' : 'var(--bg-secondary)', padding: '2px 6px', borderRadius: 4 }}>
                                                {k.key}
                                            </code>
                                        </td>
                                        <td>
                                            <div style={{ display: 'flex', gap: 4 }}>
                                                <button className="btn btn-sm" onClick={() => toggleReveal(k.id)} title={revealedKeys.has(k.id) ? 'Nascondi' : 'Mostra'}>
                                                    {revealedKeys.has(k.id) ? <EyeOff size={12} /> : <Eye size={12} />}
                                                </button>
                                                <button className="btn btn-sm" onClick={() => copyKey(k.key)} title="Copia">
                                                    <Copy size={12} />
                                                </button>
                                                <button className="btn btn-sm btn-danger" onClick={() => handleDelete(k.id)}>
                                                    <Trash2 size={12} />
                                                </button>
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
