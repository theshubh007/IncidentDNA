import { useApp } from '../hooks/useAppContext';
import { Search, Bell, Zap, User } from 'lucide-react';

export default function Toolbar() {
    const {
        sidebarCollapsed, environment, setEnvironment,
        setSimulationModalOpen, simulationState
    } = useApp();

    return (
        <header className={`toolbar${sidebarCollapsed ? ' sidebar-collapsed' : ''}`}>
            <div className="toolbar-left">
                <div className="toolbar-search" role="button" tabIndex={0} id="global-search">
                    <Search size={14} />
                    <span>Search incidents, services…</span>
                    <kbd>⌘K</kbd>
                </div>
            </div>

            <div className="toolbar-right">
                <div className="env-switch">
                    <button
                        className={environment === 'prod' ? 'active' : ''}
                        onClick={() => setEnvironment('prod')}
                        id="env-prod"
                    >
                        Prod
                    </button>
                    <button
                        className={environment === 'staging' ? 'active' : ''}
                        onClick={() => setEnvironment('staging')}
                        id="env-staging"
                    >
                        Staging
                    </button>
                </div>

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
