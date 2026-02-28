import { useState, useEffect, useRef } from 'react';
import { useApp } from '../hooks/useAppContext';
import { fetchRepoInfo } from '../services/api';
import { Search, Bell, Zap, User, GitBranch, ChevronDown, Check } from 'lucide-react';

export default function Toolbar() {
    const {
        sidebarCollapsed,
        setSimulationModalOpen, simulationState
    } = useApp();
    const [repos, setRepos] = useState([]);
    const [selectedRepo, setSelectedRepo] = useState(null);
    const [dropdownOpen, setDropdownOpen] = useState(false);
    const dropdownRef = useRef(null);

    useEffect(() => {
        fetchRepoInfo().then(r => {
            if (r?.fullName) {
                setRepos([r]);
                setSelectedRepo(r);
            }
        });
    }, []);

    useEffect(() => {
        const close = (e) => { if (dropdownRef.current && !dropdownRef.current.contains(e.target)) setDropdownOpen(false); };
        document.addEventListener('mousedown', close);
        return () => document.removeEventListener('mousedown', close);
    }, []);

    return (
        <header className={`toolbar${sidebarCollapsed ? ' sidebar-collapsed' : ''}`}>
            <div className="toolbar-left">
                {/* Repo dropdown selector */}
                <div ref={dropdownRef} style={{ position: 'relative', marginRight: '12px' }}>
                    <button
                        onClick={() => setDropdownOpen(!dropdownOpen)}
                        style={{
                            display: 'flex', alignItems: 'center', gap: '8px',
                            padding: '5px 12px', borderRadius: '8px', border: '1px solid var(--border-primary)',
                            background: 'var(--bg-secondary)', cursor: 'pointer', fontSize: '12px', fontWeight: 600,
                            color: 'var(--text-primary)', transition: 'border-color 150ms',
                        }}
                        id="repo-selector"
                    >
                        <GitBranch size={13} style={{ color: 'var(--color-accent)' }} />
                        <span style={{ maxWidth: '220px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {selectedRepo?.fullName || 'Select Repository'}
                        </span>
                        <ChevronDown size={12} style={{ color: 'var(--text-tertiary)', transform: dropdownOpen ? 'rotate(180deg)' : 'none', transition: 'transform 150ms' }} />
                    </button>
                    {dropdownOpen && (
                        <div style={{
                            position: 'absolute', top: '100%', left: 0, marginTop: '4px', minWidth: '280px',
                            background: 'var(--bg-primary)', border: '1px solid var(--border-primary)',
                            borderRadius: '10px', boxShadow: '0 8px 24px rgba(0,0,0,0.12)', zIndex: 200,
                            overflow: 'hidden',
                        }}>
                            <div style={{ padding: '8px 12px', fontSize: '10px', fontWeight: 600, textTransform: 'uppercase', color: 'var(--text-tertiary)', letterSpacing: '0.5px' }}>
                                Linked Repositories
                            </div>
                            {repos.map(r => (
                                <button key={r.fullName} onClick={() => { setSelectedRepo(r); setDropdownOpen(false); }}
                                    style={{
                                        display: 'flex', alignItems: 'center', gap: '10px', width: '100%',
                                        padding: '8px 12px', border: 'none', background: selectedRepo?.fullName === r.fullName ? 'rgba(99,102,241,0.08)' : 'transparent',
                                        cursor: 'pointer', fontSize: '13px', color: 'var(--text-primary)', textAlign: 'left',
                                        transition: 'background 100ms',
                                    }}
                                    onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-secondary)'}
                                    onMouseLeave={e => e.currentTarget.style.background = selectedRepo?.fullName === r.fullName ? 'rgba(99,102,241,0.08)' : 'transparent'}
                                >
                                    <GitBranch size={13} style={{ color: 'var(--color-accent)', flexShrink: 0 }} />
                                    <div style={{ flex: 1, minWidth: 0 }}>
                                        <div style={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.fullName}</div>
                                        <div style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>{r.defaultBranch || 'main'}</div>
                                    </div>
                                    {selectedRepo?.fullName === r.fullName && <Check size={14} style={{ color: 'var(--color-accent)', flexShrink: 0 }} />}
                                </button>
                            ))}
                            {repos.length === 0 && (
                                <div style={{ padding: '12px', fontSize: '12px', color: 'var(--text-tertiary)', textAlign: 'center' }}>
                                    No repositories linked yet
                                </div>
                            )}
                        </div>
                    )}
                </div>
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

                <div className="user-avatar" id="user-menu" title="User menu"
                    style={{
                        width: '32px', height: '32px', borderRadius: '50%',
                        background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        cursor: 'pointer', position: 'relative', border: '2px solid rgba(99,102,241,0.3)',
                    }}
                >
                    <span style={{ fontSize: '12px', fontWeight: 700, color: '#fff', lineHeight: 1 }}>PS</span>
                    <span style={{
                        position: 'absolute', bottom: '-1px', right: '-1px',
                        width: '10px', height: '10px', borderRadius: '50%',
                        background: '#22c55e', border: '2px solid var(--bg-primary)',
                    }} />
                </div>
            </div>
        </header>
    );
}
