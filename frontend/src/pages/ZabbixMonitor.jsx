import { useState, useEffect, useCallback } from 'react';
import {
    Activity, RefreshCw, Box, Cpu, HardDrive,
    Wifi, AlertCircle, CheckCircle, XCircle, ChevronDown, ChevronUp, Image,
    Router, Clock, Signal, Globe
} from 'lucide-react';
import Sidebar from '../components/Sidebar';
import { api } from '../api';
import { useAuth } from '../AuthContext';
import {
    AreaChart, Area,
    XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid
} from 'recharts';

// ── helpers ──────────────────────────────────────────────────────────
const toMB = (b) => b ? (Number(b) / 1024 / 1024).toFixed(1) : '0';
const toTime = (clock) => new Date(clock * 1000).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
const pct = (usage, limit) => limit && Number(limit) > 0 ? ((Number(usage) / Number(limit)) * 100).toFixed(1) : null;

function formatUptime(seconds) {
    if (!seconds) return '—';
    const s = Number(seconds);
    const d = Math.floor(s / 86400);
    const h = Math.floor((s % 86400) / 3600);
    const m = Math.floor((s % 3600) / 60);
    if (d > 0) return `${d}g ${h}h`;
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
}

function parseItems(items) {
    const summary = { running: 0, stopped: 0, total: 0, images: 0 };
    const containers = {};

    for (const item of items) {
        const { key_, lastvalue, itemid, value_type } = item;

        if (key_ === 'docker.containers.running') { summary.running = Number(lastvalue) || 0; continue; }
        if (key_ === 'docker.containers.stopped') { summary.stopped = Number(lastvalue) || 0; continue; }
        if (key_ === 'docker.containers.total') { summary.total = Number(lastvalue) || 0; continue; }
        if (key_ === 'docker.images.total' || key_ === 'docker.images') { summary.images = Number(lastvalue) || 0; continue; }

        const ensure = (name) => {
            if (!containers[name]) containers[name] = { name };
            return containers[name];
        };

        let m;
        if ((m = key_.match(/^docker\.containers\[(.+),State\.Status\]$/))) { ensure(m[1]).status = lastvalue; }
        else if ((m = key_.match(/^docker\.containers\[(.+),Name\]$/))) { ensure(m[1]).label = lastvalue?.replace(/^\//, ''); }
        else if ((m = key_.match(/^docker\.cpu\.util\[(.+)\]$/))) { ensure(m[1]).cpu = Number(lastvalue || 0).toFixed(1); ensure(m[1]).itemid_cpu = itemid; ensure(m[1]).vt_cpu = value_type; }
        else if ((m = key_.match(/^docker\.mem\[(.+),usage\]$/))) { ensure(m[1]).mem_usage = lastvalue; ensure(m[1]).itemid_mem = itemid; ensure(m[1]).vt_mem = value_type; }
        else if ((m = key_.match(/^docker\.mem\[(.+),limit\]$/))) { ensure(m[1]).mem_limit = lastvalue; }
        else if ((m = key_.match(/^docker\.mem\[(.+),usage_pct\]$/))) { ensure(m[1]).mem_pct = Number(lastvalue || 0).toFixed(1); }
        else if ((m = key_.match(/^docker\.net\.if\.in\[(.+),.+,bytes\]$/))) { ensure(m[1]).net_in = lastvalue; ensure(m[1]).itemid_net_in = itemid; ensure(m[1]).vt_net = value_type; }
        else if ((m = key_.match(/^docker\.net\.if\.out\[(.+),.+,bytes\]$/))) { ensure(m[1]).net_out = lastvalue; ensure(m[1]).itemid_net_out = itemid; }
    }

    return {
        summary,
        containers: Object.values(containers).map(c => ({
            ...c,
            displayName: c.label || c.name,
            memPct: c.mem_pct || pct(c.mem_usage, c.mem_limit),
        })).sort((a, b) => (a.displayName || '').localeCompare(b.displayName || '')),
    };
}

// ── sub-components ────────────────────────────────────────────────────
function SummaryCard({ icon: Icon, label, value, color }) {
    return (
        <div className="kpi-card">
            <div className="kpi-label"><Icon size={14} /> {label}</div>
            <div className={`kpi-value ${color}`}>{value}</div>
        </div>
    );
}

function StatusBadge({ status }) {
    if (status === 'running')
        return <span style={{ color: 'var(--accent-green)', fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: 4 }}><CheckCircle size={12} /> running</span>;
    if (status === 'exited' || status === 'stopped')
        return <span style={{ color: 'var(--accent-red)', fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: 4 }}><XCircle size={12} /> {status}</span>;
    return <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>{status || '—'}</span>;
}

function MiniBar({ value, max = 100, color = '#34d399' }) {
    const pctVal = Math.min(Number(value) || 0, max);
    const barColor = pctVal > 80 ? '#f87171' : pctVal > 60 ? '#fbbf24' : color;
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ flex: 1, background: 'var(--bg-card-alt)', borderRadius: 4, height: 6, overflow: 'hidden' }}>
                <div style={{ width: `${pctVal}%`, height: '100%', background: barColor, borderRadius: 4, transition: 'width 0.3s' }} />
            </div>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', minWidth: 36 }}>{Number(value || 0).toFixed(1)}%</span>
        </div>
    );
}

const CHART_STYLE = { fontSize: '0.72rem' };
const TOOLTIP_STYLE = { background: '#1e2535', border: '1px solid #2d3748', borderRadius: 8, fontSize: '0.78rem' };

function ContainerChart({ title, itemid, valueType, transform, unit, color }) {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!itemid) return;
        setLoading(true);
        api.getItemHistory(itemid, 1, valueType)
            .then(raw => setData(raw.map(p => ({ time: toTime(p.clock), value: parseFloat(transform ? transform(p.value) : p.value) }))))
            .catch(() => setData([]))
            .finally(() => setLoading(false));
    }, [itemid]);

    if (!itemid) return null;

    return (
        <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>{title}</div>
            {loading ? (
                <div style={{ height: 120, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.78rem' }}>Caricamento…</div>
            ) : data.length === 0 ? (
                <div style={{ height: 80, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.78rem' }}>Nessun dato storico</div>
            ) : (
                <ResponsiveContainer width="100%" height={140}>
                    <AreaChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                        <defs>
                            <linearGradient id={`grad-${color}`} x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                                <stop offset="95%" stopColor={color} stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis dataKey="time" tick={CHART_STYLE} minTickGap={30} stroke="transparent" />
                        <YAxis tick={CHART_STYLE} stroke="transparent" unit={unit} />
                        <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v) => [`${v}${unit}`, title]} />
                        <Area type="monotone" dataKey="value" stroke={color} fill={`url(#grad-${color})`} dot={false} strokeWidth={2} />
                    </AreaChart>
                </ResponsiveContainer>
            )}
        </div>
    );
}

function ContainerCard({ c }) {
    const [expanded, setExpanded] = useState(false);

    return (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            {/* Header row */}
            <div
                onClick={() => setExpanded(e => !e)}
                style={{ padding: '14px 18px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12, userSelect: 'none' }}
            >
                <Box size={16} style={{ color: c.status === 'running' ? 'var(--accent-green)' : 'var(--accent-red)', flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, fontSize: '0.88rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {c.displayName || c.name}
                    </div>
                    <StatusBadge status={c.status} />
                </div>

                {/* CPU bar */}
                <div style={{ width: 120, flexShrink: 0 }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 3 }}><Cpu size={10} /> CPU</div>
                    <MiniBar value={c.cpu} color="#60a5fa" />
                </div>

                {/* RAM bar */}
                <div style={{ width: 120, flexShrink: 0 }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 3 }}><HardDrive size={10} /> RAM</div>
                    {c.memPct
                        ? <MiniBar value={c.memPct} color="#a78bfa" />
                        : <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{toMB(c.mem_usage)} MB</span>
                    }
                </div>

                {/* Net */}
                <div style={{ width: 100, flexShrink: 0, textAlign: 'right' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}><Wifi size={10} /> Net</div>
                    <div style={{ fontSize: '0.75rem' }}>
                        ↑ {toMB(c.net_out)} MB<br />↓ {toMB(c.net_in)} MB
                    </div>
                </div>

                {expanded ? <ChevronUp size={16} style={{ color: 'var(--text-muted)', flexShrink: 0 }} /> : <ChevronDown size={16} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />}
            </div>

            {/* Expanded charts */}
            {expanded && (
                <div style={{ padding: '0 18px 18px', borderTop: '1px solid var(--border-color)' }}>
                    <div style={{ paddingTop: 16, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                        <ContainerChart title="CPU %" itemid={c.itemid_cpu} valueType={c.vt_cpu ?? 0} unit="%" color="#60a5fa" />
                        <ContainerChart title="RAM (MB)" itemid={c.itemid_mem} valueType={c.vt_mem ?? 3} transform={v => toMB(v)} unit=" MB" color="#a78bfa" />
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                        <ContainerChart title="Net IN (MB)" itemid={c.itemid_net_in} valueType={c.vt_net ?? 3} transform={v => toMB(v)} unit=" MB" color="#34d399" />
                        <ContainerChart title="Net OUT (MB)" itemid={c.itemid_net_out} valueType={c.vt_net ?? 3} transform={v => toMB(v)} unit=" MB" color="#fbbf24" />
                    </div>
                </div>
            )}
        </div>
    );
}

// ── device tab components ─────────────────────────────────────────────
function DeviceBadge({ available }) {
    if (available)
        return <span style={{ color: 'var(--accent-green)', fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: 4 }}><CheckCircle size={12} /> online</span>;
    return <span style={{ color: 'var(--accent-red)', fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: 4 }}><XCircle size={12} /> offline</span>;
}

function DeviceCard({ device }) {
    const [expanded, setExpanded] = useState(false);
    const m = device.metrics || {};
    const ip = device.interfaces?.find(i => i.ip && i.ip !== '0.0.0.0')?.ip || '—';
    const netIn = device.net_items?.find(i => i.direction === 'in');
    const netOut = device.net_items?.find(i => i.direction === 'out');
    const hasCharts = m.ping_itemid || m.cpu_itemid || m.mem_itemid || netIn || netOut;

    return (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div
                onClick={() => setExpanded(e => !e)}
                style={{ padding: '14px 18px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12, userSelect: 'none' }}
            >
                <Router size={16} style={{ color: device.available ? 'var(--accent-green)' : 'var(--accent-red)', flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, fontSize: '0.88rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {device.name || device.host}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <DeviceBadge available={device.available} />
                        {ip !== '—' && <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{ip}</span>}
                    </div>
                </div>

                {/* Ping ms */}
                {m.ping_ms != null && (
                    <div style={{ width: 90, flexShrink: 0, textAlign: 'right' }}>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 2 }}><Signal size={10} /> Ping</div>
                        <div style={{ fontSize: '0.82rem', fontWeight: 600, color: m.ping_ms < 10 ? 'var(--accent-green)' : m.ping_ms < 50 ? '#fbbf24' : 'var(--accent-red)' }}>
                            {Number(m.ping_ms).toFixed(1)} ms
                        </div>
                    </div>
                )}

                {/* CPU bar */}
                {m.cpu != null && (
                    <div style={{ width: 120, flexShrink: 0 }}>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 3 }}><Cpu size={10} /> CPU</div>
                        <MiniBar value={m.cpu} color="#60a5fa" />
                    </div>
                )}

                {/* Uptime */}
                {m.uptime != null && (
                    <div style={{ width: 80, flexShrink: 0, textAlign: 'right' }}>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 2 }}><Clock size={10} /> Uptime</div>
                        <div style={{ fontSize: '0.78rem' }}>{formatUptime(m.uptime)}</div>
                    </div>
                )}

                {expanded ? <ChevronUp size={16} style={{ color: 'var(--text-muted)', flexShrink: 0 }} /> : <ChevronDown size={16} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />}
            </div>

            {/* Expanded charts */}
            {expanded && (
                <div style={{ padding: '0 18px 18px', borderTop: '1px solid var(--border-color)' }}>
                    {hasCharts ? (
                        <div style={{ paddingTop: 16, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                            {m.ping_itemid && <ContainerChart title="Ping (ms)" itemid={m.ping_itemid} valueType={0} transform={v => (parseFloat(v) * 1000).toFixed(2)} unit=" ms" color="#34d399" />}
                            {m.cpu_itemid && <ContainerChart title="CPU %" itemid={m.cpu_itemid} valueType={0} unit="%" color="#60a5fa" />}
                            {m.mem_itemid && <ContainerChart title="Memoria %" itemid={m.mem_itemid} valueType={0} unit="%" color="#a78bfa" />}
                            {netIn && <ContainerChart title="Net IN (B/s)" itemid={netIn.itemid} valueType={3} unit=" B/s" color="#34d399" />}
                            {netOut && <ContainerChart title="Net OUT (B/s)" itemid={netOut.itemid} valueType={3} unit=" B/s" color="#fbbf24" />}
                        </div>
                    ) : (
                        <div style={{ padding: '16px 0', color: 'var(--text-muted)', fontSize: '0.82rem', textAlign: 'center' }}>
                            Nessun item monitorato trovato per questo host.
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

function DevicesTab() {
    const [devices, setDevices] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const load = useCallback(async () => {
        try {
            setError(null);
            const data = await api.getDevices();
            setDevices(data.filter(d => !d.is_docker));
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        load();
        const i = setInterval(load, 30000);
        return () => clearInterval(i);
    }, [load]);

    if (loading) return <div className="loading-screen"><div className="spinner" /></div>;
    if (error) return (
        <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 12, color: 'var(--accent-red)', padding: 20 }}>
            <AlertCircle size={20} /><span>{error}</span>
        </div>
    );

    const online = devices.filter(d => d.available).length;

    return (
        <>
            <div className="kpi-grid">
                <SummaryCard icon={Globe} label="Dispositivi totali" value={devices.length} color="blue" />
                <SummaryCard icon={CheckCircle} label="Online" value={online} color="green" />
                <SummaryCard icon={XCircle} label="Offline" value={devices.length - online} color={devices.length - online > 0 ? 'amber' : 'green'} />
            </div>
            <div className="card" style={{ marginTop: 24 }}>
                <div className="card-header">
                    <h3 className="card-title"><Globe size={16} /> Dispositivi ({devices.length})</h3>
                </div>
                {devices.length === 0 ? (
                    <div className="empty-state" style={{ padding: 32 }}>
                        <Globe size={40} />
                        <p>Nessun dispositivo trovato in Zabbix. Aggiungi host nella UI Zabbix.</p>
                    </div>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: '0 0 8px' }}>
                        {devices.map(d => <DeviceCard key={d.hostid} device={d} />)}
                    </div>
                )}
            </div>
        </>
    );
}

// ── Docker tab (extracted) ────────────────────────────────────────────
function DockerTab() {
    const [dockerHostId, setDockerHostId] = useState(null);
    const [summary, setSummary] = useState(null);
    const [containers, setContainers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const loadData = useCallback(async () => {
        try {
            setError(null);
            let hostId = dockerHostId;
            if (!hostId) {
                const hosts = await api.getZabbixHosts();
                const dh = hosts.find(h => h.host === 'Docker-Host' || h.name === 'Docker-Host');
                if (!dh) throw new Error('Host "Docker-Host" non trovato in Zabbix. Crealo prima nella UI.');
                hostId = dh.hostid;
                setDockerHostId(hostId);
            }
            const items = await api.getDockerStats(hostId);
            const parsed = parseItems(items);
            setSummary(parsed.summary);
            setContainers(parsed.containers);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, [dockerHostId]);

    useEffect(() => {
        loadData();
        const i = setInterval(loadData, 30000);
        return () => clearInterval(i);
    }, [loadData]);

    if (loading && !summary) return <div className="loading-screen"><div className="spinner" /></div>;
    if (error) return (
        <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 12, color: 'var(--accent-red)', padding: 20 }}>
            <AlertCircle size={20} /><span>{error}</span>
        </div>
    );

    return summary ? (
        <>
            <div className="kpi-grid">
                <SummaryCard icon={CheckCircle} label="Container Running" value={summary.running} color="green" />
                <SummaryCard icon={XCircle} label="Container Stopped" value={summary.stopped} color={summary.stopped > 0 ? 'amber' : 'green'} />
                <SummaryCard icon={Box} label="Container Totali" value={summary.total} color="blue" />
                <SummaryCard icon={Image} label="Immagini" value={summary.images} color="purple" />
            </div>
            <div className="card" style={{ marginTop: 24 }}>
                <div className="card-header">
                    <h3 className="card-title"><Box size={16} /> Container ({containers.length})</h3>
                </div>
                {containers.length === 0 ? (
                    <div className="empty-state" style={{ padding: 32 }}>
                        <Box size={40} /><p>Nessun container rilevato. Attendi il discovery di Zabbix (~5 min).</p>
                    </div>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: '0 0 8px' }}>
                        {containers.map(c => <ContainerCard key={c.name} c={c} />)}
                    </div>
                )}
            </div>
        </>
    ) : null;
}

// ── main page ─────────────────────────────────────────────────────────
export default function ZabbixMonitor() {
    const { user } = useAuth();
    const [tab, setTab] = useState('containers');

    if (user?.role !== 'admin') {
        return (
            <div className="page">
                <Sidebar />
                <div className="main-content">
                    <div className="empty-state" style={{ marginTop: 100 }}>
                        <AlertCircle size={40} style={{ color: 'var(--accent-red)', marginBottom: 16 }} />
                        <h2 style={{ color: 'var(--text)' }}>Accesso Negato</h2>
                        <p>Solo gli amministratori di sistema possono accedere al monitoraggio di infrastruttura.</p>
                    </div>
                </div>
            </div>
        );
    }

    const tabBtn = (id, label) => (
        <button
            onClick={() => setTab(id)}
            style={{
                padding: '8px 20px',
                fontSize: '0.88rem',
                fontWeight: 600,
                cursor: 'pointer',
                borderRadius: 8,
                border: 'none',
                background: tab === id ? 'var(--accent-blue)' : 'transparent',
                color: tab === id ? '#fff' : 'var(--text-muted)',
                transition: 'all 0.15s',
            }}
        >{label}</button>
    );

    return (
        <div className="page">
            <Sidebar />
            <div className="main-content">
                <div className="page-header">
                    <h1 className="page-title"><Activity size={24} /> Monitor</h1>
                    <div style={{ display: 'flex', gap: 4, background: 'var(--bg-card)', borderRadius: 10, padding: 4 }}>
                        {tabBtn('containers', 'Containers')}
                        {tabBtn('devices', 'Devices')}
                    </div>
                </div>
                {tab === 'containers' && <DockerTab />}
                {tab === 'devices' && <DevicesTab />}
            </div>
        </div>
    );
}
