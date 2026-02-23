import { useState, useEffect, useRef } from 'react';
import Sidebar from '../components/Sidebar';
import { api } from '../api';
import { Map, RefreshCw, Filter, ZoomIn, ZoomOut } from 'lucide-react';

export default function TopologyMap() {
    const [topology, setTopology] = useState(null);
    const [loading, setLoading] = useState(true);
    const [selectedNode, setSelectedNode] = useState(null);
    const [filter, setFilter] = useState('all');
    const svgRef = useRef(null);

    const loadData = async () => {
        try {
            const data = await api.getTopologyData();
            setTopology(data);
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    };

    useEffect(() => { loadData(); }, []);

    useEffect(() => {
        if (!topology || !svgRef.current) return;
        renderTopology();
    }, [topology, filter]);

    const renderTopology = () => {
        const svg = svgRef.current;
        if (!svg) return;

        // Clear
        while (svg.firstChild) svg.removeChild(svg.firstChild);

        const width = svg.clientWidth || 800;
        const height = svg.clientHeight || 600;
        const centerX = width / 2;
        const centerY = height / 2;

        const nodes = topology.nodes || [];
        const edges = topology.edges || [];

        // Filter edges
        const filteredEdges = filter === 'all' ? edges : edges.filter(e => e.status === filter);
        const connectedNodeIds = new Set();
        filteredEdges.forEach(e => { connectedNodeIds.add(e.source); connectedNodeIds.add(e.target); });
        const filteredNodes = filter === 'all' ? nodes : nodes.filter(n => connectedNodeIds.has(n.id));

        // Collect unique tenants to create cluster centers
        const tenantClusters = {};
        let tCount = 0;
        filteredNodes.forEach(n => {
            const tId = n.data?.tenant_id || 0;
            if (!tenantClusters[tId]) {
                tenantClusters[tId] = { id: tId, nodes: [], index: tCount++ };
            }
            tenantClusters[tId].nodes.push(n);
        });

        const nodePositions = {};
        const numClusters = Object.keys(tenantClusters).length;

        // Layout per cluster
        Object.values(tenantClusters).forEach(cluster => {
            // Cluster center
            let cx = centerX;
            let cy = centerY;

            if (numClusters > 1) {
                // Distribute clusters in a macro-ring
                const macroAngle = (2 * Math.PI * cluster.index) / numClusters;
                const macroRadius = Math.min(width, height) * 0.28;
                cx = centerX + macroRadius * Math.cos(macroAngle);
                cy = centerY + macroRadius * Math.sin(macroAngle);

                // Draw an underlay circle for the tenant cluster to visually segregate it
                const gBg = document.createElementNS('http://www.w3.org/2000/svg', 'g');

                const bgCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                bgCircle.setAttribute('cx', cx);
                bgCircle.setAttribute('cy', cy);
                bgCircle.setAttribute('r', Math.min(width, height) * 0.2);
                bgCircle.setAttribute('fill', 'rgba(124, 106, 239, 0.03)');
                bgCircle.setAttribute('stroke', 'rgba(124, 106, 239, 0.1)');
                bgCircle.setAttribute('stroke-width', '1');
                gBg.appendChild(bgCircle);

                const tLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                tLabel.setAttribute('x', cx);
                tLabel.setAttribute('y', cy - Math.min(width, height) * 0.2 - 10);
                tLabel.setAttribute('text-anchor', 'middle');
                tLabel.setAttribute('fill', 'var(--text-muted)');
                tLabel.setAttribute('font-size', '12');
                tLabel.setAttribute('font-weight', '600');
                tLabel.setAttribute('opacity', '0.6');
                const tName = cluster.nodes.find(n => n.data?.tenant)?.data?.tenant || (cluster.id == 0 ? "Globale" : `Tenant #${cluster.id}`);
                tLabel.textContent = tName;
                gBg.appendChild(tLabel);

                svg.appendChild(gBg);
            }

            const cRelays = cluster.nodes.filter(n => n.type === 'relay');
            const cSites = cluster.nodes.filter(n => n.type === 'site');

            // Position relays near center of cluster
            cRelays.forEach((n, i) => {
                const angle = (2 * Math.PI * i) / Math.max(cRelays.length, 1) - Math.PI / 2;
                const r = numClusters > 1 ? 40 : Math.min(width, height) * 0.15;
                nodePositions[n.id] = { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
            });

            // Position sites on outer edge of cluster
            cSites.forEach((n, i) => {
                const angle = (2 * Math.PI * i) / Math.max(cSites.length, 1);
                const r = numClusters > 1 ? 100 : Math.min(width, height) * 0.35;
                nodePositions[n.id] = { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
            });
        });

        // Draw edges
        filteredEdges.forEach(e => {
            const from = nodePositions[e.source];
            const to = nodePositions[e.target];
            if (!from || !to) return;

            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', from.x);
            line.setAttribute('y1', from.y);
            line.setAttribute('x2', to.x);
            line.setAttribute('y2', to.y);
            line.setAttribute('class', `topo-edge ${e.status || ''}`);
            svg.appendChild(line);
        });

        // Draw nodes
        filteredNodes.forEach(n => {
            const pos = nodePositions[n.id];
            if (!pos) return;

            const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            g.style.cursor = 'pointer';
            g.addEventListener('click', () => setSelectedNode(n));

            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('cx', pos.x);
            circle.setAttribute('cy', pos.y);
            circle.setAttribute('r', n.type === 'relay' ? 18 : 12);
            circle.setAttribute('class', n.type === 'relay' ? 'topo-node-relay' : 'topo-node-site');
            g.appendChild(circle);

            // Icon text
            const icon = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            icon.setAttribute('x', pos.x);
            icon.setAttribute('y', pos.y + 4);
            icon.setAttribute('text-anchor', 'middle');
            icon.setAttribute('fill', '#fff');
            icon.setAttribute('font-size', n.type === 'relay' ? '14' : '10');
            icon.setAttribute('font-weight', 'bold');
            icon.textContent = n.type === 'relay' ? 'R' : 'S';
            g.appendChild(icon);

            const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            label.setAttribute('x', pos.x);
            label.setAttribute('y', pos.y + (n.type === 'relay' ? 32 : 26));
            label.setAttribute('class', 'topo-label');
            label.textContent = n.label;
            g.appendChild(label);

            svg.appendChild(g);
        });
    };

    return (
        <div className="page">
            <Sidebar />
            <div className="main-content">
                <div className="page-header">
                    <h1 className="page-title"><Map size={26} /> Topology Map</h1>
                    <div style={{ display: 'flex', gap: 8 }}>
                        <select className="select" style={{ width: 160 }} value={filter}
                            onChange={e => setFilter(e.target.value)}>
                            <option value="all">Tutti</option>
                            <option value="active">Attivi</option>
                            <option value="degraded">Degradati</option>
                            <option value="down">Down</option>
                        </select>
                        <button className="btn btn-sm" onClick={loadData}><RefreshCw size={14} /></button>
                    </div>
                </div>

                {loading ? (
                    <div className="loading-screen"><div className="spinner" /></div>
                ) : (
                    <>
                        <div className="topology-container">
                            <svg ref={svgRef} style={{ width: '100%', height: '100%' }} />

                            {/* Legend */}
                            <div style={{ position: 'absolute', bottom: 16, left: 16, display: 'flex', gap: 16, fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                                <span><span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', background: 'var(--accent-purple)', marginRight: 4 }} /> Relay</span>
                                <span><span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', background: 'var(--accent-blue)', marginRight: 4 }} /> Site</span>
                                <span><span style={{ display: 'inline-block', width: 20, height: 2, background: 'var(--accent-green)', marginRight: 4, verticalAlign: 'middle' }} /> Active</span>
                                <span><span style={{ display: 'inline-block', width: 20, height: 2, background: 'var(--accent-amber)', marginRight: 4, verticalAlign: 'middle' }} /> Degraded</span>
                                <span><span style={{ display: 'inline-block', width: 20, height: 2, background: 'var(--accent-red)', marginRight: 4, verticalAlign: 'middle', borderTop: '2px dashed var(--accent-red)' }} /> Down</span>
                            </div>
                        </div>

                        {/* Selected Node Info */}
                        {selectedNode && (
                            <div className="card" style={{ marginTop: 16 }}>
                                <div className="card-header">
                                    <h3 className="card-title">{selectedNode.label}</h3>
                                    <span className="badge">{selectedNode.type}</span>
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 12 }}>
                                    {Object.entries(selectedNode.data || {}).map(([k, v]) => (
                                        <div key={k}>
                                            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{k}</div>
                                            <div style={{ fontSize: '0.85rem' }}>{v || '—'}</div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {(!topology?.nodes?.length) && (
                            <div className="empty-state" style={{ marginTop: 20 }}>
                                <Map size={48} />
                                <h3>Nessun nodo nella topologia</h3>
                                <p>Aggiungi relay, tenant e siti per visualizzare la mappa</p>
                            </div>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
