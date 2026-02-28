import { useLocation, useNavigate } from 'react-router-dom';
import { useApp } from '../hooks/useAppContext';
import {
    LayoutDashboard, AlertTriangle, Rocket, Server,
    BookOpen, FileText, ScrollText, Settings,
    ChevronLeft, ChevronRight, Shield
} from 'lucide-react';

const NAV_ITEMS = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard, path: '/' },
    { id: 'incidents', label: 'Incidents', icon: AlertTriangle, path: '/incidents' },
    { id: 'releases', label: 'Releases', icon: Rocket, path: '/releases' },
    { id: 'services', label: 'Services', icon: Server, path: '/services' },
    { id: 'runbooks', label: 'Runbooks', icon: BookOpen, path: '/runbooks' },
    { id: 'postmortems', label: 'Postmortems', icon: FileText, path: '/postmortems' },
    { id: 'audit', label: 'Audit Log', icon: ScrollText, path: '/audit' },
    { id: 'settings', label: 'Settings', icon: Settings, path: '/settings' },
];

export default function Sidebar() {
    const { sidebarCollapsed, setSidebarCollapsed, simulationState } = useApp();
    const location = useLocation();
    const navigate = useNavigate();

    const pipelineStatus = simulationState ? 'degraded' : 'healthy';
    const pipelineLabel = simulationState ? 'Processing' : 'Pipeline Healthy';

    return (
        <>
            {/* Collapse toggle — positioned OUTSIDE the sidebar so overflow:hidden doesn't clip it */}
            <button
                className={`sidebar-collapse-btn${sidebarCollapsed ? ' is-collapsed' : ''}`}
                onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
                style={{
                    position: 'fixed',
                    left: sidebarCollapsed ? 'calc(var(--sidebar-collapsed) - 12px)' : 'calc(var(--sidebar-width) - 12px)',
                    top: '28px',
                    zIndex: 102,
                    transition: 'left 220ms cubic-bezier(0.4, 0, 0.2, 1)',
                }}
            >
                {sidebarCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
            </button>

            <aside className={`sidebar${sidebarCollapsed ? ' collapsed' : ''}`}>
                <div className="sidebar-header">
                    <div className="sidebar-logo">
                        <Shield size={16} />
                    </div>
                    <div className="sidebar-brand">
                        <h1>ReleaseShield</h1>
                        <span>Autonomous Safety</span>
                    </div>
                </div>

                <nav className="sidebar-nav">
                    <div className="sidebar-section-label">Navigation</div>
                    {NAV_ITEMS.map(item => {
                        const Icon = item.icon;
                        const isActive = item.path === '/'
                            ? location.pathname === '/'
                            : location.pathname.startsWith(item.path);

                        return (
                            <button
                                key={item.id}
                                className={`sidebar-link${isActive ? ' active' : ''}`}
                                onClick={() => navigate(item.path)}
                                id={`nav-${item.id}`}
                                title={item.label}
                            >
                                <Icon size={18} />
                                <span className="link-text">{item.label}</span>
                            </button>
                        );
                    })}
                </nav>

                <div className="sidebar-footer">
                    <div className="sidebar-status">
                        <span className={`status-dot ${pipelineStatus}`} />
                        <span>{pipelineLabel}</span>
                    </div>
                </div>
            </aside>
        </>
    );
}
