import { useNavigate } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { Clock, LogOut, ShieldAlert } from 'lucide-react';

export default function PendingApprovalPage() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    const handleLogout = async () => {
        await logout();
        navigate('/login');
    };

    const isDisabled = user?.status === 'disabled';

    return (
        <div className="login-page">
            <div className="login-card card" style={{ maxWidth: 500, textAlign: 'center', padding: '40px 30px' }}>
                <div style={{
                    width: 80, height: 80, borderRadius: '50%',
                    background: isDisabled ? 'rgba(239, 68, 68, 0.1)' : 'rgba(251, 191, 36, 0.1)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    margin: '0 auto 24px'
                }}>
                    {isDisabled ? (
                        <ShieldAlert size={40} color="#f87171" />
                    ) : (
                        <Clock size={40} color="#fbbf24" />
                    )}
                </div>

                <h1 style={{ marginBottom: 12 }}>
                    {isDisabled ? 'Account Disabilitato' : 'In attesa di approvazione'}
                </h1>

                <p className="subtitle" style={{ fontSize: '1rem', lineHeight: 1.6, marginBottom: 32 }}>
                    {isDisabled ? (
                        "Il tuo account è stato disabilitato da un amministratore. Contatta il supporto della tua organizzazione per maggiori informazioni."
                    ) : (
                        "Il tuo account è stato creato con successo, ma è in attesa di approvazione da parte di un amministratore della tua organizzazione."
                    )}
                </p>

                <div className="card" style={{ background: 'rgba(255,255,255,0.03)', padding: 16, marginBottom: 32, textAlign: 'left' }}>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 4 }}>Utente</div>
                    <div style={{ fontWeight: 600 }}>{user?.username}</div>
                    <div style={{ height: 12 }} />
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 4 }}>Stato</div>
                    <div style={{
                        display: 'inline-block', padding: '2px 8px', borderRadius: 4, fontSize: '0.75rem', fontWeight: 700,
                        background: isDisabled ? 'rgba(239, 68, 68, 0.2)' : 'rgba(251, 191, 36, 0.2)',
                        color: isDisabled ? '#f87171' : '#fbbf24'
                    }}>
                        {user?.status?.toUpperCase() || 'PENDING'}
                    </div>
                </div>

                <button className="btn btn-secondary btn-full" onClick={handleLogout} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                    <LogOut size={18} /> Esci dall'account
                </button>
            </div>
        </div>
    );
}
