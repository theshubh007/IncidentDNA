import { useState, useMemo } from 'react';
import { INCIDENTS_DATA } from '../data/mockData';
import { useApp } from '../hooks/useAppContext';
import {
    X, Clock, GitBranch, MessageSquare, FileText,
    Check, Circle, AlertTriangle, ChevronRight, Copy, ExternalLink
} from 'lucide-react';

function SeverityChip({ severity }) {
    const map = { critical: 'critical', warning: 'warning', info: 'info' };
    return <span className={`severity-chip ${map[severity] || 'info'}`}>{severity}</span>;
}

function StatusChip({ status }) {
    const colorMap = {
        resolved: 'healthy',
        investigating: 'warning',
        detected: 'info',
        'in-progress': 'warning',
    };
    return <span className={`severity-chip ${colorMap[status] || 'info'}`}>{status}</span>;
}

function IncidentDrawer({ incident, onClose }) {
    const [activeTab, setActiveTab] = useState('timeline');

    if (!incident) return null;

    const tabs = [
        { id: 'timeline', label: 'Timeline' },
        { id: 'blast-radius', label: 'Blast Radius' },
        { id: 'patterns', label: 'Pattern Memory' },
        { id: 'actions', label: 'Actions' },
        { id: 'postmortem', label: 'Postmortem' },
    ];

    return (
        <>
            <div className="drawer-overlay" onClick={onClose} />
            <div className="drawer" id="incident-drawer">
                <div className="drawer-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{incident.id}</span>
                        <SeverityChip severity={incident.severity} />
                        <StatusChip status={incident.status} />
                    </div>
                    <button className="drawer-close" onClick={onClose}><X size={16} /></button>
                </div>

                <div style={{ padding: '0 24px' }}>
                    <p className="body-sm" style={{ padding: '12px 0 0' }}>{incident.rootCause}</p>
                    <div style={{ display: 'flex', gap: '16px', padding: '8px 0 0', fontSize: '12px', color: 'var(--text-tertiary)' }}>
                        <span>{incident.service}</span>
                        <span>Confidence: {Math.round(incident.confidence * 100)}%</span>
                        <span>{new Date(incident.detected).toLocaleString()}</span>
                    </div>
                </div>

                <div className="tabs" style={{ padding: '0 24px', marginTop: '16px' }}>
                    {tabs.map(tab => (
                        <button
                            key={tab.id}
                            className={`tab${activeTab === tab.id ? ' active' : ''}`}
                            onClick={() => setActiveTab(tab.id)}
                            id={`drawer-tab-${tab.id}`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>

                <div className="drawer-body">
                    {activeTab === 'timeline' && <TimelineTab incident={incident} />}
                    {activeTab === 'blast-radius' && <BlastRadiusTab incident={incident} />}
                    {activeTab === 'patterns' && <PatternsTab incident={incident} />}
                    {activeTab === 'actions' && <ActionsTab incident={incident} />}
                    {activeTab === 'postmortem' && <PostmortemTab incident={incident} />}
                </div>
            </div>
        </>
    );
}

function TimelineTab({ incident }) {
    return (
        <div className="stepper">
            {incident.timeline.map((step, idx) => (
                <div key={idx} className={`stepper-step ${step.status === 'complete' ? 'complete' : 'active'}`}>
                    <div className="stepper-line" />
                    <div className="stepper-dot">
                        {step.status === 'complete' ? <Check size={12} /> : <Circle size={8} fill="currentColor" />}
                    </div>
                    <div className="stepper-content">
                        <div className="stepper-label">{step.agent}</div>
                        <div className="stepper-detail">{step.action}</div>
                        <div className="stepper-timestamp">{step.time}</div>
                    </div>
                </div>
            ))}
        </div>
    );
}

function BlastRadiusTab({ incident }) {
    const br = incident.blastRadiusDetail;
    return (
        <div>
            <div className="evidence-card" style={{ marginBottom: '16px', borderLeft: '3px solid var(--color-critical)' }}>
                <div className="evidence-source">Primary Service</div>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{br.primary}</div>
            </div>
            {br.affected.length === 0 ? (
                <p className="body-sm" style={{ color: 'var(--text-tertiary)' }}>No downstream services at risk.</p>
            ) : (
                br.affected.map(a => (
                    <div key={a.service} className="evidence-card" style={{ borderLeft: `3px solid ${a.impact === 'high' ? 'var(--color-critical)' : a.impact === 'medium' ? 'var(--color-warning)' : 'var(--color-info)'}` }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{a.service}</span>
                            <span className={`risk-chip ${a.impact}`}>{a.impact}</span>
                        </div>
                        <div className="evidence-text">{a.reason}</div>
                        <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '4px' }}>ETA: {a.eta}</div>
                    </div>
                ))
            )}
        </div>
    );
}

function PatternsTab({ incident }) {
    if (!incident.patternMemory || incident.patternMemory.length === 0) {
        return <div className="empty-state"><AlertTriangle /><h3>No pattern memory</h3><p>No similar past incidents found in AI.INCIDENT_HISTORY.</p></div>;
    }
    return (
        <div>
            {incident.patternMemory.map(p => (
                <div key={p.id} className="evidence-card">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 600 }}>{p.id}</span>
                        <span className={`similarity-score ${p.similarity >= 0.9 ? 'high' : p.similarity >= 0.8 ? 'medium' : 'low'}`}>
                            {Math.round(p.similarity * 100)}%
                        </span>
                    </div>
                    <div className="body-sm"><strong>Cause:</strong> {p.cause}</div>
                    <div style={{ fontSize: '12px', color: 'var(--color-healthy)', marginTop: '4px', fontWeight: 500 }}>Fix: {p.fix}</div>
                    <div className="body-xs" style={{ marginTop: '4px' }}>{p.service} · {p.date}</div>
                </div>
            ))}
        </div>
    );
}

function ActionsTab({ incident }) {
    if (!incident.actions || incident.actions.length === 0) {
        return <div className="empty-state"><AlertTriangle /><h3>No actions</h3><p>No actions have been executed for this incident.</p></div>;
    }

    const iconMap = { slack: MessageSquare, github: GitBranch, dna_store: FileText };

    return (
        <div>
            {incident.actions.map((action, i) => {
                const Icon = iconMap[action.type] || FileText;
                return (
                    <div key={i} className="evidence-card">
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <Icon size={14} style={{ color: 'var(--text-tertiary)' }} />
                                <span style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text-primary)', textTransform: 'capitalize' }}>{action.type.replace(/_/g, ' ')}</span>
                            </div>
                            <span className={`status-chip ${action.status}`}>
                                <span className="chip-dot" />
                                {action.status}
                            </span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span className="body-xs">{action.target}</span>
                            <span className="body-xs">{action.timestamp}</span>
                        </div>
                        {action.receipt && (
                            <div className="log-line" style={{ marginTop: '6px', padding: '4px 8px', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)' }}>
                                <span className="log-text" style={{ fontFamily: 'var(--font-mono)', fontSize: '11px' }}>{action.receipt}</span>
                                <button className="log-copy" title="Copy"><Copy size={12} /></button>
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
}

function PostmortemTab({ incident }) {
    if (!incident.postmortem) {
        return <div className="empty-state"><FileText /><h3>No postmortem yet</h3><p>Postmortem will be auto-drafted once the incident is resolved.</p></div>;
    }

    const pm = incident.postmortem;

    return (
        <div>
            <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '8px' }}>Summary</h3>
            <p className="body-sm" style={{ marginBottom: '16px' }}>{pm.summary}</p>

            <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '8px' }}>Customer Impact</h3>
            <p className="body-sm" style={{ marginBottom: '16px' }}>{pm.customerImpact}</p>

            <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '8px' }}>Root Cause</h3>
            <p className="body-sm" style={{ marginBottom: '16px' }}>{pm.rootCause}</p>

            <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '8px' }}>Action Items</h3>
            <div>
                {pm.actionItems.map((item, i) => (
                    <div key={i} className={`checklist-item${item.done ? ' checked' : ''}`}>
                        <input type="checkbox" checked={item.done} readOnly />
                        <span>{item.text}</span>
                    </div>
                ))}
            </div>

            <div style={{ marginTop: '16px' }}>
                <button className="btn btn-secondary btn-sm">
                    <GitBranch size={12} />
                    Create GitHub Issue
                </button>
            </div>
        </div>
    );
}

export default function IncidentsPage() {
    const { liveEvents } = useApp();
    const [drawerIncident, setDrawerIncident] = useState(null);
    const [severityFilter, setSeverityFilter] = useState('all');
    const [statusFilter, setStatusFilter] = useState('all');

    const allIncidents = useMemo(() => {
        const simulated = liveEvents.map(evt => ({
            id: evt.id,
            severity: evt.severity === 'P1' ? 'critical' : 'warning',
            service: evt.service,
            detected: evt.timestamp,
            status: 'investigating',
            confidence: 0.75,
            blastRadius: [],
            actionsFired: 0,
            rootCause: `${evt.type.replace(/_/g, ' ')} detected on ${evt.service}`,
            timeline: [
                { time: new Date(evt.timestamp).toLocaleTimeString(), agent: 'Ag1-Detector', action: `Anomaly detected: ${evt.type}`, status: 'complete' },
            ],
            blastRadiusDetail: { primary: evt.service, affected: [] },
            patternMemory: [],
            actions: [],
            postmortem: null,
        }));
        return [...simulated, ...INCIDENTS_DATA];
    }, [liveEvents]);

    const filteredIncidents = allIncidents.filter(inc => {
        if (severityFilter !== 'all' && inc.severity !== severityFilter) return false;
        if (statusFilter !== 'all' && inc.status !== statusFilter) return false;
        return true;
    });

    return (
        <div id="incidents-page">
            <div className="page-header">
                <div>
                    <h1>Incidents</h1>
                    <p className="page-subtitle">{allIncidents.length} total · {allIncidents.filter(i => i.status !== 'resolved').length} active</p>
                </div>
            </div>

            <div className="filters-bar">
                <select
                    className="filter-select"
                    value={severityFilter}
                    onChange={e => setSeverityFilter(e.target.value)}
                    id="filter-severity"
                >
                    <option value="all">All Severities</option>
                    <option value="critical">Critical</option>
                    <option value="warning">Warning</option>
                    <option value="info">Info</option>
                </select>
                <select
                    className="filter-select"
                    value={statusFilter}
                    onChange={e => setStatusFilter(e.target.value)}
                    id="filter-status"
                >
                    <option value="all">All Statuses</option>
                    <option value="investigating">Investigating</option>
                    <option value="resolved">Resolved</option>
                </select>
            </div>

            <div className="table-container">
                <table className="data-table" id="incidents-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Severity</th>
                            <th>Service</th>
                            <th>Detected</th>
                            <th>Status</th>
                            <th>Confidence</th>
                            <th>Blast Radius</th>
                            <th>Actions</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredIncidents.map(inc => (
                            <tr
                                key={inc.id}
                                className="clickable"
                                onClick={() => setDrawerIncident(inc)}
                                id={`incident-row-${inc.id}`}
                            >
                                <td className="mono-cell">{inc.id}</td>
                                <td><SeverityChip severity={inc.severity} /></td>
                                <td>{inc.service}</td>
                                <td style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>{new Date(inc.detected).toLocaleString()}</td>
                                <td><StatusChip status={inc.status} /></td>
                                <td>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <div className="confidence-bar">
                                            <div
                                                className="confidence-bar-fill"
                                                style={{
                                                    width: `${inc.confidence * 100}%`,
                                                    background: inc.confidence >= 0.85 ? 'var(--color-healthy)' : inc.confidence >= 0.6 ? 'var(--color-warning)' : 'var(--color-critical)',
                                                }}
                                            />
                                        </div>
                                        <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)' }}>{Math.round(inc.confidence * 100)}%</span>
                                    </div>
                                </td>
                                <td>
                                    {inc.blastRadius.length > 0
                                        ? <span style={{ fontSize: '12px' }}>{inc.blastRadius.join(', ')}</span>
                                        : <span style={{ color: 'var(--text-tertiary)', fontSize: '12px' }}>—</span>}
                                </td>
                                <td style={{ fontSize: '12px' }}>{inc.actionsFired}</td>
                                <td><ChevronRight size={14} style={{ color: 'var(--text-tertiary)' }} /></td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {drawerIncident && (
                <IncidentDrawer
                    incident={drawerIncident}
                    onClose={() => setDrawerIncident(null)}
                />
            )}
        </div>
    );
}
