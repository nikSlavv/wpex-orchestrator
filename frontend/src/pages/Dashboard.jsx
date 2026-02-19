import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import { api } from '../api';
import {
    Server, Link2, Users, Activity, AlertTriangle, AlertCircle,
    ArrowUp, ArrowDown, Wifi, Shield, RefreshCw, ChevronRight
} from 'lucide-react';

function HealthRing({ value, size = 56 }) {
    const radius = (size - 8) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (value / 100) * circumference;
    const color = value >= 80 ? '#34d399' : value >= 50 ? '#fbbf24' : '#f87171';

    return (
        <div className="health-ring" style={{ width: size, height: size }}>
            <svg width={size} height={size}>
                <circle className="health-ring-bg"
                    cx={size / 2} cy={size / 2} r={radius}
                    fill="none" strokeWidth="4" />
                <circle className="health-ring-fill"
                    cx={size / 2} cy={size / 2} r={radius}
                    fill="none" stroke={color} strokeWidth="4"
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    strokeLinecap="round" />
            </svg>
            <div className="health-ring-text" style={{ color }}>{Math.round(value)}</div>
        </div>
    );
}

export default function Dashboard() {
    const [kpi, setKpi] = useState(null);
    const [alerts, setAlerts] = useState(null);
    const [loading, setLoading] = useState(true);

    const loadData = useCallback(async () => {
        try {
            const [k, a] = await Promise.all([
                api.getDashboardKPI(),
                api.getDashboardAlerts()
            ]);
            setKpi(k);
            setAlerts(a);
        } catch (e) {
            console.error('KPI load error:', e);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadData(); const i = setInterval(loadData, 30000); return () => clearInterval(i); }, [loadData]);

    return (
        <div className="page">
            <Sidebar />
            <div className="main-content">
                <div className="page-header">
                    <h1 className="page-title"><Activity size={26} /> Executive Overview</h1>
                    <button className="btn btn-sm" onClick={loadData}>
                        <RefreshCw size={14} /> Aggiorna
                    </button>
                </div>

                {loading ? (
                    <div className="loading-screen"><div className="spinner" /></div>
                ) : kpi ? (
                    <>
                        {/* KPI Cards */}
                        <div className="kpi-grid">
                            <div className="kpi-card">
                                <div className="kpi-label"><Server size={14} /> Relay Attivi</div>
                                <div className={`kpi-value ${kpi.relays_active === kpi.relays_total ? 'green' : 'amber'}`}>
                                    {kpi.relays_active}/{kpi.relays_total}
                                </div>
                                <div className="kpi-sub">{kpi.relays_total - kpi.relays_active} inattivi</div>
                            </div>
                            <div className="kpi-card">
                                <div className="kpi-label"><Link2 size={14} /> Tunnel</div>
                                <div className="kpi-value blue">{kpi.tunnels_active}/{kpi.tunnels_total}</div>
                                <div className="kpi-sub">{kpi.tunnels_degraded} degradati</div>
                            </div>
                            <div className="kpi-card">
                                <div className="kpi-label"><Users size={14} /> Tenants</div>
                                <div className="kpi-value purple">{kpi.tenants_active}</div>
                                <div className="kpi-sub">Organizzazioni attive</div>
                            </div>
                            <div className="kpi-card">
                                <div className="kpi-label"><Wifi size={14} /> Peers</div>
                                <div className="kpi-value green">{kpi.total_peers}</div>
                                <div className="kpi-sub">{kpi.bandwidth_aggregated_mb} MB trasferiti</div>
                            </div>
                            <div className="kpi-card">
                                <div className="kpi-label"><Shield size={14} /> Health Score</div>
                                <div className="kpi-value" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                    <HealthRing value={kpi.global_health_score} size={48} />
                                    <span className={kpi.global_health_score >= 80 ? 'green' : kpi.global_health_score >= 50 ? 'amber' : 'red'}>
                                        {kpi.global_health_score}%
                                    </span>
                                </div>
                            </div>
                        </div>

                        <div className="grid-2">
                            {/* Alerts */}
                            <div className="card">
                                <div className="card-header">
                                    <h3 className="card-title">
                                        <AlertTriangle size={18} /> Alerts
                                        {alerts && alerts.critical > 0 && (
                                            <span className="badge" style={{ background: 'rgba(248,113,113,0.15)', color: 'var(--accent-red)', borderColor: 'rgba(248,113,113,0.3)' }}>
                                                {alerts.critical} critici
                                            </span>
                                        )}
                                    </h3>
                                </div>
                                <div className="alert-list">
                                    {alerts && alerts.alerts.length > 0 ? alerts.alerts.map((a, i) => (
                                        <div key={i} className={`alert-item ${a.severity}`}>
                                            {a.severity === 'critical' ? <AlertCircle size={16} /> : <AlertTriangle size={16} />}
                                            <span>{a.message}</span>
                                        </div>
                                    )) : (
                                        <div className="empty-state" style={{ padding: '24px' }}>
                                            <Shield size={32} />
                                            <p>Nessun alert attivo</p>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Relay Health List */}
                            <div className="card">
                                <div className="card-header">
                                    <h3 className="card-title"><Server size={18} /> Relay Health</h3>
                                    <Link to="/relays" className="btn btn-sm"><ChevronRight size={14} /></Link>
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                    {kpi.relays.map((r) => (
                                        <Link key={r.id} to={`/relays/${r.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                                            <div className="health-gauge">
                                                <HealthRing value={r.health} size={40} />
                                                <div style={{ flex: 1 }}>
                                                    <div className="health-label">{r.name}</div>
                                                    <div className="health-detail">
                                                        <span className={`status-dot ${r.status}`} style={{ marginRight: 6 }} />
                                                        {r.status} • {r.peers_count} peers
                                                    </div>
                                                </div>
                                                <div style={{ textAlign: 'right' }}>
                                                    <div style={{ fontSize: '0.82rem', fontWeight: 600 }}>{r.health}%</div>
                                                    <div className="health-detail">
                                                        <ArrowUp size={10} /> {Math.round(r.bytes_transferred / 1024)}KB
                                                    </div>
                                                </div>
                                            </div>
                                        </Link>
                                    ))}
                                    {kpi.relays.length === 0 && (
                                        <div className="empty-state" style={{ padding: '24px' }}>
                                            <Server size={32} />
                                            <p>Nessun relay configurato</p>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </>
                ) : (
                    <div className="empty-state">
                        <AlertCircle size={48} />
                        <h3>Errore nel caricamento dei dati</h3>
                        <button className="btn btn-sm" onClick={loadData}>Riprova</button>
                    </div>
                )}
            </div>
        </div>
    );
}
