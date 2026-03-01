
import React, { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid } from "recharts";

const ZabbixMonitor = () => {
  const [hosts, setHosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Polling hosts ogni 30s
  useEffect(() => {
    let timer;
    const fetchHosts = () => {
      fetch("/api/zabbix/hosts")
        .then((res) => {
          if (!res.ok) throw new Error("Errore caricamento dati Zabbix");
          return res.json();
        })
        .then((data) => {
          setHosts(data);
          setLoading(false);
        })
        .catch((err) => {
          setError(err.message);
          setLoading(false);
        });
    };
    fetchHosts();
    timer = setInterval(fetchHosts, 30000);
    return () => clearInterval(timer);
  }, []);

  // Stato per traffico selezionato
  const [traffic, setTraffic] = useState({});
  const [trafficLoading, setTrafficLoading] = useState({});
  const [trafficError, setTrafficError] = useState({});

  // Carica traffico per host
  const loadTraffic = (hostid) => {
    setTrafficLoading((prev) => ({ ...prev, [hostid]: true }));
    fetch(`/api/zabbix/traffic/${hostid}`)
      .then((res) => {
        if (!res.ok) throw new Error("Errore caricamento traffico");
        return res.json();
      })
      .then((data) => {
        setTraffic((prev) => ({ ...prev, [hostid]: data }));
        setTrafficLoading((prev) => ({ ...prev, [hostid]: false }));
        setTrafficError((prev) => ({ ...prev, [hostid]: null }));
      })
      .catch((err) => {
        setTrafficError((prev) => ({ ...prev, [hostid]: err.message }));
        setTrafficLoading((prev) => ({ ...prev, [hostid]: false }));
      });
  };

  return (
    <div style={{ padding: 24 }}>
      <h2>Monitoraggio dispositivi Zabbix</h2>
      {loading && <div>Caricamento...</div>}
      {error && <div style={{ color: "red" }}>{error}</div>}
      {!loading && !error && (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th>ID</th>
              <th>Host</th>
              <th>Nome</th>
              <th>Stato</th>
              <th>Traffico</th>
            </tr>
          </thead>
          <tbody>
            {hosts.map((h) => (
              <React.Fragment key={h.hostid}>
                <tr>
                  <td>{h.hostid}</td>
                  <td>{h.host}</td>
                  <td>{h.name}</td>
                  <td>{h.status === "0" ? "Attivo" : "Disabilitato"}</td>
                  <td>
                    <button onClick={() => loadTraffic(h.hostid)} disabled={trafficLoading[h.hostid]}>
                      {trafficLoading[h.hostid] ? "Carico..." : "Mostra grafico"}
                    </button>
                  </td>
                </tr>
                {traffic[h.hostid] && (
                  <tr>
                    <td colSpan={5}>
                      {Object.entries(traffic[h.hostid]).map(([iface, samples]) => (
                        <div key={iface} style={{ margin: "16px 0" }}>
                          <h4>{iface}</h4>
                          <ResponsiveContainer width="100%" height={220}>
                            <LineChart data={samples.map(s => ({
                              ...s,
                              time: new Date(s.clock * 1000).toLocaleTimeString(),
                            }))}>
                              <CartesianGrid strokeDasharray="3 3" />
                              <XAxis dataKey="time" minTickGap={20} />
                              <YAxis />
                              <Tooltip />
                              <Legend />
                              <Line type="monotone" dataKey="value" stroke="#8884d8" dot={false} name="Valore" />
                            </LineChart>
                          </ResponsiveContainer>
                        </div>
                      ))}
                    </td>
                  </tr>
                )}
                {trafficError[h.hostid] && (
                  <tr><td colSpan={5} style={{ color: "red" }}>{trafficError[h.hostid]}</td></tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default ZabbixMonitor;
