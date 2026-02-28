import { useState, useEffect } from 'react';
import { fetchRepoInfo, fetchRepoFeatures } from '../services/api';
import {
    GitBranch, Star, GitFork, Eye, ExternalLink, Folder, FileText,
    Clock, Users, Code, Zap, Shield, Brain, Database, MessageSquare,
    Search, Play, ChevronDown, ChevronRight, Activity, CheckCircle2,
    AlertCircle, PauseCircle, ArrowRight
} from 'lucide-react';

const FEATURE_ICONS = {
    'multi-agent': Brain,
    'snowflake-cortex': Database,
    'threshold-engine': Shield,
    'composio-actions': MessageSquare,
    'incident-dna': Activity,
    'demo-mode': Play,
    'vector-search': Search,
    'ci-trigger': Zap,
};

function StatusBadge({ status }) {
    const colors = {
        active: { bg: 'rgba(34,197,94,0.12)', border: 'rgba(34,197,94,0.25)', text: '#22c55e', label: 'Active' },
        disabled: { bg: 'rgba(239,68,68,0.12)', border: 'rgba(239,68,68,0.25)', text: '#ef4444', label: 'Disabled' },
        standby: { bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.25)', text: '#f59e0b', label: 'Standby' },
    };
    const c = colors[status] || colors.standby;
    const Icon = status === 'active' ? CheckCircle2 : status === 'disabled' ? AlertCircle : PauseCircle;
    return (
        <span style={{
            display: 'inline-flex', alignItems: 'center', gap: '4px',
            padding: '2px 8px', borderRadius: '9999px', fontSize: '11px', fontWeight: 600,
            background: c.bg, border: `1px solid ${c.border}`, color: c.text,
        }}>
            <Icon size={10} />
            {c.label}
        </span>
    );
}

function RepoHeader({ repo }) {
    if (!repo) return null;
    const since = repo.createdAt ? new Date(repo.createdAt).toLocaleDateString('en-US', { year: 'numeric', month: 'short' }) : '';
    const lastPush = repo.pushedAt ? new Date(repo.pushedAt).toLocaleString() : '';

    return (
        <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px', flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: '280px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                        <Shield size={20} style={{ color: 'var(--color-accent)' }} />
                        <h2 style={{ margin: 0, fontSize: '20px' }}>{repo.fullName}</h2>
                        <span style={{
                            padding: '2px 8px', borderRadius: '9999px', fontSize: '11px',
                            background: 'rgba(99,102,241,0.12)', border: '1px solid rgba(99,102,241,0.25)', color: '#818cf8',
                        }}>{repo.visibility}</span>
                    </div>
                    <p className="body-sm" style={{ color: 'var(--text-secondary)', margin: '0 0 12px 0' }}>
                        {repo.description || 'AI-powered autonomous incident detection and resolution platform'}
                    </p>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                        {(repo.topics || []).map(t => (
                            <span key={t} style={{
                                padding: '2px 10px', borderRadius: '9999px', fontSize: '11px',
                                background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.15)', color: 'var(--text-secondary)',
                            }}>{t}</span>
                        ))}
                    </div>
                </div>
                <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
                    {[
                        { icon: Star, label: 'Stars', value: repo.stars },
                        { icon: GitFork, label: 'Forks', value: repo.forks },
                        { icon: AlertCircle, label: 'Issues', value: repo.openIssues },
                        { icon: Eye, label: 'Watchers', value: repo.watchers },
                    ].map(s => (
                        <div key={s.label} style={{ textAlign: 'center', minWidth: '48px' }}>
                            <s.icon size={14} style={{ color: 'var(--text-tertiary)', marginBottom: '2px' }} />
                            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '16px', fontWeight: 700 }}>{s.value}</div>
                            <div style={{ fontSize: '10px', color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>{s.label}</div>
                        </div>
                    ))}
                </div>
            </div>
            <div style={{ display: 'flex', gap: '16px', marginTop: '16px', flexWrap: 'wrap', fontSize: '12px', color: 'var(--text-tertiary)' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <GitBranch size={12} /> {repo.defaultBranch}
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Clock size={12} /> Created {since}
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Zap size={12} /> Last push: {lastPush}
                </span>
                <a href={repo.url} target="_blank" rel="noopener noreferrer"
                    style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--color-accent)', textDecoration: 'none' }}>
                    <ExternalLink size={12} /> View on GitHub
                </a>
            </div>
        </div>
    );
}

function LanguageBar({ languages }) {
    if (!languages || Object.keys(languages).length === 0) return null;
    const LANG_COLORS = {
        Python: '#3572A5', JavaScript: '#f1e05a', TypeScript: '#3178c6', HTML: '#e34c26',
        CSS: '#563d7c', Shell: '#89e051', Dockerfile: '#384d54', SQL: '#e38c00',
        Makefile: '#427819', SCSS: '#c6538c', Vue: '#41b883',
    };
    const entries = Object.entries(languages).sort((a, b) => b[1] - a[1]);

    return (
        <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
            <div className="card-header">
                <span className="card-title"><Code size={14} style={{ marginRight: '6px' }} />Languages</span>
            </div>
            <div style={{ display: 'flex', borderRadius: '6px', overflow: 'hidden', height: '8px', marginBottom: '12px' }}>
                {entries.map(([lang, pct]) => (
                    <div key={lang} title={`${lang}: ${pct}%`}
                        style={{ width: `${pct}%`, background: LANG_COLORS[lang] || '#71717a', minWidth: pct > 0.5 ? '3px' : '1px' }} />
                ))}
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
                {entries.map(([lang, pct]) => (
                    <div key={lang} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
                        <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: LANG_COLORS[lang] || '#71717a' }} />
                        <span style={{ fontWeight: 500 }}>{lang}</span>
                        <span style={{ color: 'var(--text-tertiary)' }}>{pct}%</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

function FileTree({ files }) {
    if (!files || files.length === 0) return null;
    return (
        <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
            <div className="card-header">
                <span className="card-title"><Folder size={14} style={{ marginRight: '6px' }} />Repository Structure</span>
                <span className="body-xs">{files.length} items</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '4px' }}>
                {files.map(f => {
                    const Icon = f.type === 'dir' ? Folder : FileText;
                    const iconColor = f.type === 'dir' ? '#818cf8' : 'var(--text-tertiary)';
                    return (
                        <div key={f.path} style={{
                            display: 'flex', alignItems: 'center', gap: '8px',
                            padding: '6px 10px', borderRadius: '6px',
                            fontSize: '13px', fontFamily: 'var(--font-mono)',
                            background: 'var(--bg-secondary)',
                        }}>
                            <Icon size={14} style={{ color: iconColor, flexShrink: 0 }} />
                            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.name}</span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

function RecentCommits({ commits }) {
    if (!commits || commits.length === 0) return null;
    return (
        <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
            <div className="card-header">
                <span className="card-title"><GitBranch size={14} style={{ marginRight: '6px' }} />Recent Commits</span>
                <span className="body-xs">{commits.length} latest</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                {commits.map((c, idx) => (
                    <div key={c.sha + idx} style={{
                        display: 'flex', alignItems: 'center', gap: '12px',
                        padding: '8px 10px', borderRadius: '6px',
                        background: idx % 2 === 0 ? 'transparent' : 'var(--bg-secondary)',
                    }}>
                        {c.avatar ? (
                            <img src={c.avatar} alt="" style={{ width: '24px', height: '24px', borderRadius: '50%' }} />
                        ) : (
                            <Users size={16} style={{ color: 'var(--text-tertiary)' }} />
                        )}
                        <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: '13px', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {c.message}
                            </div>
                            <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '1px' }}>
                                {c.author} &middot; {c.date ? new Date(c.date).toLocaleDateString() : ''}
                            </div>
                        </div>
                        <code style={{ fontSize: '11px', color: 'var(--color-accent)', background: 'rgba(99,102,241,0.08)', padding: '2px 6px', borderRadius: '4px' }}>
                            {c.sha}
                        </code>
                    </div>
                ))}
            </div>
        </div>
    );
}

function Contributors({ contributors }) {
    if (!contributors || contributors.length === 0) return null;
    return (
        <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
            <div className="card-header">
                <span className="card-title"><Users size={14} style={{ marginRight: '6px' }} />Contributors</span>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
                {contributors.map(c => (
                    <a key={c.login} href={c.url} target="_blank" rel="noopener noreferrer"
                        style={{
                            display: 'flex', alignItems: 'center', gap: '8px',
                            padding: '8px 14px', borderRadius: '8px', textDecoration: 'none',
                            background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)',
                            transition: 'border-color 150ms',
                        }}
                        onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--color-accent)'}
                        onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border-primary)'}
                    >
                        <img src={c.avatar} alt="" style={{ width: '28px', height: '28px', borderRadius: '50%' }} />
                        <div>
                            <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>{c.login}</div>
                            <div style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>{c.contributions} commits</div>
                        </div>
                    </a>
                ))}
            </div>
        </div>
    );
}

function FeaturesSection({ features }) {
    const [expanded, setExpanded] = useState(null);
    if (!features) return null;

    return (
        <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
            <div className="card-header">
                <span className="card-title"><Zap size={14} style={{ marginRight: '6px' }} />Platform Features</span>
                <span className="body-xs">{features.features?.length || 0} capabilities</span>
            </div>
            <p className="body-sm" style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
                {features.tagline}
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '10px' }}>
                {(features.features || []).map(f => {
                    const Icon = FEATURE_ICONS[f.id] || Zap;
                    const isExpanded = expanded === f.id;
                    return (
                        <div key={f.id}
                            onClick={() => setExpanded(isExpanded ? null : f.id)}
                            style={{
                                padding: '14px 16px', borderRadius: '10px', cursor: 'pointer',
                                background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)',
                                transition: 'border-color 150ms, box-shadow 150ms',
                                borderColor: isExpanded ? 'var(--color-accent)' : 'var(--border-primary)',
                                boxShadow: isExpanded ? '0 0 0 1px rgba(99,102,241,0.15)' : 'none',
                            }}
                        >
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <Icon size={16} style={{ color: 'var(--color-accent)' }} />
                                    <span style={{ fontSize: '13px', fontWeight: 600 }}>{f.title}</span>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                    <StatusBadge status={f.status} />
                                    {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                                </div>
                            </div>
                            {isExpanded && (
                                <div style={{ marginTop: '8px' }}>
                                    <p className="body-sm" style={{ color: 'var(--text-secondary)', margin: '0 0 8px 0' }}>{f.description}</p>
                                    <div style={{
                                        fontSize: '11px', fontFamily: 'var(--font-mono)',
                                        padding: '4px 8px', borderRadius: '4px',
                                        background: 'rgba(99,102,241,0.06)', color: 'var(--text-tertiary)',
                                    }}>
                                        {f.stats}
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

function ArchitectureSection({ arch }) {
    if (!arch) return null;
    return (
        <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
            <div className="card-header">
                <span className="card-title"><Activity size={14} style={{ marginRight: '6px' }} />Architecture</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '16px', marginBottom: '16px' }}>
                {[
                    { label: 'AI Agents', value: arch.agents?.join(', '), icon: Brain },
                    { label: 'Data Store', value: arch.dataStore, icon: Database },
                    { label: 'LLM Engine', value: arch.llm, icon: Zap },
                    { label: 'Integrations', value: arch.integrations?.join(', '), icon: MessageSquare },
                ].map(item => (
                    <div key={item.label} style={{
                        padding: '12px 14px', borderRadius: '8px',
                        background: 'var(--bg-secondary)', border: '1px solid var(--border-primary)',
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                            <item.icon size={13} style={{ color: 'var(--color-accent)' }} />
                            <span style={{ fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', color: 'var(--text-tertiary)', letterSpacing: '0.5px' }}>
                                {item.label}
                            </span>
                        </div>
                        <div style={{ fontSize: '13px', fontWeight: 500 }}>{item.value}</div>
                    </div>
                ))}
            </div>
            <div style={{
                padding: '12px 16px', borderRadius: '8px',
                background: 'linear-gradient(90deg, rgba(99,102,241,0.06), rgba(34,197,94,0.06))',
                border: '1px solid var(--border-primary)',
            }}>
                <div style={{ fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '8px', letterSpacing: '0.5px' }}>
                    End-to-End Pipeline
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 500 }}>
                    {(arch.pipeline || '').split(' → ').map((step, i, arr) => (
                        <span key={i} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{
                                padding: '3px 10px', borderRadius: '6px',
                                background: 'var(--bg-primary)', border: '1px solid var(--border-primary)',
                            }}>{step}</span>
                            {i < arr.length - 1 && <ArrowRight size={12} style={{ color: 'var(--text-tertiary)' }} />}
                        </span>
                    ))}
                </div>
            </div>
        </div>
    );
}

export default function RepositoryPage() {
    const [repo, setRepo] = useState(null);
    const [features, setFeatures] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;
        const load = async () => {
            setLoading(true);
            const [r, f] = await Promise.all([fetchRepoInfo(), fetchRepoFeatures()]);
            if (!cancelled) {
                setRepo(r);
                setFeatures(f);
                setLoading(false);
            }
        };
        load();
        const interval = setInterval(load, 60000);
        return () => { cancelled = true; clearInterval(interval); };
    }, []);

    if (loading && !repo) {
        return (
            <div id="repository-page">
                <div className="page-header">
                    <div>
                        <h1>Repository</h1>
                        <p className="page-subtitle">Loading repository details...</p>
                    </div>
                </div>
                <div className="card" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-tertiary)' }}>
                    <Activity size={24} style={{ marginBottom: '8px', animation: 'spin 1s linear infinite' }} />
                    <p>Fetching from GitHub API...</p>
                </div>
            </div>
        );
    }

    return (
        <div id="repository-page">
            <div className="page-header">
                <div>
                    <h1>Repository</h1>
                    <p className="page-subtitle">Live repository details, architecture & platform features</p>
                </div>
            </div>

            <RepoHeader repo={repo} />

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)', marginBottom: 'var(--space-4)' }}>
                <LanguageBar languages={repo?.languages} />
                <Contributors contributors={repo?.contributors} />
            </div>

            <FeaturesSection features={features} />
            <ArchitectureSection arch={features?.architecture} />

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)' }}>
                <FileTree files={repo?.fileTree} />
                <RecentCommits commits={repo?.recentCommits} />
            </div>
        </div>
    );
}
