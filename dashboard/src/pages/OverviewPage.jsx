import { useState } from 'react';
import { useApp } from '../hooks/useAppContext';
import {
    METRICS_OVERVIEW, STEPPER_STATES, DEPENDENCY_GRAPH,
    INCIDENTS_DATA
} from '../data/mockData';
import {
    AlertTriangle, TrendingUp, Activity, Clock, Check,
    ChevronDown, ChevronRight, Zap, ArrowRight, Circle
} from 'lucide-react';

function MetricCard({ label, value, change, changeDir, icon: Icon }) {
    return (
        <div className="metric-card" id={`metric-${label.toLowerCase().replace(/\s/g, '-')}`}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span className="metric-label">{label}</span>
                {Icon && <Icon size={14} style={{ color: 'var(--text-tertiary)' }} />}
            </div>
            <div className="metric-value">{value}</div>
            {change && (
                <div className={`metric-change ${changeDir}`}>
                    <TrendingUp size={12} style={changeDir === 'down' ? { transform: 'rotate(180deg)' } : {}} />
                    {change}
                </div>
            )}
        </div>
    );
}

function LiveStepper() {
    const [expandedStep, setExpandedStep] = useState(null);

    return (
        <div className="card" id="live-agent-loop">
            <div className="card-header">
                <span className="card-title">Live Agent Loop</span>
                <span className="body-xs">INC-001 · payment-service</span>
            </div>
            <div className="stepper">
                {STEPPER_STATES.map((step, idx) => (
                    <div key={step.id} className={`stepper-step ${step.status}`}>
                        <div className="stepper-line" />
                        <div className="stepper-dot">
                            {step.status === 'complete' && <Check size={12} />}
                            {step.status === 'active' && <Circle size={8} fill="currentColor" />}
                        </div>
                        <div className="stepper-content">
                            <div
                                className="stepper-label"
                                onClick={() => setExpandedStep(expandedStep === idx ? null : idx)}
                                style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
                            >
                                {step.label}
                                {expandedStep === idx ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                            </div>
                            <div className="stepper-detail">{step.detail}</div>
                            <div className="stepper-timestamp">{step.timestamp}</div>
                            {expandedStep === idx && (
                                <div className="stepper-evidence" style={{ marginTop: '6px' }}>{step.evidence}</div>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

function BlastRadiusGraph() {
    const [hoveredNode, setHoveredNode] = useState(null);
    const { edges } = DEPENDENCY_GRAPH;

    // Well-spaced node positions (percentage-based, 3-tier layout)
    const graphNodes = [
        { id: 'api-gateway', label: 'API Gateway', x: 50, y: 8, status: 'healthy' },
        { id: 'payment-service', label: 'Payment Svc', x: 22, y: 32, status: 'critical' },
        { id: 'user-service', label: 'User Svc', x: 78, y: 32, status: 'healthy' },
        { id: 'order-service', label: 'Order Svc', x: 10, y: 60, status: 'warning' },
        { id: 'inventory-service', label: 'Inventory', x: 40, y: 60, status: 'healthy' },
        { id: 'notification-service', label: 'Notif Svc', x: 70, y: 60, status: 'healthy' },
        { id: 'db-primary', label: 'DB Primary', x: 25, y: 88, status: 'healthy' },
        { id: 'redis-cluster', label: 'Redis', x: 60, y: 88, status: 'healthy' },
    ];

    const statusColors = {
        healthy: '#22c55e',
        critical: '#ef4444',
        warning: '#f59e0b',
    };

    return (
        <div className="card blast-radius-card" id="blast-radius-panel">
            <div className="card-header">
                <span className="card-title">Blast Radius</span>
                <span className="severity-chip critical">2 at risk</span>
            </div>
            <div className="blast-graph">
                {/* SVG edges — same percentage coordinate space as nodes */}
                <svg
                    className="blast-graph-svg"
                    viewBox="0 0 100 100"
                    preserveAspectRatio="xMidYMid meet"
                >
                    <defs>
                        <linearGradient id="edgeCrit" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stopColor="#ef4444" stopOpacity="0.5" />
                            <stop offset="100%" stopColor="#ef4444" stopOpacity="0.12" />
                        </linearGradient>
                        <linearGradient id="edgeNorm" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stopColor="#71717a" stopOpacity="0.3" />
                            <stop offset="100%" stopColor="#71717a" stopOpacity="0.08" />
                        </linearGradient>
                    </defs>
                    {edges.map((edge, i) => {
                        const from = graphNodes.find(n => n.id === edge.from);
                        const to = graphNodes.find(n => n.id === edge.to);
                        if (!from || !to) return null;
                        const isCrit = from.status === 'critical' || to.status === 'critical';
                        const isLit = hoveredNode && (hoveredNode === from.id || hoveredNode === to.id);
                        return (
                            <line
                                key={i}
                                x1={from.x} y1={from.y}
                                x2={to.x} y2={to.y}
                                stroke={isCrit ? 'url(#edgeCrit)' : 'url(#edgeNorm)'}
                                strokeWidth={isLit ? 0.8 : 0.35}
                                strokeDasharray={isCrit ? 'none' : '2 1.5'}
                                opacity={isLit ? 1 : 0.7}
                                style={{ transition: 'stroke-width 200ms, opacity 200ms' }}
                            />
                        );
                    })}
                </svg>

                {/* Nodes */}
                {graphNodes.map(node => {
                    const color = statusColors[node.status];
                    const isHovered = hoveredNode === node.id;
                    return (
                        <div
                            key={node.id}
                            className={`blast-node ${node.status}${isHovered ? ' hovered' : ''}`}
                            style={{ left: `${node.x}%`, top: `${node.y}%` }}
                            onMouseEnter={() => setHoveredNode(node.id)}
                            onMouseLeave={() => setHoveredNode(null)}
                        >
                            <span className="blast-node-ring" style={{ '--node-color': color }} />
                            <span className="blast-node-dot" style={{ background: color }} />
                            <span className="blast-node-label">{node.label}</span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

function SimilarIncidents() {
    const patterns = INCIDENTS_DATA[0].patternMemory;
    return (
        <div className="card" id="pattern-memory-panel">
            <div className="card-header">
                <span className="card-title">Similar Past Incidents</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {patterns.map(p => (
                    <div key={p.id} className="evidence-card">
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>{p.id}</span>
                            <span className={`similarity-score ${p.similarity >= 0.9 ? 'high' : p.similarity >= 0.8 ? 'medium' : 'low'}`}>
                                {Math.round(p.similarity * 100)}%
                            </span>
                        </div>
                        <div className="evidence-text">{p.cause}</div>
                        <div style={{ fontSize: '11px', color: 'var(--color-healthy)', marginTop: '4px', fontWeight: 500 }}>
                            Fix: {p.fix}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

function QuickSimulate() {
    const { setSimulationModalOpen, simulationState } = useApp();
    return (
        <div className="card" id="quick-simulate">
            <div className="card-header">
                <span className="card-title">Quick Simulate</span>
            </div>
            <p className="body-sm" style={{ marginBottom: '12px' }}>
                Trigger a demo scenario to see the full autonomous loop in action.
            </p>
            <button
                className={`btn-simulate${simulationState ? ' running' : ''}`}
                onClick={() => !simulationState && setSimulationModalOpen(true)}
                style={{ width: '100%', justifyContent: 'center' }}
                id="overview-simulate-btn"
            >
                <Zap size={14} />
                {simulationState ? 'Running…' : 'Simulate Event'}
            </button>
        </div>
    );
}

export default function OverviewPage() {
    const { liveEvents } = useApp();
    const m = METRICS_OVERVIEW;

    return (
        <div id="overview-page">
            <div className="page-header">
                <div>
                    <h1>Control Tower</h1>
                    <p className="page-subtitle">Real-time autonomous release safety overview</p>
                </div>
            </div>

            <div className="grid-3col" style={{ marginBottom: 'var(--space-6)' }}>
                {/* LEFT: Key Metrics */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
                    <MetricCard label="Active Incidents" value={m.activeIncidents} change="+1 in 2h" changeDir="up" icon={AlertTriangle} />
                    <MetricCard label="Deploy Confidence" value={`${m.deployConfidence}%`} change="−4 from avg" changeDir="up" icon={Activity} />
                    <MetricCard label="Error Rate" value={`${(m.errorRate * 100).toFixed(1)}%`} change="+2.1% spike" changeDir="up" icon={TrendingUp} />
                    <MetricCard label="Avg MTTR" value={`${m.mttrAvg}m`} change={`${Math.round((1 - m.mttrAvg / m.mttrIndustry) * 100)}% faster than industry`} changeDir="down" icon={Clock} />
                    <QuickSimulate />
                </div>

                {/* CENTER: Live Agent Loop */}
                <div>
                    <LiveStepper />

                    {liveEvents.length > 0 && (
                        <div className="card" style={{ marginTop: 'var(--space-4)' }}>
                            <div className="card-header">
                                <span className="card-title">Recent Simulated Events</span>
                                <span className="body-xs">{liveEvents.length} new</span>
                            </div>
                            {liveEvents.slice(0, 3).map(evt => (
                                <div key={evt.id} className="log-line">
                                    <span className="log-time">{new Date(evt.timestamp).toLocaleTimeString()}</span>
                                    <span className="log-text">
                                        <span className={`severity-chip ${evt.severity === 'P1' ? 'critical' : 'warning'}`} style={{ marginRight: '6px' }}>{evt.severity}</span>
                                        {evt.service} — {evt.type.replace(/_/g, ' ')}
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* RIGHT: Evidence + Prediction */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
                    <BlastRadiusGraph />
                    <SimilarIncidents />
                </div>
            </div>
        </div>
    );
}
