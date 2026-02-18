import { useNavigate } from 'react-router-dom';
import { Shield, Zap, Globe } from 'lucide-react';

export default function LandingPage() {
    const navigate = useNavigate();

    return (
        <div className="landing">
            <div className="landing-hero">
                <span className="badge">WPEX Orchestrator v2</span>
                <h1>
                    Gestisci i tuoi server<br />
                    <span className="gradient-text">in modo semplice</span>
                </h1>
                <p>
                    Monitora, controlla e gestisci le tue istanze WPEX da un'unica
                    dashboard moderna. Provisioning automatico, gestione chiavi integrata
                    e monitoraggio in tempo reale.
                </p>
                <button className="btn btn-primary btn-lg" onClick={() => navigate('/login')}>
                    Get Started
                </button>
            </div>

            <div className="landing-features">
                <div className="grid-3">
                    <div className="feature-card">
                        <div className="feature-icon purple"><Shield size={26} /></div>
                        <h3>Sicurezza Integrata</h3>
                        <p>Autenticazione JWT, chiavi crittografate con PGP e sessioni sicure con blacklist automatica.</p>
                    </div>
                    <div className="feature-card">
                        <div className="feature-icon green"><Zap size={26} /></div>
                        <h3>Deploy Istantaneo</h3>
                        <p>Crea e avvia nuovi server con un click. Gestione Docker automatizzata con rete overlay condivisa.</p>
                    </div>
                    <div className="feature-card">
                        <div className="feature-icon blue"><Globe size={26} /></div>
                        <h3>Monitoraggio Live</h3>
                        <p>Console integrata con iframe live, log in tempo reale e controlli rapidi per ogni istanza.</p>
                    </div>
                </div>
            </div>

            <div className="landing-footer">
                WPEX Orchestrator — Built with React &amp; FastAPI
            </div>
        </div>
    );
}
