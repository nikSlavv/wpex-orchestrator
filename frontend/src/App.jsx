import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './AuthContext';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import Dashboard from './pages/Dashboard';
import NetworkView from './pages/NetworkView';
import RelayView from './pages/RelayView';
import TopologyMap from './pages/TopologyMap';
import TenantsPage from './pages/TenantsPage';
import TunnelList from './pages/TunnelList';
import KeysPage from './pages/KeysPage';
import ConfigManager from './pages/ConfigManager';
import AuditLog from './pages/AuditLog';
import SettingsPage from './pages/SettingsPage';

function ProtectedRoute({ children }) {
    const { user, loading } = useAuth();
    if (loading) return <div className="loading-screen"><div className="spinner" /></div>;
    return user ? children : <Navigate to="/login" />;
}

export default function App() {
    const { user, loading } = useAuth();

    if (loading) return <div className="loading-screen"><div className="spinner" /></div>;

    return (
        <Routes>
            <Route path="/" element={user ? <Navigate to="/dashboard" /> : <LandingPage />} />
            <Route path="/login" element={user ? <Navigate to="/dashboard" /> : <LoginPage />} />
            <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/network" element={<ProtectedRoute><NetworkView /></ProtectedRoute>} />
            <Route path="/relays" element={<ProtectedRoute><NetworkView /></ProtectedRoute>} />
            <Route path="/relays/:id" element={<ProtectedRoute><RelayView /></ProtectedRoute>} />
            <Route path="/server/:name" element={<ProtectedRoute><RelayView /></ProtectedRoute>} />
            <Route path="/topology" element={<ProtectedRoute><TopologyMap /></ProtectedRoute>} />
            <Route path="/tenants" element={<ProtectedRoute><TenantsPage /></ProtectedRoute>} />
            <Route path="/tunnels" element={<ProtectedRoute><TunnelList /></ProtectedRoute>} />
            <Route path="/keys" element={<ProtectedRoute><KeysPage /></ProtectedRoute>} />
            <Route path="/config" element={<ProtectedRoute><ConfigManager /></ProtectedRoute>} />
            <Route path="/audit" element={<ProtectedRoute><AuditLog /></ProtectedRoute>} />
            <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
            <Route path="*" element={<Navigate to="/" />} />
        </Routes>
    );
}
