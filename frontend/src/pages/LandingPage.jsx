import { useNavigate } from 'react-router-dom';
import { Shield, Zap, Globe, Server, Activity, ArrowRight } from 'lucide-react';

export default function LandingPage() {
    const navigate = useNavigate();

    return (
        <div className="landing">
            <div className="landing-hero" style={{ paddingTop: '120px' }}>
                <img src="/logo.svg" alt="WPEX Logo" width="80" height="80" style={{ marginBottom: 24, animation: 'float 6s ease-in-out infinite' }} />

                <div className="badge" style={{ marginBottom: 24, fontSize: '0.85rem' }}>
                    <Server size={14} /> WPEX Orchestrator 2.0
                </div>

                <h1>
                    Controllo totale delle tue reti<br />
                    <span className="gradient-text">WireGuard Mesh</span>
                </h1>

                <p>
                    Semplifica il deployment, gestisci il traffico BGP/OSPF e monitora la
                    tua infrastruttura overlay globale con un'esperienza fluida e reattiva.
                    Creato per gli ambienti zero-trust moderni.
                </p>

                <button
                    className="btn btn-primary btn-lg"
                    onClick={() => navigate('/login')}
                    style={{ padding: '16px 36px', fontSize: '1.05rem', marginTop: 16, display: 'inline-flex', gap: 12 }}
                >
                    Inizia ora <ArrowRight size={20} />
                </button>
            </div>

            <div className="landing-features">
                <div className="grid-3" style={{ gap: 32 }}>
                    <div className="feature-card">
                        <div className="feature-icon purple"><Shield size={26} /></div>
                        <h3>Sicurezza Granulare</h3>
                        <p>Gestione RBAC multi-tenant out-of-the-box, crittografia end-to-end e autenticazione JWT rigorosa. La tua sicurezza, al primo posto.</p>
                    </div>
                    <div className="feature-card">
                        <div className="feature-icon green"><Zap size={26} /></div>
                        <h3>Deploy Istantaneo</h3>
                        <p>Spina nuovi nodi di relay con interfacce native Docker. La riconfigurazione automatica propaga le modifiche dell'infrastruttura in tempo reale senza down-time.</p>
                    </div>
                    <div className="feature-card">
                        <div className="feature-icon blue"><Activity size={26} /></div>
                        <h3>Monitoraggio Dinamico</h3>
                        <p>Osserva l'heartbeat dei tuoi nodi, handshake, latenza e l'allocazione delle risorse attraverso KPI avanzati e log streaming diretti dal demone WireGuard.</p>
                    </div>
                </div>
            </div>

            <div className="landing-footer" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                Powered by WPEX • FastAPI • React
            </div>
        </div>
    );
}
