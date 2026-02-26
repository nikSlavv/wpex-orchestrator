import { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import { api } from '../api';
import { useAuth } from '../AuthContext';
import {
    Server, RefreshCw, Play, Square, ArrowUpRight,
    Activity, Cpu, HardDrive, Wifi, Terminal, Search,
    RotateCw, Upload, ChevronLeft, Key
} from 'lucide-react';

function HealthRing({ value, size = 64 }) {
    const radius = (size - 8) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (value / 100) * circumference;
    const color = value >= 80 ? '#34d399' : value >= 50 ? '#fbbf24' : '#f87171';
    return (
        <div className="health-ring" style={{ width: size, height: size }}>
            <svg width={size} height={size}>
                <circle className="health-ring-bg" cx={size / 2} cy={size / 2} r={radius} fill="none" strokeWidth="5" />
                <circle className="health-ring-fill" cx={size / 2} cy={size / 2} r={radius}
                    fill="none" stroke={color} strokeWidth="5"
                    strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round" />
            </svg>
            <div className="health-ring-text" style={{ color }}>{Math.round(value)}</div>
        </div>
    );
}

export default function RelayView() {
    const { id } = useParams();   // handles both /relays/7 and /relays/asd
    const [relay, setRelay] = useState(null);
    const [health, setHealth] = useState(null);
    const [container, setContainer] = useState(null);
    const [stats, setStats] = useState(null);
    const [logs, setLogs] = useState(null);
    const [loading, setLoading] = useState(true);
    const [tab, setTab] = useState('overview');
    const [diagTarget, setDiagTarget] = useState('');
    const [diagResult, setDiagResult] = useState(null);
    const [diagLoading, setDiagLoading] = useState(false);

    const { user } = useAuth();
    const canMutate = !['viewer', 'executive'].includes(user?.role);

    // Resolve relay ID: if id param is numeric use it directly, otherwise treat as name
    const [relayId, setRelayId] = useState(() => {
        const parsed = parseInt(id);
        return isNaN(parsed) ? null : parsed;
    });

    const loadData = async () => {
        const rid = parseInt(relayId);
        if (!rid) return;
        try {
            const [h, c, s, serversData] = await Promise.all([
                api.getRelayHealth(rid),
                api.getRelayContainer(rid),
                api.getRelayStats(rid),
                api.getServers().catch(() => ({ servers: [] }))
            ]);
            setHealth(h);
            setContainer(c);
            setStats(s);

            const foundRelay = serversData.servers?.find(r => r.id === rid);
            if (foundRelay) {
                setRelay(foundRelay);
            }
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    };

    // If id is a name (non-numeric), resolve it to a numeric ID
    useEffect(() => {
        const parsed = parseInt(id);
        if (isNaN(parsed)) {
            api.getServers().then(data => {
                const found = data.servers?.find(s => s.name === id);
                if (found) setRelayId(found.id);
            });
        }
    }, [id]);

    useEffect(() => {
        if (!relayId) return;
        loadData();
        const interval = setInterval(() => {
            if (!isMutating.current) loadData();
        }, 10000);
        return () => clearInterval(interval);
    }, [relayId]);

    const handleRestart = async () => {
        try { await api.restartRelay(parseInt(relayId)); loadData(); } catch (e) { alert(e.message); }
    };


    const handlePing = async () => {
        if (!diagTarget) return;
        setDiagLoading(true);
        try {
            const r = await api.pingFromRelay(parseInt(relayId), diagTarget);
            setDiagResult(r);
        } catch (e) { setDiagResult({ error: e.message }); }
        finally { setDiagLoading(false); }
    };

    const handleTraceroute = async () => {
        if (!diagTarget) return;
        setDiagLoading(true);
        try {
            const r = await api.tracerouteFromRelay(parseInt(relayId), diagTarget);
            setDiagResult(r);
        } catch (e) { setDiagResult({ error: e.message }); }
        finally { setDiagLoading(false); }
    };

    const loadLogs = async () => {
        try { const l = await api.getServerLogs(parseInt(relayId)); setLogs(l); } catch { }
    };

    return (
        <div className="page">
            <Sidebar />
            <div className="main-content">
                <div className="page-header">
                    <h1 className="page-title">
                        <Link to="/relays" className="btn btn-sm" style={{ marginRight: 8 }}>
                            <ChevronLeft size={14} />
                        </Link>
                        <Server size={26} /> {health?.relay_name || name || `Relay #${relayId}`}
                    </h1>
                    <div style={{ display: 'flex', gap: 8 }}>
                        <button className="btn btn-sm" onClick={handleRestart}><RotateCw size={14} /> Restart</button>
                        <button className="btn btn-sm" onClick={loadData}><RefreshCw size={14} /></button>
                    </div>
                </div>

                {/* Tabs */}
                <div className="tabs">
                    {['overview', 'diagnostics', 'logs'].map(t => (
                        <button key={t} className={`tab ${tab === t ? 'active' : ''}`}
                            onClick={() => { setTab(t); if (t === 'logs' && !logs) loadLogs(); }}>
                            {t === 'overview' ? 'Overview' : t === 'diagnostics' ? 'Diagnostica' : 'Logs'}
                        </button>
                    ))}
                </div>

                {loading ? (
                    <div className="loading-screen"><div className="spinner" /></div>
                ) : tab === 'overview' ? (
                    <>
                        {/* Health + Container Info */}
                        <div className="grid-2" style={{ marginBottom: 20 }}>
                            {health && (
                                <div className="card">
                                    <div className="card-header">
                                        <h3 className="card-title"><Activity size={18} /> Health Score</h3>
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 24, marginBottom: 20 }}>
                                        <HealthRing value={health.health_score} size={80} />
                                        <div>
                                            <div style={{ fontSize: '2rem', fontWeight: 700, color: health.health_score >= 80 ? 'var(--accent-green)' : health.health_score >= 50 ? 'var(--accent-amber)' : 'var(--accent-red)' }}>
                                                {health.health_score}%
                                            </div>
                                            <div style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>
                                                Composito • {Object.keys(health.components || {}).length} componenti
                                            </div>
                                        </div>
                                    </div>
                                    {/* Component breakdown */}
                                    {health.components && Object.entries(health.components).map(([k, v]) => (
                                        <div key={k} style={{ marginBottom: 8 }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: 4 }}>
                                                <span style={{ textTransform: 'capitalize' }}>{k.replace('_', ' ')}</span>
                                                <span style={{ color: v.score >= 80 ? 'var(--accent-green)' : v.score >= 50 ? 'var(--accent-amber)' : 'var(--accent-red)' }}>
                                                    {v.score}%
                                                </span>
                                            </div>
                                            <div className="progress-bar">
                                                <div className={`progress-fill ${v.score >= 80 ? 'green' : v.score >= 50 ? 'amber' : 'red'}`}
                                                    style={{ width: `${v.score}%` }} />
                                            </div>
                                            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 2 }}>{v.detail}</div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {container && !container.error && (
                                <div className="card">
                                    <div className="card-header">
                                        <h3 className="card-title"><Cpu size={18} /> Container</h3>
                                        <span className={`badge ${container.status === 'running' ? 'badge-green' : ''}`}>
                                            {container.status}
                                        </span>
                                    </div>
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                                        <div>
                                            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Image</div>
                                            <div style={{ fontSize: '0.85rem', fontFamily: 'monospace' }}>{container.image || '—'}</div>
                                        </div>
                                        <div>
                                            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Restart Count</div>
                                            <div style={{ fontSize: '0.85rem' }}>{container.restart_count}</div>
                                        </div>
                                        {container.resources?.cpu_pct !== undefined && (
                                            <>
                                                <div>
                                                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>CPU</div>
                                                    <div style={{ fontSize: '0.85rem' }}>{container.resources.cpu_pct}%</div>
                                                </div>
                                                <div>
                                                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>RAM</div>
                                                    <div style={{ fontSize: '0.85rem' }}>
                                                        {container.resources.memory_usage_mb}MB / {container.resources.memory_limit_mb}MB
                                                    </div>
                                                </div>
                                                <div>
                                                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Net TX</div>
                                                    <div style={{ fontSize: '0.85rem' }}>{container.resources.network_tx_mb} MB</div>
                                                </div>
                                                <div>
                                                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Net RX</div>
                                                    <div style={{ fontSize: '0.85rem' }}>{container.resources.network_rx_mb} MB</div>
                                                </div>
                                            </>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Stats */}
                        {stats && !stats.error && (
                            <div className="card">
                                <div className="card-header">
                                    <h3 className="card-title"><Wifi size={18} /> WPEX Stats</h3>
                                </div>
                                <div className="kpi-grid">
                                    <div className="kpi-card">
                                        <div className="kpi-label">Total Handshakes</div>
                                        <div className="kpi-value purple">{stats.total_handshakes || 0}</div>
                                    </div>
                                    <div className="kpi-card">
                                        <div className="kpi-label">Successful</div>
                                        <div className="kpi-value green">{stats.successful_handshakes || 0}</div>
                                    </div>
                                    <div className="kpi-card">
                                        <div className="kpi-label">Active Sessions</div>
                                        <div className="kpi-value blue">{stats.active_sessions || 0}</div>
                                    </div>
                                    <div className="kpi-card">
                                        <div className="kpi-label">Data Transferred</div>
                                        <div className="kpi-value">{Math.round((stats.total_bytes_transferred || 0) / 1024)} KB</div>
                                    </div>
                                </div>
                            </div>
                        )}


                    </>
                ) : tab === 'diagnostics' ? (
                    <div className="card">
                        <div className="card-header">
                            <h3 className="card-title"><Terminal size={18} /> Diagnostica Remota</h3>
                        </div>
                        <div className="form-row">
                            <div className="form-group" style={{ flex: 3 }}>
                                <label>Target (IP o hostname)</label>
                                <input className="input" value={diagTarget} onChange={e => setDiagTarget(e.target.value)}
                                    placeholder="8.8.8.8" />
                            </div>
                            <div className="form-group" style={{ flex: 2, justifyContent: 'flex-end', flexDirection: 'row', gap: 8, alignItems: 'flex-end' }}>
                                <button className="btn btn-primary" onClick={handlePing} disabled={diagLoading}>
                                    {diagLoading ? 'Running...' : 'Ping'}
                                </button>
                                <button className="btn" onClick={handleTraceroute} disabled={diagLoading}>
                                    Traceroute
                                </button>
                            </div>
                        </div>
                        {diagResult && (
                            <div className="diag-panel" style={{ marginTop: 16 }}>
                                <div className="diag-output">
                                    {diagResult.output || diagResult.error || 'Nessun output'}
                                </div>
                            </div>
                        )}
                    </div>
                ) : tab === 'logs' ? (
                    <div className="card">
                        <div className="card-header">
                            <h3 className="card-title"><Terminal size={18} /> Logs</h3>
                            <button className="btn btn-sm" onClick={loadLogs}><RefreshCw size={14} /></button>
                        </div>
                        <div className="code-block" style={{ maxHeight: 500 }}>
                            {logs?.logs || 'Nessun log disponibile'}
                        </div>
                    </div>
                ) : null}
            </div>
        </div>
    );
}
