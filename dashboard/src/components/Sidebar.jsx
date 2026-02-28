import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useApp } from '../hooks/useAppContext';
import {
    LayoutDashboard, AlertTriangle, Rocket, Server,
    BookOpen, FileText, ScrollText, Settings,
    ChevronLeft, ChevronRight, ChevronDown, Shield, GitBranch,
    Activity, Wrench
} from 'lucide-react';

const NAV_SECTIONS = [
    {
        id: 'main',
        label: 'Dashboard',
        icon: Activity,
        items: [
            { id: 'overview', label: 'Overview', icon: LayoutDashboard, path: '/' },
            { id: 'incidents', label: 'Incidents', icon: AlertTriangle, path: '/incidents' },
            { id: 'services', label: 'Services', icon: Server, path: '/services' },
        ],
    },
    {
        id: 'ops',
        label: 'Operations',
        icon: Wrench,
        items: [
            { id: 'releases', label: 'Releases', icon: Rocket, path: '/releases' },
            { id: 'runbooks', label: 'Runbooks', icon: BookOpen, path: '/runbooks' },
            { id: 'postmortems', label: 'Postmortems', icon: FileText, path: '/postmortems' },
            { id: 'audit', label: 'Audit Log', icon: ScrollText, path: '/audit' },
        ],
    },
    {
        id: 'config',
        label: 'Configuration',
        icon: Settings,
        items: [
            { id: 'repository', label: 'Repositories', icon: GitBranch, path: '/repository' },
            { id: 'settings', label: 'Settings', icon: Settings, path: '/settings' },
        ],
    },
];

export default function Sidebar() {
    const { sidebarCollapsed, setSidebarCollapsed, simulationState } = useApp();
    const location = useLocation();
    const navigate = useNavigate();
    const [openSections, setOpenSections] = useState({ main: true, ops: true, config: true });

    const toggleSection = (id) => {
        setOpenSections(prev => ({ ...prev, [id]: !prev[id] }));
    };

    const pipelineStatus = simulationState ? 'degraded' : 'healthy';
    const pipelineLabel = simulationState ? 'Processing' : 'Pipeline Healthy';

    return (
        <>
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
                        <span>IncidentDNA Platform</span>
                    </div>
                </div>

                <nav className="sidebar-nav">
                    {NAV_SECTIONS.map(section => {
                        const hasActive = section.items.some(item =>
                            item.path === '/' ? location.pathname === '/' : location.pathname.startsWith(item.path)
                        );
                        // Always show items if section has an active child
                        const isOpen = openSections[section.id] || hasActive;

                        return (
                            <div key={section.id} style={{ marginBottom: '6px' }}>
                                <button
                                    className="sidebar-section-toggle"
                                    onClick={() => toggleSection(section.id)}
                                    style={{
                                        display: 'flex', alignItems: 'center', gap: '8px', width: '100%',
                                        padding: '8px 16px', border: 'none', background: 'none', cursor: 'pointer',
                                        color: hasActive ? 'var(--text-primary)' : 'var(--text-tertiary)',
                                        fontSize: '10px', fontWeight: 600, textTransform: 'uppercase',
                                        letterSpacing: '0.6px', transition: 'color 150ms',
                                    }}
                                >
                                    <ChevronDown size={10} style={{
                                        transform: isOpen ? 'rotate(0deg)' : 'rotate(-90deg)',
                                        transition: 'transform 150ms',
                                    }} />
                                    <span className="link-text">{section.label}</span>
                                </button>
                                {isOpen && section.items.map(item => {
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
                                            style={{ paddingLeft: '28px' }}
                                        >
                                            <Icon size={16} />
                                            <span className="link-text">{item.label}</span>
                                        </button>
                                    );
                                })}
                            </div>
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
