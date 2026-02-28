import { useApp } from '../hooks/useAppContext';
import { Database, Clock, Hash } from 'lucide-react';

export default function Footer() {
    const { sidebarCollapsed } = useApp();
    const now = new Date();
    const refreshTime = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    return (
        <footer className={`footer${sidebarCollapsed ? ' sidebar-collapsed' : ''}`}>
            <div className="footer-item">
                <Database size={12} />
                <span>COMPUTE_WH · INCIDENTDNA</span>
            </div>
            <div className="footer-item">
                <Clock size={12} />
                <span>Last refresh: {refreshTime}</span>
            </div>
            <div className="footer-item">
                <Hash size={12} />
                <span>v1.0.0-beta · sha-a1b2c3d</span>
            </div>
        </footer>
    );
}
