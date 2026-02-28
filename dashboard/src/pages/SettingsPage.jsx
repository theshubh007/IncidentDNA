import { useState } from 'react';
import { useApp } from '../hooks/useAppContext';
import { Settings as SettingsIcon, Check, AlertCircle, Plug, Shield, Bell, Clock } from 'lucide-react';

const CONNECTIONS = [
    { id: 'snowflake', name: 'Snowflake', status: 'connected', detail: 'INCIDENTDNA · COMPUTE_WH', icon: '❄️' },
    { id: 'composio-github', name: 'GitHub (Composio)', status: 'connected', detail: 'org/incidents · 3 triggers enabled', icon: '🐙' },
    { id: 'composio-slack', name: 'Slack (Composio)', status: 'connected', detail: '#incident-alerts · WebSocket active', icon: '💬' },
    { id: 'crewai', name: 'CrewAI Engine', status: 'connected', detail: '5 agents, hierarchical process', icon: '🤖' },
];

const POLICIES = [
    { id: 'auto-act-threshold', label: 'Auto-Act Confidence Threshold', value: '85%', description: 'Minimum confidence to auto-execute actions without human review' },
    { id: 'debate-rounds', label: 'Max Debate Rounds', value: '2', description: 'Maximum Ag2↔Ag5 validation rounds before Manager override' },
    { id: 'agent-timeout', label: 'Agent Timeout', value: '30s', description: 'Per-agent execution timeout before fallback' },
    { id: 'idempotency', label: 'Idempotency Check', value: 'Enabled', description: 'Dedup check on AI.ACTIONS before every external call' },
    { id: 'friday-deploy', label: 'Friday Deploy Warning', value: 'Enabled', description: 'Additional risk factor for deploys on Fridays after 3 PM' },
    { id: 'blast-radius-threshold', label: 'Blast Radius Alert Threshold', value: '≥2 services', description: 'Auto-escalate when predicted blast radius exceeds threshold' },
];

export default function SettingsPage() {
    const { addToast } = useApp();

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
                        {CONNECTIONS.map(conn => (
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
                        {POLICIES.map(policy => (
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
