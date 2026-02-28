import { useState, useEffect } from 'react';
import { useApp } from '../hooks/useAppContext';
import { fetchRepoInfo } from '../services/api';
import { Search, Bell, Zap, User, GitBranch } from 'lucide-react';

export default function Toolbar() {
    const {
        sidebarCollapsed,
        setSimulationModalOpen, simulationState
    } = useApp();
    const [repoName, setRepoName] = useState('');

    useEffect(() => {
        fetchRepoInfo().then(r => { if (r?.fullName) setRepoName(r.fullName); });
    }, []);

    return (
        <header className={`toolbar${sidebarCollapsed ? ' sidebar-collapsed' : ''}`}>
            <div className="toolbar-left">
                {repoName && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginRight: '16px' }}>
                        <GitBranch size={14} style={{ color: 'var(--color-accent)' }} />
                        <span style={{ fontSize: '13px', fontWeight: 600, letterSpacing: '-0.2px' }}>{repoName}</span>
                    </div>
                )}
                <div className="toolbar-search" role="button" tabIndex={0} id="global-search">
                    <Search size={14} />
                    <span>Search incidents, services…</span>
                    <kbd>⌘K</kbd>
                </div>
            </div>

            <div className="toolbar-right">
                <button
                    className={`btn-simulate${simulationState ? ' running' : ''}`}
                    onClick={() => !simulationState && setSimulationModalOpen(true)}
                    id="simulate-event-btn"
                >
                    <Zap size={14} />
                    {simulationState ? 'Running…' : 'Simulate Event'}
                </button>

                <button className="toolbar-icon-btn" id="notifications-btn" title="Notifications">
                    <Bell size={18} />
                    <span className="badge" />
                </button>

                <div className="user-avatar" id="user-menu" title="User menu">
                    <User size={14} />
                </div>
            </div>
        </header>
    );
}
