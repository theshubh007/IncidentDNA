import { useState, useEffect } from 'react';
import { useApp } from '../hooks/useAppContext';
import {
    fetchMetrics, fetchStepperState, fetchDependencyGraph, fetchIncidents,
    fetchRepoInfo,
} from '../services/api';
import {
    METRICS_OVERVIEW, STEPPER_STATES, DEPENDENCY_GRAPH, INCIDENTS_DATA
} from '../data/mockData';
import {
    AlertTriangle, TrendingUp, Activity, Clock, Check,
    ChevronDown, ChevronRight, Zap, ArrowRight, Circle,
    Star, GitFork, Users, GitCommit, Code2, Eye
} from 'lucide-react';

/* ── Language colors ──────────────────────────────────────────── */
const LANG_COLORS = {
    JavaScript: '#f1e05a', TypeScript: '#3178c6', Python: '#3572A5',
    Java: '#b07219', Go: '#00ADD8', Rust: '#dea584', Ruby: '#701516',
    'C++': '#f34b7d', C: '#555555', 'C#': '#178600', PHP: '#4F5D95',
    Swift: '#F05138', Kotlin: '#A97BFF', Dart: '#00B4AB',
    HTML: '#e34c26', CSS: '#563d7c', Shell: '#89e051', Dockerfile: '#384d54',
    Jupyter: '#DA5B0B', Makefile: '#427819', HCL: '#844FBA',
};

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

/* ── Recent Commits (replaces LiveStepper when repo data available) ── */
function RecentCommits({ commits, repoName }) {
    const [expandedIdx, setExpandedIdx] = useState(null);

    if (!commits || commits.length === 0) return null;

    return (
        <div className="card" id="live-agent-loop">
            <div className="card-header">
                <span className="card-title">Recent Commits</span>
                <span className="body-xs">{repoName}</span>
            </div>
            <div className="stepper">
                {commits.slice(0, 8).map((c, idx) => {
                    const isLatest = idx === 0;
                    return (
                        <div key={c.sha} className={`stepper-step ${isLatest ? 'active' : 'complete'}`}>
                            <div className="stepper-line" />
                            <div className="stepper-dot">
                                {isLatest ? <Circle size={8} fill="currentColor" /> : <Check size={12} />}
                            </div>
                            <div className="stepper-content">
                                <div
                                    className="stepper-label"
                                    onClick={() => setExpandedIdx(expandedIdx === idx ? null : idx)}
                                    style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
                                >
                                    <code style={{ fontSize: '11px', color: 'var(--color-accent)' }}>{c.sha}</code>
                                    {expandedIdx === idx ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                                </div>
                                <div className="stepper-detail">{c.message}</div>
                                <div className="stepper-timestamp">
                                    {c.author} {c.date ? `· ${new Date(c.date).toLocaleDateString()}` : ''}
                                </div>
                                {expandedIdx === idx && (
                                    <div className="stepper-evidence" style={{ marginTop: '6px' }}>
                                        Full message: {c.message}
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

/* ── Fallback LiveStepper (mock data) ────────────────────────── */
function LiveStepper({ steps }) {
    const [expandedStep, setExpandedStep] = useState(null);

    return (
        <div className="card" id="live-agent-loop">
            <div className="card-header">
                <span className="card-title">Live Agent Loop</span>
            </div>
            <div className="stepper">
                {steps.map((step, idx) => (
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

/* ── File Structure — visual tree ─────────────────────────────── */
function FileStructure({ fileTree, repoName }) {
    if (!fileTree || fileTree.length === 0) return null;

    const dirs = fileTree.filter(f => f.type === 'dir');
    const files = fileTree.filter(f => f.type !== 'dir');
    const all = [...dirs, ...files];

    const fmtSize = (bytes) => {
        if (!bytes || bytes === 0) return '';
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / 1048576).toFixed(1)} MB`;
    };

    const fileColor = (name) => {
        const ext = name.split('.').pop()?.toLowerCase();
        const map = {
            py: '#3572A5', js: '#f1e05a', jsx: '#f1e05a', ts: '#3178c6', tsx: '#3178c6',
            json: '#71717a', yml: '#cb171e', yaml: '#cb171e', md: '#083fa1',
            css: '#563d7c', html: '#e34c26', sh: '#89e051', sql: '#e38c00',
            env: '#71717a', txt: '#71717a', toml: '#9c4221', cfg: '#71717a',
            ps1: '#012456', dockerfile: '#384d54', gitignore: '#f05033',
        };
        return map[ext] || '#71717a';
    };

    const connectorStyle = {
        color: 'var(--text-tertiary)', opacity: 0.5, userSelect: 'none',
        width: '18px', flexShrink: 0, textAlign: 'right',
    };

    return (
        <div className="card" id="blast-radius-panel" style={{ maxHeight: '420px', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div className="card-header">
                <span className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Code2 size={14} style={{ color: 'var(--color-accent)' }} />
                    {repoName || 'File Structure'}
                </span>
                <span className="body-xs">{dirs.length} dirs, {files.length} files</span>
            </div>
            <div style={{
                overflow: 'auto', flex: 1, padding: '4px 0',
                fontSize: '12px', fontFamily: 'var(--font-mono)', lineHeight: '1.7',
            }}>
                {all.map((item, idx) => {
                    const isLast = idx === all.length - 1;
                    const isDir = item.type === 'dir';
                    const connector = isLast ? '\u2514\u2500\u2500' : '\u251C\u2500\u2500';

                    return (
                        <div key={item.name} style={{
                            display: 'flex', alignItems: 'center',
                            padding: '1px 14px', cursor: 'default',
                            transition: 'background 120ms',
                            borderRadius: '4px', margin: '0 4px',
                        }}
                            onMouseEnter={e => e.currentTarget.style.background = 'rgba(99,102,241,0.06)'}
                            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                        >
                            <span style={connectorStyle}>{connector}</span>
                            {isDir ? (
                                <>
                                    <span style={{ margin: '0 6px', color: 'var(--color-accent)', fontSize: '13px', flexShrink: 0 }}>/</span>
                                    <span style={{ fontWeight: 600, color: 'var(--text-primary)', flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                        {item.name}
                                    </span>
                                </>
                            ) : (
                                <>
                                    <span style={{
                                        width: '7px', height: '7px', borderRadius: '50%', flexShrink: 0,
                                        background: fileColor(item.name), margin: '0 6px',
                                    }} />
                                    <span style={{ color: 'var(--text-secondary)', flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                        {item.name}
                                    </span>
                                    <span style={{ color: 'var(--text-tertiary)', fontSize: '10px', flexShrink: 0, marginLeft: '8px' }}>
                                        {fmtSize(item.size)}
                                    </span>
                                </>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

/* ── Fallback Blast Radius (mock data) ───────────────────────── */
function BlastRadiusGraph({ graph }) {
    const [hoveredNode, setHoveredNode] = useState(null);
    const edges = graph?.edges || [];
    const graphNodes = (graph?.nodes || []).map(n => typeof n === 'string' ? null : n).filter(Boolean);

    const statusColors = { healthy: '#22c55e', critical: '#ef4444', warning: '#f59e0b' };
    const atRisk = graphNodes.filter(n => n.status !== 'healthy').length;

    return (
        <div className="card blast-radius-card" id="blast-radius-panel">
            <div className="card-header">
                <span className="card-title">Blast Radius</span>
                <span className={`severity-chip ${atRisk > 0 ? 'critical' : 'healthy'}`}>
                    {atRisk > 0 ? `${atRisk} at risk` : 'All healthy'}
                </span>
            </div>
            <div className="blast-graph">
                <svg className="blast-graph-svg" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet">
                    <defs>
                        <linearGradient id="edgeCrit" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stopColor="#ef4444" stopOpacity="0.5" />
                            <stop offset="100%" stopColor="#ef4444" stopOpacity="0.12" />
                        </linearGradient>
                        <linearGradient id="edgeNorm2" x1="0%" y1="0%" x2="100%" y2="100%">
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
                            <line key={i}
                                x1={from.x / 5} y1={from.y / 4}
                                x2={to.x / 5} y2={to.y / 4}
                                stroke={isCrit ? 'url(#edgeCrit)' : 'url(#edgeNorm2)'}
                                strokeWidth={isLit ? 0.8 : 0.35}
                                strokeDasharray={isCrit ? 'none' : '2 1.5'}
                                opacity={isLit ? 1 : 0.7}
                                style={{ transition: 'stroke-width 200ms, opacity 200ms' }}
                            />
                        );
                    })}
                </svg>
                {graphNodes.map(node => {
                    const color = statusColors[node.status] || '#71717a';
                    const isHovered = hoveredNode === node.id;
                    return (
                        <div key={node.id}
                            className={`blast-node ${node.status}${isHovered ? ' hovered' : ''}`}
                            style={{ left: `${node.x / 5}%`, top: `${node.y / 4}%` }}
                            onMouseEnter={() => setHoveredNode(node.id)}
                            onMouseLeave={() => setHoveredNode(null)}
                        >
                            <span className="blast-node-ring" style={{ '--node-color': color }} />
                            <span className="blast-node-dot" style={{ background: color }} />
                            <span className="blast-node-label">{node.id.replace(/-/g, ' ')}</span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

/* ── Contributors Panel ──────────────────────────────────────── */
function ContributorsPanel({ contributors }) {
    if (!contributors || contributors.length === 0) return null;

    return (
        <div className="card" id="pattern-memory-panel">
            <div className="card-header">
                <span className="card-title">Top Contributors</span>
                <span className="body-xs">{contributors.length} people</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {contributors.slice(0, 5).map((c, i) => (
                    <div key={c.login || i} className="evidence-card" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        {c.avatar && (
                            <img src={c.avatar} alt={c.login}
                                style={{ width: '28px', height: '28px', borderRadius: '50%', flexShrink: 0 }} />
                        )}
                        <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 600 }}>{c.login}</div>
                            <div style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>{c.contributions} commits</div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

/* ── Fallback Similar Incidents (mock data) ──────────────────── */
function SimilarIncidents({ incidents }) {
    const patterns = incidents.length > 0 && incidents[0].patternMemory
        ? incidents[0].patternMemory
        : [];

    if (patterns.length === 0) {
        return (
            <div className="card" id="pattern-memory-panel">
                <div className="card-header">
                    <span className="card-title">Similar Past Incidents</span>
                </div>
                <p className="body-sm" style={{ color: 'var(--text-tertiary)' }}>No pattern data available.</p>
            </div>
        );
    }

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
                {simulationState ? 'Running\u2026' : 'Simulate Event'}
            </button>
        </div>
    );
}

export default function OverviewPage() {
    const { liveEvents } = useApp();
    const [metrics, setMetrics] = useState(METRICS_OVERVIEW);
    const [steps, setSteps] = useState(STEPPER_STATES);
    const [graph, setGraph] = useState(DEPENDENCY_GRAPH);
    const [incidents, setIncidents] = useState(INCIDENTS_DATA);
    const [repo, setRepo] = useState(null);

    useEffect(() => {
        let cancelled = false;
        const load = async () => {
            // Fetch mock/live incident data + GitHub repo data in parallel
            const [m, s, g, inc, repoData] = await Promise.all([
                fetchMetrics(),
                fetchStepperState('INC-001'),
                fetchDependencyGraph('llm-gateway'),
                fetchIncidents(),
                fetchRepoInfo(),
            ]);
            if (cancelled) return;
            setMetrics(m);
            setSteps(s);
            setGraph(g);
            setIncidents(inc);
            if (repoData) setRepo(repoData);
        };
        load();
        const interval = setInterval(load, 30000);
        return () => { cancelled = true; clearInterval(interval); };
    }, []);

    const m = metrics;
    const hasRepo = !!repo;

    return (
        <div id="overview-page">
            <div className="page-header">
                <div>
                    <h1>Control Tower</h1>
                    <p className="page-subtitle">
                        {hasRepo
                            ? `Monitoring ${repo.fullName} \u00b7 ${repo.defaultBranch}`
                            : 'Real-time autonomous release safety overview'}
                    </p>
                </div>
            </div>

            <div className="grid-3col" style={{ marginBottom: 'var(--space-6)' }}>
                {/* LEFT: Key Metrics — real repo stats when available */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
                    {hasRepo ? (
                        <>
                            <MetricCard label="Stars" value={repo.stars ?? 0} icon={Star} />
                            <MetricCard label="Forks" value={repo.forks ?? 0} icon={GitFork} />
                            <MetricCard label="Open Issues" value={repo.openIssues ?? 0}
                                change={repo.openIssues > 0 ? `${repo.openIssues} need attention` : 'All clear'}
                                changeDir={repo.openIssues > 0 ? 'up' : 'down'} icon={AlertTriangle} />
                            <MetricCard label="Contributors" value={repo.contributors?.length ?? 0} icon={Users} />
                            <MetricCard label="Languages" value={repo.languages ? Object.keys(repo.languages).length : 0} icon={Code2} />
                            <QuickSimulate />
                        </>
                    ) : (
                        <>
                            <MetricCard label="Active Incidents" value={m.activeIncidents} change="+1 in 2h" changeDir="up" icon={AlertTriangle} />
                            <MetricCard label="Deploy Confidence" value={`${m.deployConfidence}%`} change="\u22124 from avg" changeDir="up" icon={Activity} />
                            <MetricCard label="Error Rate" value={`${(m.errorRate * 100).toFixed(1)}%`} change="+2.1% spike" changeDir="up" icon={TrendingUp} />
                            <MetricCard label="Avg MTTR" value={`${m.mttrAvg}m`} change={`${Math.round((1 - m.mttrAvg / m.mttrIndustry) * 100)}% faster than industry`} changeDir="down" icon={Clock} />
                            <QuickSimulate />
                        </>
                    )}
                </div>

                {/* CENTER: Recent commits (real) or LiveStepper (mock) */}
                <div>
                    {hasRepo && repo.recentCommits?.length > 0
                        ? <RecentCommits commits={repo.recentCommits} repoName={repo.fullName} />
                        : <LiveStepper steps={steps} />
                    }

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
                                        {evt.service} \u2014 {evt.type.replace(/_/g, ' ')}
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* RIGHT: Tech stack (real) or Blast Radius (mock) + Contributors/Incidents */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
                    {hasRepo && repo.fileTree?.length > 0
                        ? <FileStructure fileTree={repo.fileTree} repoName={repo.fullName} />
                        : <BlastRadiusGraph graph={graph} />
                    }
                    {hasRepo && repo.contributors?.length > 0
                        ? <ContributorsPanel contributors={repo.contributors} />
                        : <SimilarIncidents incidents={incidents} />
                    }
                </div>
            </div>
        </div>
    );
}
