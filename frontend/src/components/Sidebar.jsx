import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import {
    LayoutDashboard, Map, Server, Link2, Users,
    Key, Settings, FileText, Shield, LogOut, User, ChevronDown, ChevronRight, Activity, Menu, X
} from 'lucide-react';
import { useState } from 'react';

const NAV_ITEMS = [
    { to: '/dashboard', icon: LayoutDashboard, label: 'Overview', roles: ['admin', 'executive', 'engineer'] },
    { to: '/topology', icon: Map, label: 'Topology', roles: ['admin', 'engineer'] },
    { divider: true },
    { to: '/relays', icon: Server, label: 'Relays', roles: ['admin', 'engineer'] },
    { to: '/tenants', icon: Users, label: 'Tenants', roles: ['admin'] },
    { to: '/keys', icon: Key, label: 'Chiavi', roles: ['admin', 'engineer'] },
    { divider: true },
    { to: '/zabbix', icon: Activity, label: 'Zabbix Monitor', roles: ['admin', 'engineer'] },
    { to: '/audit', icon: FileText, label: 'Audit Log', roles: ['admin'] },
    { to: '/settings', icon: Shield, label: 'Settings', roles: ['admin', 'engineer'] },
];

export default function Sidebar() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [collapsed, setCollapsed] = useState(false);
    const [mobileOpen, setMobileOpen] = useState(false);
    const userRole = user?.role || 'engineer';

    const handleLogout = async () => {
        await logout();
        navigate('/');
    };

    const filteredItems = NAV_ITEMS.filter(item =>
        item.divider || !item.roles || item.roles.includes(userRole)
    );

    const toggleMobileMenu = () => setMobileOpen(!mobileOpen);
    const closeMobileMenu = () => setMobileOpen(false);

    return (
        <>
            <div className={`sidebar-overlay ${mobileOpen ? 'open' : ''}`} onClick={closeMobileMenu} />
            <button className="mobile-menu-btn" onClick={toggleMobileMenu} style={{ position: 'fixed', top: 24, left: 16, zIndex: 99 }}>
                <Menu size={24} />
            </button>
            <nav className={`sidebar ${collapsed ? 'collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`}>
                <div className="sidebar-brand" onClick={() => setCollapsed(!collapsed)}>
                    <Activity size={22} className="brand-icon" />
                    {!collapsed && <span>WPEX SaaS</span>}
                </div>

                <div className="sidebar-nav">
                    {filteredItems.map((item, i) =>
                        item.divider ? (
                            <div key={`d-${i}`} className="sidebar-divider" />
                        ) : (
                            <NavLink key={item.to} to={item.to}
                                onClick={closeMobileMenu}
                                className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
                                <item.icon size={18} />
                                {!collapsed && <span>{item.label}</span>}
                            </NavLink>
                        )
                    )}
                </div>

                <div className="sidebar-user">
                    <div className="user-info">
                        <User size={16} />
                        {!collapsed && (
                            <div className="user-details">
                                <span className="user-name">{user?.username}</span>
                                <span className="user-role">{userRole}</span>
                            </div>
                        )}
                    </div>
                    <button className="btn btn-sm btn-icon" onClick={handleLogout} title="Logout">
                        <LogOut size={14} />
                    </button>
                </div>
            </nav>
        </>
    );
}
