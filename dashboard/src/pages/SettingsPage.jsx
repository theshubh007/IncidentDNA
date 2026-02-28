import { useState, useEffect } from 'react';
import { useApp } from '../hooks/useAppContext';
import { fetchSettings } from '../services/api';
import { SETTINGS_DATA } from '../data/mockData';
import { Settings as SettingsIcon, Check, AlertCircle, Plug, Shield, Bell, Clock } from 'lucide-react';

export default function SettingsPage() {
    const { addToast } = useApp();
    const [settings, setSettings] = useState(SETTINGS_DATA);

    useEffect(() => {
        let cancelled = false;
        const load = async () => {
            const data = await fetchSettings();
            if (!cancelled && data) setSettings(data);
        };
        load();
        return () => { cancelled = true; };
    }, []);

    const connections = settings.connections || [];
    const policies = settings.policies || [];

    return (
        <div id="settings-page">
            <div className="page-header">
                <div>
                    <h1>Settings</h1>
                    <p className="page-subtitle">Tool connections, policies & agent configuration</p>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-6)' }}>
                {/* Connections */}
                <div>
                    <h2 className="heading-md" style={{ marginBottom: 'var(--space-4)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Plug size={16} /> Tool Connections
                    </h2>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {connections.map(conn => (
                            <div key={conn.id} className="card" id={`connection-${conn.id}`}>
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                        <span style={{ fontSize: '20px' }}>{conn.icon}</span>
                                        <div>
                                            <div style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-primary)' }}>{conn.name}</div>
                                            <div className="body-xs">{conn.detail}</div>
                                        </div>
                                    </div>
                                    <span className={`status-chip ${conn.status === 'connected' ? 'sent' : 'failed'}`}>
                                        <span className="chip-dot" />
                                        {conn.status}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Policies */}
                <div>
                    <h2 className="heading-md" style={{ marginBottom: 'var(--space-4)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Shield size={16} /> Agent Policies
                    </h2>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {policies.map(policy => (
                            <div key={policy.id} className="card" id={`policy-${policy.id}`}>
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                                    <span style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text-primary)' }}>{policy.label}</span>
                                    <span style={{
                                        fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 600,
                                        padding: '2px 8px', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-sm)',
                                    }}>
                                        {policy.value}
                                    </span>
                                </div>
                                <p className="body-xs">{policy.description}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
